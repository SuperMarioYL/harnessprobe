"""OpenAI-compatible vendor adapter.

Single external-I/O seam: probe DeepSeek / Qwen (DashScope) / Kimi (Moonshot)
endpoints that all expose an OpenAI-compatible ``/chat/completions`` API. The
adapter applies a :class:`~harnessprobe.profile.HarnessProfile` to a request —
system prompt, temperature, max_tokens, stop tokens, decoding knobs, and the
reasoning-effort lever where the model accepts it.

When no API key is present (e.g. CI / demo / tests), the adapter transparently
falls back to a deterministic **stub** that emits a plausible answer string, so
the runner/matrix/report pipeline can be exercised end-to-end without secrets.
This is the only place that touches the network.
"""

from __future__ import annotations

import os
import re
import zlib
from dataclasses import dataclass
from typing import Any

import httpx

from harnessprobe.profile import HarnessProfile

# Default OpenAI-compatible base URLs per vendor (override with --base-url).
DEFAULT_BASE_URLS: dict[str, str] = {
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "kimi": "https://api.moonshot.cn/v1",
}

# Canonical env-var name per vendor (schema-smoke-verified).
DEFAULT_API_KEY_ENV: dict[str, str] = {
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "kimi": "MOONSHOT_API_KEY",
}


@dataclass
class CompletionResult:
    """The raw output of one completion call."""

    text: str
    finish_reason: str
    raw: dict[str, Any]
    stub: bool = False

    @property
    def usage(self) -> dict[str, int]:
        u = self.raw.get("usage") or {}
        return {k: int(v) for k, v in u.items() if isinstance(v, (int, float))}


def stable_gate(vendor: str, problem_id: str) -> int:
    """Process-independent digest of ``(vendor, problem_id)`` in ``[0, 10000)``.

    The stub's correctness pattern must be identical across CLI invocations
    (same inputs → same outputs), so it is keyed on ``zlib.crc32`` rather than
    the builtin ``hash()``, which is salt-randomized per process.
    """
    return zlib.crc32(f"{vendor}:{problem_id}".encode()) % 10000


class OpenAICompatAdapter:
    """Apply a HarnessProfile to an OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        profile: HarnessProfile,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.profile = profile
        self.timeout = timeout
        vendor = profile.vendor
        self.base_url = (
            base_url
            or profile.base_url
            or DEFAULT_BASE_URLS.get(vendor, "")
        )
        env_name = profile.api_key_env or DEFAULT_API_KEY_ENV.get(vendor, "")
        self.api_key = api_key if api_key is not None else (
            os.environ.get(env_name, "") if env_name else ""
        )
        self._env_name = env_name

    # -- public ------------------------------------------------------------

    @property
    def is_stub(self) -> bool:
        return not self.api_key or not self.base_url

    def complete(self, prompt: str, *, context: dict[str, Any] | None = None) -> CompletionResult:
        """Run one chat completion with the profile applied; stub if no key.

        ``context`` (optional, stub-only) carries the expected answer + problem
        index so the deterministic stub can produce a realistic, vendor-
        differentiated accuracy spread for demos. Live mode ignores it.
        """
        if self.is_stub:
            return self._stub_complete(prompt, context=context or {})
        return self._live_complete(prompt)

    # -- live --------------------------------------------------------------

    def _build_payload(self, prompt: str) -> dict[str, Any]:
        p = self.profile
        messages: list[dict[str, str]] = []
        if p.system_prompt:
            messages.append({"role": "system", "content": p.system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": p.model_name,
            "messages": messages,
            "temperature": p.temperature,
            "max_tokens": p.max_tokens,
        }
        if p.stop_tokens:
            payload["stop"] = p.stop_tokens
        # merge decoding knobs (top_p, presence_penalty, …) at top level
        for k, v in p.decoding.items():
            if k not in payload:
                payload[k] = v
        if p.reasoning_effort:
            # reasoning-effort is the reasoning-model harness lever; only some
            # vendors expose it as a top-level field — send it and let the
            # endpoint ignore what it doesn't recognise.
            payload["reasoning_effort"] = p.reasoning_effort
        return payload

    def _live_complete(self, prompt: str) -> CompletionResult:
        payload = self._build_payload(prompt)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = msg.get("content") or ""
        finish = choice.get("finish_reason", "stop")
        return CompletionResult(text=text, finish_reason=finish, raw=data)

    # -- stub (deterministic, no secrets needed) ---------------------------

    # Vendor-differentiated deterministic "accuracy" for the stub spread.
    # This is NOT a real score — it only makes the stub demo read like a real
    # GapMatrix. Live mode (with API keys) overrides it with real completions.
    _STUB_ACCURACY = {"deepseek": 0.62, "qwen": 0.52, "kimi": 0.47}

    def _stub_complete(
        self, prompt: str, *, context: dict[str, Any] | None
    ) -> CompletionResult:
        """Deterministic plausible answer for offline / CI / demo runs.

        Uses the expected answer (passed via ``context``) + a per-(vendor,
        problem-id) stable digest to produce an identical, vendor-differentiated
        accuracy spread on every invocation, so the demo GapMatrix reads
        realistically and stays reproducible across processes. Live mode
        ignores this path entirely. All stub outputs are clearly flagged.
        """
        ctx = context or {}
        expected = ctx.get("expected")
        pid = ctx.get("problem_id", "")
        vendor = self.profile.vendor
        # deterministic correctness gate keyed on (vendor, problem_id)
        gate = stable_gate(vendor, pid) / 10000.0
        target_acc = self._STUB_ACCURACY.get(vendor, 0.5)
        correct = gate < target_acc and expected is not None
        if correct:
            ans = str(expected)
        elif expected is not None:
            # deterministic wrong answer ≠ expected
            wrong = (int(expected) + 1 + (stable_gate(vendor, pid) % 97)) % 1000
            ans = str(wrong)
        else:
            ans = str(zlib.crc32(prompt.encode("utf-8")) % 1000)
        effort = self.profile.reasoning_effort or "none"
        text = (
            f"<reasoning>applying {vendor} harness profile "
            f"(stub mode, reasoning_effort={effort}, temperature="
            f"{self.profile.temperature})</reasoning>\n"
            f"The answer is \\boxed{{{ans}}}."
        )
        raw = {
            "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": len(prompt) // 4,
                "completion_tokens": 40,
                "total_tokens": len(prompt) // 4 + 40,
            },
            "stub": True,
            "model": self.profile.model_name,
            "deterministic": True,
        }
        return CompletionResult(text=text, finish_reason="stop", raw=raw, stub=True)
