"""Tests for HarnessProfile schema, the stdlib YAML loader, and profile loading."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from harnessprobe.profile import (
    HarnessProfile,
    ProfileError,
    ToolCallTemplate,
    list_profiles,
    load_profile,
    load_yaml,
)


# ---------------------------------------------------------------------------
# YAML loader (stdlib subset)
# ---------------------------------------------------------------------------

class TestYamlLoader:
    def test_simple_scalars(self) -> None:
        assert load_yaml('a: 1\nb: 2.5\nc: true\nd: "hi"\n') == {
            "a": 1, "b": 2.5, "c": True, "d": "hi"
        }

    def test_nested_dict(self) -> None:
        data = load_yaml("outer:\n  inner: 42\n  flag: true\n")
        assert data == {"outer": {"inner": 42, "flag": True}}

    def test_list_of_scalars(self) -> None:
        data = load_yaml('items:\n  - "x"\n  - 7\n  - y\n')
        assert data == {"items": ["x", 7, "y"]}

    def test_inline_flow_sequence(self) -> None:
        data = load_yaml('stops: ["a", "b", 3]\n')
        assert data == {"stops": ["a", "b", 3]}

    def test_comments_stripped(self) -> None:
        data = load_yaml("# header\nkey: val  # trailing\n# only comment\n")
        assert data == {"key": "val"}

    def test_multiline_escaped_string(self) -> None:
        data = load_yaml('msg: "line1\\nline2"\n')
        assert data == {"msg": "line1\nline2"}

    def test_empty(self) -> None:
        assert load_yaml("") == {}
        assert load_yaml("# only a comment\n") == {}

    def test_deeply_nested(self) -> None:
        data = load_yaml(
            "a:\n  b:\n    c:\n      d: 1\n"
        )
        assert data == {"a": {"b": {"c": {"d": 1}}}}


# ---------------------------------------------------------------------------
# HarnessProfile validation
# ---------------------------------------------------------------------------

class TestHarnessProfile:
    def _base(self) -> dict:
        return {
            "vendor": "deepseek",
            "model_id": "x-1",
            "model_name": "deepseek-chat",
            "system_prompt": "be careful",
            "stop_tokens": ["<|im_end|>"],
            "reasoning_effort": "high",
            "temperature": 0.0,
            "max_tokens": 8192,
            "decoding": {"top_p": 0.95},
            "provenance": ["reddit"],
            "published_score": {"aime": 79.8},
            "base_url": "https://api.deepseek.com/v1",
            "api_key_env": "DEEPSEEK_API_KEY",
        }

    def test_valid_profile(self) -> None:
        p = HarnessProfile.model_validate(self._base())
        assert p.vendor == "deepseek"
        assert p.reasoning_effort == "high"
        assert p.published_score == {"aime": 79.8}
        assert p.decoding == {"top_p": 0.95}

    def test_invalid_vendor_rejected(self) -> None:
        d = self._base()
        d["vendor"] = "openai"
        with pytest.raises(ValidationError):
            HarnessProfile.model_validate(d)

    def test_invalid_reasoning_effort_rejected(self) -> None:
        d = self._base()
        d["reasoning_effort"] = "turbo"
        with pytest.raises(ValidationError):
            HarnessProfile.model_validate(d)

    def test_none_reasoning_effort_ok(self) -> None:
        d = self._base()
        d["reasoning_effort"] = None
        p = HarnessProfile.model_validate(d)
        assert p.reasoning_effort is None

    def test_tool_call_template_defaults(self) -> None:
        t = ToolCallTemplate()
        assert t.style == "openai"
        assert t.schema_shape == {}


# ---------------------------------------------------------------------------
# Bundled profile loading (m1 + m2)
# ---------------------------------------------------------------------------

class TestBundledProfiles:
    def test_list_profiles_has_three(self) -> None:
        keys = list_profiles()
        assert sorted(keys) == ["deepseek-v4", "kimi-k3", "qwen3-8"]

    @pytest.mark.parametrize("key", ["deepseek-v4", "qwen3-8", "kimi-k3"])
    def test_load_each_profile(self, key: str) -> None:
        p = load_profile(key)
        assert p.vendor in {"deepseek", "qwen", "kimi"}
        assert p.model_id
        assert p.model_name
        assert p.system_prompt
        assert isinstance(p.stop_tokens, list) and len(p.stop_tokens) >= 1
        assert p.api_key_env in {"DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "MOONSHOT_API_KEY"}
        assert p.base_url.startswith("https://")
        # every stop token is a non-empty string
        for s in p.stop_tokens:
            assert isinstance(s, str) and len(s) > 0, f"empty stop token in {key}"

    @pytest.mark.parametrize("key", ["deepseek-v4", "qwen3-8", "kimi-k3"])
    def test_each_profile_has_published_aime(self, key: str) -> None:
        p = load_profile(key)
        assert "aime" in p.published_score
        assert 0 <= p.published_score["aime"] <= 100

    @pytest.mark.parametrize("key", ["deepseek-v4", "qwen3-8", "kimi-k3"])
    def test_each_profile_has_provenance(self, key: str) -> None:
        p = load_profile(key)
        assert len(p.provenance) >= 2, f"{key} needs >=2 provenance sources for audit"

    def test_unknown_key_raises(self) -> None:
        with pytest.raises(ProfileError):
            load_profile("nonexistent-model")
