"""Command-line entry point for pylock-lint."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from . import __version__
from .checks import ERROR, WARNING, Finding, run_all
from .model import LockParseError, load_lockfile


def _discover(paths: list[str]) -> list[str]:
    if paths:
        expanded: list[str] = []
        for p in paths:
            hits = glob.glob(p)
            expanded += hits if hits else [p]
        return expanded
    # default: any pylock.toml / pylock.*.toml in the cwd
    found = sorted(set(glob.glob("pylock.toml") + glob.glob("pylock.*.toml")))
    return found or ["pylock.toml"]


def _filter(findings: list[Finding], select: set[str] | None, ignore: set[str]) -> list[Finding]:
    out = []
    for f in findings:
        if select is not None and f.code not in select:
            continue
        if f.code in ignore:
            continue
        out.append(f)
    return out


def _print_text(results: dict[str, list[Finding]], errors: int, warnings: int) -> None:
    for path, findings in results.items():
        if not findings:
            print(f"{path}: ok")
            continue
        for f in findings:
            loc = f"{path}" + (f" [{f.package}]" if f.package else "")
            print(f"{loc}: {f.severity.upper()} {f.code} {f.message}")
    total = errors + warnings
    if total:
        print(f"\n{errors} error(s), {warnings} warning(s) across {len(results)} file(s)", file=sys.stderr)


def _print_json(results: dict[str, list[Finding]]) -> None:
    payload = {
        path: [
            {"code": f.code, "severity": f.severity, "package": f.package, "message": f.message}
            for f in findings
        ]
        for path, findings in results.items()
    }
    print(json.dumps(payload, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pylock-lint",
        description="Static CI check for PEP 751 pylock.toml: hash completeness, "
        "sdist-only builds, platform portability, and drift vs pyproject.toml.",
    )
    p.add_argument("paths", nargs="*", help="pylock.toml files or globs (default: ./pylock*.toml)")
    p.add_argument("--pyproject", metavar="PATH", help="check the lock is in sync with this pyproject.toml")
    p.add_argument("--require-cross-platform", action="store_true",
                   help="fail if committed wheels cover only one platform")
    p.add_argument("--strict", action="store_true", help="treat warnings as failures too")
    p.add_argument("--select", metavar="CODES", help="comma-separated rule codes to run exclusively")
    p.add_argument("--ignore", metavar="CODES", default="", help="comma-separated rule codes to skip")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--version", action="version", version=f"pylock-lint {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    select = {c.strip() for c in args.select.split(",") if c.strip()} if args.select else None
    ignore = {c.strip() for c in args.ignore.split(",") if c.strip()}

    files = _discover(args.paths)
    results: dict[str, list[Finding]] = {}
    parse_failed = False
    for path in files:
        try:
            lock = load_lockfile(path)
        except LockParseError as exc:
            parse_failed = True
            results[path] = [Finding("PL000", ERROR, None, str(exc))]
            continue
        findings = run_all(
            lock,
            pyproject_path=args.pyproject,
            require_cross_platform=args.require_cross_platform,
        )
        results[path] = _filter(findings, select, ignore)

    errors = sum(1 for fs in results.values() for f in fs if f.severity == ERROR)
    warnings = sum(1 for fs in results.values() for f in fs if f.severity == WARNING)

    if args.format == "json":
        _print_json(results)
    else:
        _print_text(results, errors, warnings)

    if errors or parse_failed:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
