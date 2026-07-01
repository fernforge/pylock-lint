from pathlib import Path

import pytest

from pylock_lint.checks import run_all
from pylock_lint.cli import main
from pylock_lint.model import load_lockfile

FIX = Path(__file__).parent / "fixtures"


def codes(findings):
    return sorted({f.code for f in findings})


def test_clean_lock_has_no_findings():
    lock = load_lockfile(FIX / "clean.pylock.toml")
    findings = run_all(lock)
    assert findings == [], [f.message for f in findings]


def test_broken_lock_flags_expected_rules():
    lock = load_lockfile(FIX / "broken.pylock.toml")
    found = codes(run_all(lock))
    for expected in ("PL001", "PL002", "PL003", "PL013", "PL020"):
        assert expected in found, f"{expected} missing from {found}"


def test_missing_version_flagged(tmp_path):
    p = tmp_path / "pylock.toml"
    p.write_text(
        'lock-version = "1.0"\ncreated-by = "x"\n'
        '[[packages]]\nname = "foo"\n'
        '[[packages.wheels]]\nname = "foo-1-py3-none-any.whl"\n'
        'url = "u"\nhashes = { sha256 = "a" }\n'
    )
    found = codes(run_all(load_lockfile(p)))
    assert "PL015" in found


def test_unsupported_lock_version(tmp_path):
    p = tmp_path / "pylock.toml"
    p.write_text('lock-version = "2.0"\ncreated-by = "x"\n[[packages]]\nname="a"\n[packages.directory]\npath="."\n')
    found = codes(run_all(load_lockfile(p)))
    assert "PL012" in found


def test_mutually_exclusive_sources(tmp_path):
    p = tmp_path / "pylock.toml"
    p.write_text(
        'lock-version = "1.0"\ncreated-by = "x"\n'
        '[[packages]]\nname = "foo"\nversion = "1"\n'
        '[packages.sdist]\nurl = "u"\nhashes = { sha256 = "a" }\n'
        '[packages.vcs]\ntype = "git"\ncommit-id = "abc"\nurl = "u"\n'
    )
    found = codes(run_all(load_lockfile(p)))
    assert "PL011" in found


def test_pyproject_drift(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "app"\nrequires-python = ">=3.10"\n'
        'dependencies = ["requests>=2", "rich"]\n'
    )
    lock = tmp_path / "pylock.toml"
    lock.write_text(
        'lock-version = "1.0"\ncreated-by = "x"\nrequires-python = ">=3.9"\n'
        '[[packages]]\nname = "requests"\nversion = "2.31.0"\n'
        '[packages.directory]\npath = "."\n'
    )
    found = codes(run_all(load_lockfile(lock), pyproject_path=pyproject))
    assert "PL030" in found  # rich declared but not locked
    assert "PL031" in found  # requires-python mismatch


def test_require_cross_platform(tmp_path):
    p = tmp_path / "pylock.toml"
    p.write_text(
        'lock-version = "1.0"\ncreated-by = "x"\n'
        'environments = ["a", "b"]\n'
        '[[packages]]\nname = "numpy"\nversion = "1"\n'
        '[[packages.wheels]]\nname = "numpy-1-cp311-cp311-manylinux_x86_64.whl"\n'
        'url = "u"\nhashes = { sha256 = "a" }\n'
    )
    found = codes(run_all(load_lockfile(p), require_cross_platform=True))
    assert "PL021" in found


def test_cli_exit_codes(capsys):
    assert main([str(FIX / "clean.pylock.toml")]) == 0
    assert main([str(FIX / "broken.pylock.toml")]) == 1


def test_cli_json_format(capsys):
    main([str(FIX / "broken.pylock.toml"), "--format", "json"])
    out = capsys.readouterr().out
    assert '"code"' in out and "PL001" in out


def test_cli_ignore(capsys):
    # ignoring every error code should drop exit to 0 (warnings only, no --strict)
    rc = main([str(FIX / "broken.pylock.toml"), "--ignore", "PL001,PL003"])
    assert rc == 0


def test_parse_error(tmp_path, capsys):
    bad = tmp_path / "pylock.toml"
    bad.write_text("this is = = not toml")
    assert main([str(bad)]) == 1
