"""v0.2.0 profile tooling — `harnessprobe profile show / validate / probe`."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from harnessprobe.cli import app

runner = CliRunner()

VALID_YAML = """\
vendor: qwen
model_id: local-1
model_name: Qwen3-8B-Instruct
system_prompt: "Answer carefully."
temperature: 0.0
max_tokens: 512
stop_tokens: ["<|im_end|>"]
base_url: "https://vllm.internal:8000/v1"
api_key_env: INTERNAL_QWEN_KEY
provenance:
  - "internal vLLM deployment manifest"
  - "vendor model card 2026-08"
published_score:
  aime: 61.2
"""

BAD_YAML = """\
vendor: openai
model_id: gpt-x
model_name: gpt-x
system_prompt: "hi"
"""


class TestProfileShow:
    def test_profile_show_prints_fields(self) -> None:
        result = runner.invoke(app, ["profile", "show", "deepseek-v4"])
        assert result.exit_code == 0, result.output
        assert "vendor" in result.output
        assert "deepseek" in result.output
        assert "deepseek-v4-pro-0813" in result.output
        assert "system_prompt" in result.output
        assert "provenance" in result.output
        assert "published_score" in result.output
        assert "aime" in result.output

    def test_profile_show_unknown_key_exits_2(self) -> None:
        result = runner.invoke(app, ["profile", "show", "no-such-model"])
        assert result.exit_code == 2
        assert "Traceback" not in result.output


class TestProfileValidate:
    def test_profile_validate_ok(self, tmp_path: Path) -> None:
        path = tmp_path / "custom.yaml"
        path.write_text(VALID_YAML, encoding="utf-8")
        result = runner.invoke(app, ["profile", "validate", str(path)])
        assert result.exit_code == 0, result.output
        assert "OK" in result.output
        assert "Qwen3-8B-Instruct" in result.output

    def test_profile_validate_bad_yaml(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text(BAD_YAML, encoding="utf-8")
        result = runner.invoke(app, ["profile", "validate", str(path)])
        assert result.exit_code == 2
        assert "vendor must be one of" in result.output
        assert "Traceback" not in result.output

    def test_profile_validate_missing_file_exits_2(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["profile", "validate", str(tmp_path / "nope.yaml")])
        assert result.exit_code == 2
        assert "not found" in result.output


class TestProfileProbe:
    def test_profile_probe_stub_reports_no_key(self, monkeypatch) -> None:
        for env in ("DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "MOONSHOT_API_KEY"):
            monkeypatch.delenv(env, raising=False)
        result = runner.invoke(app, ["profile", "probe", "kimi-k3"])
        assert result.exit_code == 0, result.output
        assert "no API key" in result.output
        assert "MOONSHOT_API_KEY" in result.output

    def test_profile_probe_unreachable_endpoint(self, monkeypatch) -> None:
        monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
        result = runner.invoke(
            app,
            ["profile", "probe", "qwen3-8", "--base-url", "http://127.0.0.1:9/v1"],
        )
        assert result.exit_code == 4, result.output
        assert "probe failed" in result.output
        assert "Traceback" not in result.output

    def test_profile_probe_unknown_key_exits_2(self) -> None:
        result = runner.invoke(app, ["profile", "probe", "no-such-model"])
        assert result.exit_code == 2
