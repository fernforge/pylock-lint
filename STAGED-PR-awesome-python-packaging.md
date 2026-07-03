# STAGED PR — add pylock-lint to awesome-python-packaging

Status: READY TO SUBMIT. Operator-gated (needs a public_repo PAT to fork + push, or a manual
click-submit). Same gate/precedent as the mcp-conform awesome-list PR. Do NOT self-provision a
token. Do NOT re-ask while operator is away.

## Target
- Repo: https://github.com/flying-sheep/awesome-python-packaging
- Branch base: `master`  ·  File: `README.md`  ·  Section: `## Testing / Checking`
- Why this list: small, technical, packaging-specific; a "Testing / Checking" section exists;
  and there is NO PEP 751 / pylock validator listed in any awesome list yet — genuine gap, not
  self-promo. Entry is descriptive and matches the list's voice (cf. the `twine` entry, which
  has no config-file badge; pylock-lint validates pyproject.toml, it is not configured by it, so
  no ✅/❌ badge).

## Exact addition (insert after the `Coverage.py` entry, at the end of "Testing / Checking")
```markdown
- [pylock-lint](https://github.com/fernforge/pylock-lint)

  Static CI check for [PEP 751](https://peps.python.org/pep-0751/) `pylock.toml` lockfiles.
  Flags wheels with missing hashes, sdist-only packages, single-platform locks that pin
  platform-specific wheels, and drift between the lock and `pyproject.toml` — the failures that
  only surface once a teammate on another OS runs `pip install`. Ships as a CLI and a GitHub
  Action.
```

## PR title
Add pylock-lint (PEP 751 pylock.toml checker) to Testing / Checking

## PR body
Adds [pylock-lint](https://github.com/fernforge/pylock-lint) under **Testing / Checking**.

PEP 751's `pylock.toml` became installable via `pip install -r pylock.toml` in pip 26.1
(April 2026), but pip's generated locks are single-platform / single-Python and skip
environment markers, so a committed lock can pass CI on Linux and then fail (or silently build
from source) on a teammate's Windows/macOS machine. There isn't a standalone checker for this in
the list yet — `packaging` only parses the schema and `pip-audit` only scans CVEs. pylock-lint
statically flags missing hashes, sdist-only entries, single-platform locks that pin
platform-specific wheels, and drift vs `pyproject.toml`. MIT, runs as a CLI and a GitHub Action.

## To submit (operator, when a public_repo PAT is available)
1. Fork flying-sheep/awesome-python-packaging → fernforge.
2. Branch `add-pylock-lint`; apply the addition above to README.md.
3. Commit: "Add pylock-lint (PEP 751 pylock.toml checker)"; push; open PR with the title/body above.
