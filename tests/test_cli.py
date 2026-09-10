"""CLI smoke tests — exercises the typer app end-to-end in stub mode."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from harnessprobe.cli import app

runner = CliRunner()


class TestCLI:
    def test_version(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.2.0" in result.output

    def test_profiles(self) -> None:
        result = runner.invoke(app, ["profiles"])
        assert result.exit_code == 0
        assert "deepseek-v4" in result.output
        assert "qwen3-8" in result.output
        assert "kimi-k3" in result.output

    def test_match_single_model(self, tmp_path: Path) -> None:
        state = tmp_path / "state.json"
        result = runner.invoke(
            app,
            ["match", "--models", "deepseek-v4", "--n", "5", "--save", str(state)],
        )
        assert result.exit_code == 0, result.output
        assert "GapMatrix" in result.output
        assert "deepseek" in result.output
        assert state.exists()
        data = json.loads(state.read_text())
        assert data["bench"] == "aime"
        assert len(data["matrix"]) == 1

    def test_match_all_three(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["match", "--models", "deepseek-v4,qwen3-8,kimi-k3", "--n", "5",
             "--save", str(tmp_path / "s.json")],
        )
        assert result.exit_code == 0, result.output
        assert "deepseek" in result.output
        assert "qwen" in result.output
        assert "kimi" in result.output

    def test_match_writes_html(self, tmp_path: Path) -> None:
        html_out = tmp_path / "report.html"
        result = runner.invoke(
            app,
            ["match", "--models", "kimi-k3", "--n", "5",
             "--html", str(html_out)],
        )
        assert result.exit_code == 0, result.output
        assert html_out.exists()
        assert "DOCTYPE" in html_out.read_text()

    def test_match_writes_repro(self, tmp_path: Path) -> None:
        repro_out = tmp_path / "repro.zip"
        result = runner.invoke(
            app,
            ["match", "--models", "qwen3-8", "--n", "5",
             "--repro", str(repro_out)],
        )
        assert result.exit_code == 0, result.output
        assert repro_out.exists()
        assert repro_out.stat().st_size > 0

    def test_report_from_state(self, tmp_path: Path) -> None:
        state = tmp_path / "state.json"
        runner.invoke(
            app,
            ["match", "--models", "deepseek-v4", "--n", "4", "--save", str(state)],
        )
        out = tmp_path / "report.html"
        result = runner.invoke(
            app, ["report", "--state", str(state), "--out", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_repro_from_state(self, tmp_path: Path) -> None:
        state = tmp_path / "state.json"
        runner.invoke(
            app,
            ["match", "--models", "kimi-k3", "--n", "4", "--save", str(state)],
        )
        out = tmp_path / "repro.zip"
        result = runner.invoke(
            app, ["repro", "--state", str(state), "--out", str(out)]
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_match_unknown_model_errors(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["match", "--models", "no-such-model", "--n", "3",
             "--save", str(tmp_path / "s.json")],
        )
        assert result.exit_code != 0

    def test_stub_mode_note(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["match", "--models", "deepseek-v4", "--n", "3",
             "--save", str(tmp_path / "s.json")],
        )
        assert result.exit_code == 0
        assert "STUB" in result.output.upper() or "stub" in result.output
