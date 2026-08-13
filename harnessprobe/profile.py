"""HarnessProfile — the core primitive.

A ``HarnessProfile`` types up the per-vendor eval-harness assumptions that each
CN vendor's published score depends on but never publishes: system-prompt shape,
tool-call template, stop tokens, reasoning-effort, temperature, decoding knobs,
plus the provenance trail (reddit / official card / reverse-engineered) that
makes the assumption auditable for 信创 procurement due-diligence.

Profiles ship as static YAML under ``harnessprobe/profiles/`` and load into
validated pydantic objects. The YAML loader is dependency-free (stdlib only) —
it understands the controlled subset the seed profiles use, so no ``pyyaml``
dependency is required.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Minimal stdlib YAML loader (controlled subset — no pyyaml dependency)
# ---------------------------------------------------------------------------
# Supports: nested dicts, lists of scalars, inline flow ``[a, b]`` / ``{k: v}``,
# double/single-quoted scalars with C-style escapes, ints, floats, bools, null,
# ``#`` comments. Sufficient for the seed profile format; intentionally small.

_STR_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"',
    "'": "'", "0": "\0", "b": "\b", "f": "\f", "/": "/",
}


def _strip_comment(line: str) -> str:
    """Remove a trailing ``# comment`` that is not inside quotes."""
    in_single = in_double = False
    for i, c in enumerate(line):
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif c == "#" and not in_single and not in_double:
            return line[:i]
    return line


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        inner = s[1:-1]
        if s[0] == "'":
            return inner.replace("''", "'")
        out = []
        i = 0
        while i < len(inner):
            c = inner[i]
            if c == "\\" and i + 1 < len(inner):
                nxt = inner[i + 1]
                out.append(_STR_ESCAPES.get(nxt, nxt))
                i += 2
            else:
                out.append(c)
                i += 1
        return "".join(out)
    return s


def _scalar(s: str) -> Any:
    s = s.strip()
    if s == "":
        return None
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return _unquote(s)
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "none", "~", ""):
        return None
    # inline flow sequence / mapping
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_scalar(p) for p in _split_flow(inner)]
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1].strip()
        if not inner:
            return {}
        out: dict[str, Any] = {}
        for part in _split_flow(inner):
            k, _, v = part.partition(":")
            out[k.strip()] = _scalar(v.strip())
        return out
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s  # bare string


def _split_flow(s: str) -> list[str]:
    """Split a flow body on top-level commas (respecting quotes)."""
    parts: list[str] = []
    depth = 0
    in_single = in_double = False
    cur: list[str] = []
    for c in s:
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if c in "[{":
                depth += 1
            elif c in "]}":
                depth -= 1
            elif c == "," and depth == 0:
                parts.append("".join(cur))
                cur = []
                continue
        cur.append(c)
    if cur:
        parts.append("".join(cur))
    return parts


def _parse_node(lines: list[str], idx: int, indent: int) -> tuple[Any, int]:
    """Parse a dict or list node starting at ``idx`` with base ``indent``.

    Returns ``(value, next_index)``.
    """
    if idx >= len(lines):
        return {}, idx
    first = lines[idx].lstrip(" ")
    if first.startswith("- "):
        return _parse_list(lines, idx, indent)
    if first == "-":
        return _parse_list(lines, idx, indent)
    return _parse_dict(lines, idx, indent)


def _parse_dict(lines: list[str], idx: int, indent: int) -> tuple[dict, int]:
    out: dict[str, Any] = {}
    i = idx
    while i < len(lines):
        line = lines[i]
        if _indent(line) < indent:
            break
        if _indent(line) > indent:
            i += 1
            continue
        content = line.lstrip(" ")
        if content.startswith("- "):
            break
        if ":" not in content:
            i += 1
            continue
        key, _, val = content.partition(":")
        key = key.strip()
        val = val.strip()
        if val:
            out[key] = _scalar(val)
            i += 1
        else:
            # nested block or list — look ahead
            if i + 1 < len(lines) and _indent(lines[i + 1]) > indent:
                child_indent = _indent(lines[i + 1])
                child, ni = _parse_node(lines, i + 1, child_indent)
                out[key] = child
                i = ni
            else:
                out[key] = None
                i += 1
    return out, i


def _parse_list(lines: list[str], idx: int, indent: int) -> tuple[list, int]:
    out: list[Any] = []
    i = idx
    while i < len(lines):
        line = lines[i]
        if _indent(line) < indent:
            break
        if _indent(line) > indent:
            i += 1
            continue
        content = line.lstrip(" ")
        if not content.startswith("-"):
            break
        rest = content[1:].strip()
        if rest:
            out.append(_scalar(rest))
            i += 1
        else:
            # nested block after bare dash
            if i + 1 < len(lines) and _indent(lines[i + 1]) > indent:
                child_indent = _indent(lines[i + 1])
                child, ni = _parse_node(lines, i + 1, child_indent)
                out.append(child)
                i = ni
            else:
                out.append(None)
                i += 1
    return out, i


def load_yaml(text: str) -> Any:
    """Parse a controlled YAML subset into Python data (stdlib only)."""
    lines = [_strip_comment(l).rstrip() for l in text.splitlines()]
    lines = [l for l in lines if l.strip()]
    if not lines:
        return {}
    base = _indent(lines[0])
    node, _ = _parse_node(lines, 0, base)
    return node


# ---------------------------------------------------------------------------
# Pydantic schema
# ---------------------------------------------------------------------------


class ToolCallTemplate(BaseModel):
    """Shape of the tool-call / function-call template a vendor's harness uses."""

    style: str = Field(
        default="openai",
        description="openai (json tool_calls) | xml | hermes | custom",
    )
    trigger: str = Field(
        default="", description="marker/token that opens a tool call, if any"
    )
    schema_shape: dict[str, Any] = Field(
        default_factory=dict, description="function-call schema shape (name/args keys)"
    )
    description: str = ""

    model_config = {"extra": "allow"}


class HarnessProfile(BaseModel):
    """A reverse-engineered per-vendor eval-harness assumption set.

    This is the proprietary-data primitive: every published vendor score depends
    on one of these, and the vendor never publishes it. Reverse-engineering +
    provenance is the moat.
    """

    vendor: str = Field(description="deepseek | qwen | kimi")
    model_id: str = Field(description="e.g. deepseek-v4-pro-0813")
    model_name: str = Field(
        description="the model string sent to the OpenAI-compatible endpoint"
    )
    system_prompt: str = Field(description="reverse-engineered minimal-mode system prompt")
    tool_call_template: ToolCallTemplate = Field(default_factory=ToolCallTemplate)
    stop_tokens: list[str] = Field(default_factory=list)
    reasoning_effort: str | None = Field(
        default=None, description="low|medium|high — reasoning-model harness lever"
    )
    temperature: float = 0.0
    max_tokens: int = 4096
    decoding: dict[str, Any] = Field(
        default_factory=dict, description="top_p / presence_penalty / etc."
    )
    provenance: list[str] = Field(
        default_factory=list, description="public lead sources (reddit / card / reverse)"
    )
    published_score: dict[str, float] = Field(
        default_factory=dict,
        description="vendor-published headline scores per benchmark, e.g. {aime: 82.7}",
    )
    base_url: str = Field(default="", description="OpenAI-compatible base URL")
    api_key_env: str = Field(
        default="", description="env var holding the API key (e.g. DEEPSEEK_API_KEY)"
    )
    notes: str = Field(default="", description="free-form reverse-engineering notes")

    model_config = {"extra": "allow"}

    @field_validator("vendor")
    @classmethod
    def _validate_vendor(cls, v: str) -> str:
        allowed = {"deepseek", "qwen", "kimi"}
        if v not in allowed:
            raise ValueError(
                f"vendor must be one of {sorted(allowed)} (got {v!r})"
            )
        return v

    @field_validator("reasoning_effort")
    @classmethod
    def _validate_effort(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"low", "medium", "high"}
        if v not in allowed:
            raise ValueError(f"reasoning_effort must be one of {sorted(allowed)} or null")
        return v


class ProfileError(Exception):
    """Raised when a profile cannot be loaded or validated."""


# ---------------------------------------------------------------------------
# Profile registry / loading
# ---------------------------------------------------------------------------

# Map a friendly profile key (deepseek-v4 / qwen3-8 / kimi-k3) to its YAML file.
PROFILE_FILES = {
    "deepseek-v4": "deepseek_v4.yaml",
    "qwen3-8": "qwen3_8.yaml",
    "kimi-k3": "kimi_k3.yaml",
}

PROFILE_DIR = Path(__file__).parent / "profiles"


def _resolve_file(key: str) -> Path:
    if key in PROFILE_FILES:
        return PROFILE_DIR / PROFILE_FILES[key]
    # allow a direct path fallback
    p = Path(key)
    if p.suffix in (".yaml", ".yml") and p.exists():
        return p
    # case-insensitive vendor match
    norm = key.lower().replace("_", "-")
    for k, fn in PROFILE_FILES.items():
        if k == norm:
            return PROFILE_DIR / fn
    raise ProfileError(
        f"unknown profile key {key!r}; known: {sorted(PROFILE_FILES)}"
    )


def load_profile(key: str) -> HarnessProfile:
    """Load and validate a HarnessProfile from the bundled profiles dir.

    ``key`` is one of the friendly keys (``deepseek-v4`` / ``qwen3-8`` /
    ``kimi-k3``) or a path to a ``.yaml`` file.
    """
    path = _resolve_file(key)
    if not path.exists():
        # fall back to importlib.resources (installed wheel)
        try:
            text = resources.files("harnessprobe.profiles").joinpath(
                path.name
            ).read_text(encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            raise ProfileError(f"profile {key!r} not found on disk or in package: {e}")
    else:
        text = path.read_text(encoding="utf-8")
    data = load_yaml(text)
    if not isinstance(data, dict):
        raise ProfileError(f"profile {key!r}: top-level must be a mapping")
    try:
        return HarnessProfile.model_validate(data)
    except Exception as e:  # noqa: BLE001
        raise ProfileError(f"profile {key!r} failed validation: {e}") from e


def list_profiles() -> list[str]:
    """Return the available bundled profile keys."""
    return sorted(PROFILE_FILES)
