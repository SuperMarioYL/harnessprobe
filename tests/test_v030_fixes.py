"""v0.3.0 fix regressions — release assets, error grading, state provenance."""

from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from harnessprobe.cli import app
from harnessprobe.profile import load_profile
from harnessprobe.runner import run_match

ROOT = Path(__file__).resolve().parent.parent

runner = CliRunner()


# ---------------------------------------------------------------------------
# m8 — the release workflow must attach dist files to the GitHub Release.
# At v0.2.0 the workflow only called actions/upload-artifact (workflow artifact
# store), so releases/latest carried zero assets while CI was green.
# ---------------------------------------------------------------------------

RELEASE_WORKFLOW = (ROOT / ".github" / "workflows" / "release.yml").read_text(
    encoding="utf-8"
)


class TestReleaseWorkflowAttachesAssets:
    def test_release_job_exists_and_needs_build(self) -> None:
        m = re.search(r"^  release:\n(?:    .*\n|\n)*?    needs: build\n", RELEASE_WORKFLOW, re.M)
        assert m, "release.yml must define a `release` job that `needs: build`"

    def test_release_job_downloads_and_uploads_to_the_release(self) -> None:
        assert "actions/download-artifact" in RELEASE_WORKFLOW
        assert "gh release upload" in RELEASE_WORKFLOW, (
            "dist files must be attached to the GitHub Release, "
            "not only to the workflow artifact store"
        )


# ---------------------------------------------------------------------------
# m9 — failed completions are never graded. At v0.2.0 the error string was fed
# to _extract_int, so digits inside e.g. "rate-limited, retry 6" could be
# graded as a correct answer.
# ---------------------------------------------------------------------------


class _FailingAdapter:
    """Simulates a live endpoint whose exception message contains digits."""

    is_stub = False

    def __init__(self, profile, *, base_url=None, api_key=None, timeout=120.0):
        self.profile = profile

    def complete(self, prompt, *, context=None):
        raise RuntimeError("moonshot rate-limited, retry 6")


class _BoxedAdapter:
    """Simulates a successful live completion with a boxed answer."""

    is_stub = False

    def __init__(self, profile, *, base_url=None, api_key=None, timeout=120.0):
        self.profile = profile

    def complete(self, prompt, *, context=None):
        from harnessprobe.adapters.openai_compat import CompletionResult

        return CompletionResult(
            text="...reasoning... The answer is \\boxed{72}.",
            finish_reason="stop",
            raw={},
        )


class TestFailedCompletionsNeverGraded:
    def test_error_text_is_not_extracted_as_answer(self, monkeypatch) -> None:
        # aime-2024-02 expects 6; the error message ends in "retry 6".
        # v0.2.0 graded that as correct (verified repro: matched 50.0 on n=2).
        monkeypatch.setattr("harnessprobe.runner.OpenAICompatAdapter", _FailingAdapter)
        run = run_match(load_profile("kimi-k3"), bench="aime", n=2)
        assert all(r.failed for r in run.results)
        assert all(r.guessed is None for r in run.results)
        assert all(not r.correct for r in run.results)

    def test_all_failed_run_scores_zero(self, monkeypatch) -> None:
        monkeypatch.setattr("harnessprobe.runner.OpenAICompatAdapter", _FailingAdapter)
        run = run_match(load_profile("kimi-k3"), bench="aime", n=5)
        assert run.n_correct == 0
        assert run.matched_score == 0.0
        assert run.stub is False  # live adapter, just broken

    def test_error_string_kept_for_audit(self, monkeypatch) -> None:
        monkeypatch.setattr("harnessprobe.runner.OpenAICompatAdapter", _FailingAdapter)
        run = run_match(load_profile("kimi-k3"), bench="aime", n=1)
        assert "[runner error:" in run.results[0].response
        assert "rate-limited" in run.results[0].response

    def test_successful_completions_still_graded(self, monkeypatch) -> None:
        monkeypatch.setattr("harnessprobe.runner.OpenAICompatAdapter", _BoxedAdapter)
        run = run_match(load_profile("deepseek-v4"), bench="aime", n=1)
        res = run.results[0]
        assert res.failed is False
        assert res.guessed == 72
        assert res.correct is True
        assert run.n_correct == 1


# ---------------------------------------------------------------------------
# m10 — match persists harness assumptions + provenance, and report --state
# re-renders the provenance trail (v0.2.0 dropped it entirely on that path).
# ---------------------------------------------------------------------------


class TestStateProvenanceReport:
    def test_state_carries_harness_and_provenance(self, tmp_path: Path) -> None:
        state = tmp_path / "state.json"
        r = runner.invoke(
            app,
            ["match", "--models", "deepseek-v4", "--n", "3", "--save", str(state)],
        )
        assert r.exit_code == 0, r.output
        data = json.loads(state.read_text(encoding="utf-8"))
        row = data["matrix"][0]
        harness = row["harness"]
        assert harness["model_name"] == "deepseek-chat"
        assert harness["reasoning_effort"] == "high"
        assert harness["temperature"] == 0.0
        assert harness["max_tokens"] == 8192
        assert "<｜end▁of▁sentence｜>" in harness["stop_tokens"]
        assert any("r/LocalLLaMA" in src for src in harness["provenance"])

    def test_report_from_state_keeps_provenance_trail(self, tmp_path: Path) -> None:
        state = tmp_path / "state.json"
        out = tmp_path / "report.html"
        r = runner.invoke(
            app,
            ["match", "--models", "deepseek-v4", "--n", "3", "--save", str(state)],
        )
        assert r.exit_code == 0, r.output
        r2 = runner.invoke(app, ["report", "--state", str(state), "--out", str(out)])
        assert r2.exit_code == 0, r2.output
        html = out.read_text(encoding="utf-8")
        assert "Per-profile provenance trail" in html
        assert "r/LocalLLaMA" in html  # a provenance entry survives the round-trip
        assert "reasoning_effort" in html

    def test_legacy_state_without_harness_still_renders(self, tmp_path: Path) -> None:
        state = tmp_path / "legacy.json"
        state.write_text(
            json.dumps(
                {
                    "version": "0.2.0",
                    "bench": "aime",
                    "n_problems": 2,
                    "all_stub": True,
                    "matrix": [
                        {
                            "vendor": "deepseek",
                            "model_id": "deepseek-v4-pro-0813",
                            "bench": "aime",
                            "published_score": 79.8,
                            "matched_score": 33.33,
                            "n_correct": 1,
                            "n_problems": 2,
                            "gap": -46.47,
                            "stub": True,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        out = tmp_path / "report.html"
        r = runner.invoke(app, ["report", "--state", str(state), "--out", str(out)])
        assert r.exit_code == 0, r.output
        html = out.read_text(encoding="utf-8")
        # pre-v0.3.0 state has no assumptions to audit — no empty trail section
        assert "Per-profile provenance trail" not in html
        assert "33.33" in html  # scores still render
