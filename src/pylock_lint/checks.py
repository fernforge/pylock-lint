"""Static checks over a parsed pylock.toml.

Each check yields Finding objects. Rules are keyed by a stable code (PLnnn) so
they can be selected/ignored from the CLI and referenced in CI logs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .model import Lockfile, package_source_types

ERROR = "error"
WARNING = "warning"

SUPPORTED_LOCK_MAJOR = 1


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    package: str | None
    message: str


# --- helpers ----------------------------------------------------------------

def _hashes_present(entry: dict[str, Any]) -> bool:
    h = entry.get("hashes")
    return isinstance(h, dict) and len(h) > 0


_WHEEL_RE = re.compile(r"^(?P<name>.+?)-(?P<ver>[^-]+)(-\d[^-]*)?-(?P<py>[^-]+)-(?P<abi>[^-]+)-(?P<plat>.+)\.whl$")


def _wheel_platform_family(filename: str) -> str | None:
    """Return a coarse platform family for a wheel filename, or None if pure ('any')."""
    m = _WHEEL_RE.match(filename)
    plat = m.group("plat") if m else filename
    plat = plat.lower()
    if plat == "any" or "none-any" in plat:
        return None
    for fam in ("manylinux", "musllinux", "linux", "macosx", "win", "android", "ios"):
        if fam in plat:
            return "windows" if fam == "win" else ("linux" if fam in ("manylinux", "musllinux") else fam)
    return plat


def _wheel_name(w: dict[str, Any]) -> str:
    n = w.get("name")
    if isinstance(n, str) and n:
        return n
    for key in ("url", "path"):
        v = w.get(key)
        if isinstance(v, str) and v:
            return v.rsplit("/", 1)[-1]
    return ""


# --- checks -----------------------------------------------------------------

def check_metadata(lock: Lockfile) -> Iterable[Finding]:
    lv = lock.lock_version
    if lv is None:
        yield Finding("PL012", ERROR, None, "missing required 'lock-version' key")
    else:
        try:
            major = int(lv.split(".")[0])
        except (ValueError, IndexError):
            yield Finding("PL012", ERROR, None, f"'lock-version' is not a valid version: {lv!r}")
        else:
            if major > SUPPORTED_LOCK_MAJOR:
                yield Finding(
                    "PL012", ERROR, None,
                    f"lock-version {lv} has a newer major than this linter supports (1.x)",
                )
    if lock.created_by is None:
        yield Finding("PL013", WARNING, None, "missing 'created-by' key (recommended for provenance)")
    if not lock.packages:
        yield Finding("PL014", WARNING, None, "lockfile declares no packages")


def check_packages(lock: Lockfile) -> Iterable[Finding]:
    for pkg in lock.packages:
        name = pkg.get("name")
        label = name if isinstance(name, str) else "<unnamed>"
        if not isinstance(name, str) or not name:
            yield Finding("PL010", ERROR, None, "package entry is missing required 'name'")

        sources = package_source_types(pkg)
        if not sources:
            yield Finding("PL003", ERROR, label, "package has no installable source (no sdist/wheels/vcs/directory/archive)")
        elif len(sources) > 1:
            yield Finding(
                "PL011", ERROR, label,
                f"package declares mutually-exclusive source types: {', '.join(sources)}",
            )

        has_dist = ("sdist" in pkg) or ("wheels" in pkg)
        if has_dist and not pkg.get("version"):
            yield Finding("PL015", ERROR, label, "package with sdist/wheels is missing 'version' (required by PEP 751)")

        # hash completeness on every downloadable artifact
        sdist = pkg.get("sdist")
        if isinstance(sdist, dict) and not _hashes_present(sdist):
            yield Finding("PL001", ERROR, label, "sdist has no hashes (integrity/reproducibility gap)")
        wheels = pkg.get("wheels")
        if isinstance(wheels, list):
            for w in wheels:
                if isinstance(w, dict) and not _hashes_present(w):
                    yield Finding("PL001", ERROR, label, f"wheel {_wheel_name(w) or '?'} has no hashes")
        archive = pkg.get("archive")
        if isinstance(archive, dict) and not _hashes_present(archive):
            yield Finding("PL001", ERROR, label, "archive has no hashes")

        # sdist-only: forces a source build on install -> non-reproducible, needs a toolchain
        if isinstance(sdist, dict) and not (isinstance(wheels, list) and wheels):
            yield Finding(
                "PL002", WARNING, label,
                "sdist-only (no wheels): install must build from source, which is not "
                "byte-reproducible and requires a build toolchain in CI",
            )


def check_portability(lock: Lockfile, require_cross_platform: bool = False) -> Iterable[Finding]:
    envs = lock.environments
    # Which platform families are covered by the committed wheels?
    families: set[str] = set()
    has_pure = False
    platform_specific_pkgs: list[str] = []
    for pkg in lock.packages:
        wheels = pkg.get("wheels")
        if not isinstance(wheels, list) or not wheels:
            continue
        pkg_families = set()
        pkg_pure = False
        for w in wheels:
            if not isinstance(w, dict):
                continue
            fam = _wheel_platform_family(_wheel_name(w))
            if fam is None:
                pkg_pure = True
            else:
                pkg_families.add(fam)
        families |= pkg_families
        has_pure = has_pure or pkg_pure
        if pkg_families and not pkg_pure:
            name = pkg.get("name")
            platform_specific_pkgs.append(name if isinstance(name, str) else "<unnamed>")

    if len(envs) <= 1 and platform_specific_pkgs:
        detail = (
            "no 'environments' declared" if not envs
            else f"only one environment declared: {envs[0]!r}"
        )
        yield Finding(
            "PL020", WARNING, None,
            f"single-environment lock ({detail}) but it pins platform-specific wheels "
            f"({', '.join(sorted(set(platform_specific_pkgs))[:5])}"
            f"{'...' if len(set(platform_specific_pkgs)) > 5 else ''}); "
            "installs on another OS/Python will fail or fall back to source",
        )

    if require_cross_platform and len(families) <= 1 and platform_specific_pkgs:
        yield Finding(
            "PL021", ERROR, None,
            f"--require-cross-platform: committed wheels cover only "
            f"{('platform ' + next(iter(families))) if families else 'a single platform'}; "
            "no wheels for other operating systems are present",
        )


# --- pyproject drift --------------------------------------------------------

def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared_dependencies(pyproject: dict[str, Any]) -> set[str]:
    from packaging.requirements import Requirement

    names: set[str] = set()
    proj = pyproject.get("project", {})
    reqs: list[str] = []
    if isinstance(proj.get("dependencies"), list):
        reqs += [r for r in proj["dependencies"] if isinstance(r, str)]
    opt = proj.get("optional-dependencies")
    if isinstance(opt, dict):
        for group in opt.values():
            if isinstance(group, list):
                reqs += [r for r in group if isinstance(r, str)]
    dg = pyproject.get("dependency-groups")
    if isinstance(dg, dict):
        for group in dg.values():
            if isinstance(group, list):
                reqs += [r for r in group if isinstance(r, str)]
    for r in reqs:
        try:
            names.add(_normalize(Requirement(r).name))
        except Exception:
            continue
    return names


def check_pyproject_drift(lock: Lockfile, pyproject_path: str | Path) -> Iterable[Finding]:
    import tomllib

    try:
        data = tomllib.loads(Path(pyproject_path).read_text("utf-8"))
    except Exception as exc:
        yield Finding("PL030", WARNING, None, f"could not read pyproject.toml for drift check: {exc}")
        return

    declared = _declared_dependencies(data)
    locked = {_normalize(p["name"]) for p in lock.packages if isinstance(p.get("name"), str)}
    missing = sorted(declared - locked)
    for name in missing:
        yield Finding("PL030", ERROR, name, "declared in pyproject.toml but absent from the lock (out of sync)")

    # requires-python coherence
    proj_rp = data.get("project", {}).get("requires-python")
    lock_rp = lock.requires_python
    if isinstance(proj_rp, str) and isinstance(lock_rp, str) and proj_rp.strip() != lock_rp.strip():
        yield Finding(
            "PL031", WARNING, None,
            f"requires-python differs: pyproject {proj_rp!r} vs pylock {lock_rp!r}",
        )


ALL_CODES = {
    "PL001": "artifact missing hashes",
    "PL002": "sdist-only package (no wheels)",
    "PL003": "package has no installable source",
    "PL010": "package missing name",
    "PL011": "mutually-exclusive source types",
    "PL012": "invalid or unsupported lock-version",
    "PL013": "missing created-by",
    "PL014": "no packages in lock",
    "PL015": "missing version with sdist/wheels",
    "PL020": "single-environment lock with platform-specific wheels",
    "PL021": "wheels cover only one platform (--require-cross-platform)",
    "PL030": "pyproject dependency missing from lock",
    "PL031": "requires-python mismatch vs pyproject",
}


def run_all(
    lock: Lockfile,
    pyproject_path: str | Path | None = None,
    require_cross_platform: bool = False,
) -> list[Finding]:
    findings: list[Finding] = []
    findings += check_metadata(lock)
    findings += check_packages(lock)
    findings += check_portability(lock, require_cross_platform=require_cross_platform)
    if pyproject_path is not None:
        findings += check_pyproject_drift(lock, pyproject_path)
    return findings
