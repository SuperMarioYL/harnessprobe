"""v0.2.0 fix regressions — cross-process stub determinism + CLI error contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import zlib
from pathlib import Path

from typer.testing import CliRunner

from harnessprobe.adapters.openai_compat import stable_gate
from harnessprobe.cli import app

ROOT = Path(__file__).resolve().parent.parent
VENDOR_KEY_ENVS = ("DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "MOONSHOT_API_KEY")

runner = CliRunner()


class TestStubDeterminism:
    def test_stub_scores_stable_across_processes(self, tmp_path: Path) -> None:
        """Two separate CLI processes must produce identical stub scores.

        v0.1.0 keyed the stub gate on builtin hash() (salt-randomized per
        process), so every invocation produced a different GapMatrix despite
        the documented determinism promise.
        """
        scores = []
        for i in range(2):
            state = tmp_path / f"state{i}.json"
            env = {k: v for k, v in os.environ.items() if k not in VENDOR_KEY_ENVS}
            r = subprocess.run(
                [
                    sys.executable, "-m", "harnessprobe.cli",
                    "match", "--models", "kimi-k3", "--n", "30",
                    "--save", str(state),
                ],
                capture_output=True, text=True, cwd=ROOT, env=env, check=False,
            )
            assert r.returncode == 0, r.stderr
            run = json.loads(state.read_text())["runs"][0]
            scores.append((run["matched_score"], run["n_correct"]))
        assert scores[0] == scores[1]

    def test_stub_gate_matches_reference_digest(self) -> None:
        """The gate is the documented crc32 digest, not a per-process hash."""
        assert stable_gate("kimi", "aime-2024-01") == (
            zlib.crc32(b"kimi:aime-2024-01") % 10000
        )
        # stable and vendor-differentiated
        assert stable_gate("deepseek", "aime-2024-01") != stable_gate("kimi", "aime-2024-01")


class TestCLIErrorContracts:
    def test_unknown_bench_is_clean_error(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["match", "--models", "deepseek-v4", "--bench", "mmlu", "--n", "3",
             "--save", str(tmp_path / "s.json")],
        )
        assert result.exit_code == 2
        assert "mmlu" in result.output
        assert "aime" in result.output
        assert "Traceback" not in result.output

    def test_nonpositive_n_is_clean_error(self, tmp_path: Path) -> None:
        for bad in ("-5", "0"):
            result = runner.invoke(
                app,
                ["match", "--models", "deepseek-v4", "--n", bad,
                 "--save", str(tmp_path / "s.json")],
            )
            assert result.exit_code == 2, f"--n {bad} should exit 2"
            assert "n must be >= 1" in result.output
            assert "Traceback" not in result.output

    def test_unknown_model_still_exit_2(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["match", "--models", "no-such-model", "--n", "3",
             "--save", str(tmp_path / "s.json")],
        )
        assert result.exit_code == 2
        assert "Traceback" not in result.output
