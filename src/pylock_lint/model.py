"""Loading and light structural modeling of pylock.toml (PEP 751)."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


class LockParseError(Exception):
    """Raised when a pylock.toml file cannot be read or parsed as TOML."""


@dataclass
class Lockfile:
    path: Path
    data: dict[str, Any]

    @property
    def lock_version(self) -> str | None:
        v = self.data.get("lock-version")
        return v if isinstance(v, str) else None

    @property
    def created_by(self) -> str | None:
        v = self.data.get("created-by")
        return v if isinstance(v, str) else None

    @property
    def environments(self) -> list[str]:
        v = self.data.get("environments")
        return list(v) if isinstance(v, list) else []

    @property
    def requires_python(self) -> str | None:
        v = self.data.get("requires-python")
        return v if isinstance(v, str) else None

    @property
    def packages(self) -> list[dict[str, Any]]:
        v = self.data.get("packages")
        return [p for p in v if isinstance(p, dict)] if isinstance(v, list) else []


def load_lockfile(path: str | Path) -> Lockfile:
    p = Path(path)
    try:
        raw = p.read_bytes()
    except OSError as exc:
        raise LockParseError(f"cannot read {p}: {exc}") from exc
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise LockParseError(f"{p}: invalid TOML: {exc}") from exc
    if not isinstance(data, dict):
        raise LockParseError(f"{p}: top level is not a table")
    return Lockfile(path=p, data=data)


# Source-type keys that are mutually exclusive per PEP 751 (sdist+wheels count as one).
SOURCE_KEYS = ("vcs", "directory", "archive", "sdist", "wheels")


def package_source_types(pkg: dict[str, Any]) -> list[str]:
    """Return which distinct source-type groups a package declares."""
    types: list[str] = []
    if "vcs" in pkg:
        types.append("vcs")
    if "directory" in pkg:
        types.append("directory")
    if "archive" in pkg:
        types.append("archive")
    if "sdist" in pkg or "wheels" in pkg:
        types.append("sdist+wheels")
    return types
