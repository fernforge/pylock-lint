# pylock-lint

A `pylock.toml` that installs cleanly on your laptop can still be broken: wheels with no
hashes, packages that only ship an sdist (so CI silently builds from source), or a lock
generated on Linux that has no wheels for the Windows runner it'll actually run on. Nothing in
the standard toolchain flags any of that before it reaches a teammate's machine.

`pylock-lint` is a static CI check for [PEP 751](https://peps.python.org/pep-0751/) lockfiles.
It reads a committed `pylock.toml`, reports the reproducibility and portability gaps, and exits
non-zero so a bad lock fails the build instead of the deploy.

```console
$ pylock-lint
pylock.toml [numpy]: ERROR PL001 wheel numpy-2.1.0-...-manylinux_2_17_x86_64.whl has no hashes
pylock.toml [somepkg]: WARNING PL002 sdist-only (no wheels): install must build from source...
pylock.toml: WARNING PL020 single-environment lock (no 'environments' declared) but it pins
  platform-specific wheels (numpy); installs on another OS/Python will fail or fall back to source

2 error(s), 1 warning(s) across 1 file(s)
$ echo $?
1
```

## Why this exists

pip 26.1 (April 2026) shipped `pip install -r pylock.toml`, and pip's own generated locks are
single-platform and single-Python — it "avoids some advanced features (like environment
markers) for now." uv and PDM export cross-platform locks; Poetry has none. So teams are
starting to commit `pylock.toml` to their repos, and the file's failure modes are exactly the
kind that don't show up until someone on a different OS runs `pip install`. `packaging` parses
the schema and `pip-audit` scans for CVEs; neither answers "is this lock actually reproducible
and portable?"

## Install

```console
pip install pylock-lint
```

Or run it without installing:

```console
pipx run pylock-lint
```

## Usage

```console
pylock-lint                          # lint ./pylock.toml (and pylock.*.toml)
pylock-lint path/to/pylock.toml      # lint a specific file or glob
pylock-lint --pyproject pyproject.toml   # also check the lock is in sync with declared deps
pylock-lint --require-cross-platform     # fail if wheels cover only one platform
pylock-lint --strict                 # treat warnings as failures too
pylock-lint --format json            # machine-readable output
pylock-lint --ignore PL002,PL020     # skip specific rules
```

Default exit code is `1` when any error-level finding is present, `0` otherwise. `--strict`
also fails on warnings.

## Checks

| Code  | Severity | What it catches |
|-------|----------|-----------------|
| PL001 | error    | An sdist, wheel, or archive with no `hashes` — the lock can't verify integrity. |
| PL002 | warning  | A package with an sdist but no wheels — install builds from source, which isn't byte-reproducible and needs a toolchain. |
| PL003 | error    | A package with no installable source at all. |
| PL010 | error    | A package entry missing its required `name`. |
| PL011 | error    | Mutually-exclusive source types on one package (PEP 751 allows exactly one). |
| PL012 | error    | Missing or unsupported `lock-version`. |
| PL013 | warning  | Missing `created-by` (provenance). |
| PL014 | warning  | Lockfile declares no packages. |
| PL015 | error    | A package with sdist/wheels missing its required `version`. |
| PL020 | warning  | Single-environment lock that pins platform-specific wheels — non-portable. |
| PL021 | error    | With `--require-cross-platform`: wheels cover only one platform. |
| PL030 | error    | With `--pyproject`: a dependency declared in `pyproject.toml` is absent from the lock. |
| PL031 | warning  | With `--pyproject`: `requires-python` disagrees between the two files. |

## GitHub Action

```yaml
- uses: fernforge/pylock-lint@v1
  with:
    paths: pylock.toml
    pyproject: pyproject.toml
    strict: "false"
```

The action installs the package and runs it against your committed lock on every push.

## What it does not do

No network calls. It won't fetch the referenced wheels or re-resolve your dependency graph — it
reads what's committed and checks the file against the spec and your `pyproject.toml`. That
keeps it fast and safe to run on untrusted branches, but it means PL030 checks presence, not
that every locked version satisfies every declared constraint.

## License

MIT
