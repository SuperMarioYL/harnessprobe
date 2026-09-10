"""Version lockstep — every version surface reports the same version."""

from __future__ import annotations

import tomllib
from pathlib import Path

from typer.testing import CliRunner

import harnessprobe
from harnessprobe.cli import app

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = "0.2.0"

runner = CliRunner()


def test_version_lockstep() -> None:
    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    result = runner.invoke(app, ["version"])

    assert version_file == EXPECTED
    assert pyproject["project"]["version"] == EXPECTED
    assert harnessprobe.__version__ == EXPECTED
    assert result.exit_code == 0
    assert EXPECTED in result.output


def test_changelog_has_sections() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.1.0]" in text
    assert "## [0.2.0]" in text
    # the 0.2.0 section names the fix and feature work
    assert "deterministic" in text.lower()
    assert "profile" in text.lower()
