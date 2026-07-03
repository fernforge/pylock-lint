# Approve & publish the pylock-lint educational dev.to post?

**Channel:** dev.to (single post), API-publishable via `DEVTO_API_KEY` (already wired).

**Draft (verbatim title + body):** attached — `DRAFT-devto-pylock-audit.md`.

**Title:** "Your committed pylock.toml can pass CI and still break a teammate's install"

**Tags:** `python`, `packaging`, `ci`, `devops` (all 4 slots = discovery tags; no `ABotWroteThis` tag, per policy the footer line carries the disclosure instead).

**Disclosure line (verbatim, builder-voice footer):**
> Written by an autonomous software agent. I build and maintain Python tooling, and while working on lockfile checks I packaged the audit above into an open-source linter called pylock-lint. The stdlib script here is complete on its own — you don't need the tool to run any of it.

## Why it's on-policy (dev.to AI-assisted-content rules)
- **Genuinely educational, stands alone.** The post hands the reader a complete ~30-line stdlib `tomllib` audit script for the four pylock.toml failure classes (unhashed wheels, sdist-only, no-source, single-env platform-wheel lock). They get 100% of the value without ever installing anything.
- **No self-promotion / no funnel abuse.** `pylock-lint` is named exactly once, non-CTA, inside the disclosure line. No install CTA, no repeated product links, not an announcement.
- **Factually verified.** The load-bearing hook is a direct quote from pip's own docs ("The generated lock file is only guaranteed to be valid for the current python version and platform" — pip.pypa.io/en/stable/cli/pip_lock/). PEP 751 timeline and pip 25.1/26.1 versions verified via web. Every code snippet was run against a real broken fixture and its output pasted in.

## What it's meant to achieve
The reach lever for a dev tool. pylock-lint is live on PyPI (first ~123 downloads/day, mostly noise) with 0 GitHub stars. This post targets exactly the teams who feel the pain — pip-lock committers adopting PEP 751 — with a technique that stands on its own, and lets the tool's existence surface once. It's the only autonomous, measurable growth lever for this pursuit that isn't PAT-gated.

If declined: no post ships, draft is kept. The alternative reach move (curated-list PR to awesome-python-packaging) remains staged and needs a `public_repo` PAT you hold.
