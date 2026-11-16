"""v0.4.0 fix regressions — state/repro fidelity and failure visibility."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from harnessprobe.adapters.openai_compat import CompletionResult
from harnessprobe.cli import app

ROOT = Path(__file__).resolve().parent.parent

runner = CliRunner()

CUSTOM_PROFILE = """vendor: deepseek
model_id: custom-ds-9000
model_name: custom-ds-9000-endpoint
system_prompt: "Integrator-supplied harness profile."
stop_tokens: ["<END>"]
temperature: 0.3
max_tokens: 1024
published_score:
  aime: 88.8
provenance:
  - "integrator-provided custom profile"
"""


def _match_custom(tmp_path: Path, n: int = 3) -> tuple[Path, Path]:
    profile = tmp_path / "custom.yaml"
    profile.write_text(CUSTOM_PROFILE, encoding="utf-8")
    state = tmp_path / "state.json"
    r = runner.invoke(
        app,
        ["match", "--models", str(profile), "--n", str(n), "--save", str(state)],
    )
    assert r.exit_code == 0, r.output
    return profile, state


# ---------------------------------------------------------------------------
# m13 — state is a faithful contract: the profile source and endpoint a run
# used survive into state, repro rebuilds that run (not the vendor's bundled
# profile), and state/repro input errors are clean.
# ---------------------------------------------------------------------------


class TestStateAndReproFidelity:
    def test_state_records_profile_source_and_endpoint(self, tmp_path: Path) -> None:
        profile, state = _match_custom(tmp_path)
        row = json.loads(state.read_text(encoding="utf-8"))["matrix"][0]
        assert row["profile"] == str(profile)
        assert row["base_url"] == "https://api.deepseek.com/v1"

    def test_repro_uses_recorded_profile(self, tmp_path: Path) -> None:
        """v0.3.0 silently substituted the bundled deepseek profile here."""
        _, state = _match_custom(tmp_path)
        out = tmp_path / "repro.zip"
        r = runner.invoke(app, ["repro", "--state", str(state), "--out", str(out)])
        assert r.exit_code == 0, r.output
        with zipfile.ZipFile(out) as zf:
            manifest = json.loads(zf.read("manifest.json"))
            profile_txt = zf.read("models/deepseek_custom-ds-9000/profile.txt").decode()
        assert manifest["models"][0]["model_id"] == "custom-ds-9000"
        assert "custom-ds-9000-endpoint" in profile_txt
        assert "integrator-provided custom profile" in profile_txt

    def test_repro_missing_recorded_profile_is_clean_error(self, tmp_path: Path) -> None:
        profile, state = _match_custom(tmp_path)
        profile.unlink()
        out = tmp_path / "repro.zip"
        r = runner.invoke(app, ["repro", "--state", str(state), "--out", str(out)])
        assert r.exit_code == 2
        assert "Traceback" not in r.output
        assert not out.exists()  # no package substituted from another profile

    def test_repro_keeps_recorded_stub_mode(self, tmp_path: Path, monkeypatch) -> None:
        _, state = _match_custom(tmp_path)
        # A key appearing later must not turn a recorded stub run into a live one.
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-not-used")
        out = tmp_path / "repro.zip"
        r = runner.invoke(app, ["repro", "--state", str(state), "--out", str(out)])
        assert r.exit_code == 0, r.output
        with zipfile.ZipFile(out) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert manifest["models"][0]["stub"] is True

    def test_repro_recorded_live_run_without_key_is_clean_error(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        state = tmp_path / "state.json"
        state.write_text(
            json.dumps(
                {
                    "version": "0.4.0",
                    "bench": "aime",
                    "n_problems": 1,
                    "all_stub": False,
                    "matrix": [
                        {
                            "vendor": "deepseek",
                            "model_id": "deepseek-v4-pro-0813",
                            "bench": "aime",
                            "published_score": 79.8,
                            "matched_score": 0.0,
                            "n_correct": 0,
                            "n_problems": 1,
                            "gap": -79.8,
                            "stub": False,
                            "profile": "deepseek-v4",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        out = tmp_path / "repro.zip"
        r = runner.invoke(app, ["repro", "--state", str(state), "--out", str(out)])
        assert r.exit_code == 3
        assert "no API key" in r.output
        assert not out.exists()

    def test_report_malformed_state_is_clean_error(self, tmp_path: Path) -> None:
        state = tmp_path / "bad.json"
        state.write_text(json.dumps({"matrix": [{"vendor": "deepseek"}]}), encoding="utf-8")
        r = runner.invoke(app, ["report", "--state", str(state), "--out", str(tmp_path / "r.html")])
        assert r.exit_code == 2
        assert "Traceback" not in r.output
        assert "missing model_id" in r.output

    def test_repro_invalid_json_state_is_clean_error(self, tmp_path: Path) -> None:
        state = tmp_path / "bad.json"
        state.write_text("not json", encoding="utf-8")
        r = runner.invoke(app, ["repro", "--state", str(state), "--out", str(tmp_path / "r.zip")])
        assert r.exit_code == 2
        assert "Traceback" not in r.output


# ---------------------------------------------------------------------------
# m14 — endpoint failure must never masquerade as model performance. At v0.3.0
# a run whose every completion raised printed a live 0.00 % row, a "largest
# harness inflation" claim, and exited 0.
# ---------------------------------------------------------------------------


class _AllFailAdapter:
    is_stub = False

    def __init__(self, profile, *, base_url=None, api_key=None, timeout=120.0):
        self.profile = profile
        self.base_url = base_url or ""

    def complete(self, prompt, *, context=None):
        raise RuntimeError("connection refused")


class _FirstCallFailsAdapter:
    is_stub = False

    def __init__(self, profile, *, base_url=None, api_key=None, timeout=120.0):
        self.profile = profile
        self.base_url = base_url or ""

    def complete(self, prompt, *, context=None):
        if context and context.get("index") == 0:
            raise RuntimeError("connection refused")
        return CompletionResult(
            text=f"\\boxed{{{context['expected']}}}",
            finish_reason="stop",
            raw={},
        )


class TestFailureVisibility:
    def test_total_failure_exits_5_and_makes_no_inflation_claim(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr("harnessprobe.runner.OpenAICompatAdapter", _AllFailAdapter)
        state = tmp_path / "state.json"
        html = tmp_path / "report.html"
        r = runner.invoke(
            app,
            [
                "match", "--models", "deepseek-v4", "--n", "3",
                "--save", str(state), "--html", str(html),
            ],
        )
        assert r.exit_code == 5, r.output
        assert "Endpoint failures" in r.output
        assert "Largest harness inflation" not in r.output
        data = json.loads(state.read_text(encoding="utf-8"))
        assert data["matrix"][0]["n_failed"] == 3
        text = html.read_text(encoding="utf-8")
        assert "3/3 completions failed" in text
        assert "Largest harness inflation" not in text

    def test_partial_failure_visible_but_scored(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "harnessprobe.runner.OpenAICompatAdapter", _FirstCallFailsAdapter
        )
        state = tmp_path / "state.json"
        r = runner.invoke(
            app,
            ["match", "--models", "deepseek-v4", "--n", "3", "--save", str(state)],
        )
        assert r.exit_code == 0, r.output
        assert "Endpoint failures" in r.output
        row = json.loads(state.read_text(encoding="utf-8"))["matrix"][0]
        assert row["n_failed"] == 1
        assert row["n_correct"] == 2
        assert row["matched_score"] == 66.67  # denominator unchanged: 2/3

    def test_state_and_report_carry_failed_count(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr("harnessprobe.runner.OpenAICompatAdapter", _AllFailAdapter)
        state = tmp_path / "state.json"
        runner.invoke(
            app,
            ["match", "--models", "deepseek-v4", "--n", "3", "--save", str(state)],
        )
        out = tmp_path / "rendered.html"
        r = runner.invoke(app, ["report", "--state", str(state), "--out", str(out)])
        assert r.exit_code == 0, r.output
        text = out.read_text(encoding="utf-8")
        assert "Endpoint failures" in text
        assert "3/3 completions failed" in text

    def test_stub_run_reports_zero_failures(self, tmp_path: Path) -> None:
        state = tmp_path / "state.json"
        r = runner.invoke(
            app,
            ["match", "--models", "kimi-k3", "--n", "3", "--save", str(state)],
        )
        assert r.exit_code == 0, r.output
        row = json.loads(state.read_text(encoding="utf-8"))["matrix"][0]
        assert row["n_failed"] == 0
        assert "Endpoint failures" not in r.output
