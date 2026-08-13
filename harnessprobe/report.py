"""Report — HTML matched-score report + repro-pkg export.

Two artifacts for procurement due-diligence:

1. ``render_report`` — a self-contained HTML page (jinja2) rendering the
   GapMatrix: vendor-published vs matched-reproduced vs signed gap, per-model,
   with the provenance trail so the assumption set is auditable.
2. ``export_repro_pkg`` — a zip the integrator hands to 甲方 for verbatim
   re-run: the exact profiles + prompts + raw model outputs + a manifest.
"""

from __future__ import annotations

import io
import json
import time
import zipfile
from importlib import resources
from pathlib import Path
from typing import Iterable

from jinja2 import Environment, FileSystemLoader, select_autoescape

from harnessprobe.matrix import GapMatrix
from harnessprobe.runner import MatchedRun

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_report(
    matrix: GapMatrix,
    runs: Iterable[MatchedRun] | None = None,
    *,
    title: str = "HarnessProbe GapMatrix",
    out: str | Path | None = None,
) -> str:
    """Render the HTML matched-score report; write to ``out`` if given."""
    runs = list(runs) if runs is not None else []
    env = _env()
    tmpl = env.get_template("report.html.j2")
    html = tmpl.render(
        title=title,
        matrix=matrix,
        runs=runs,
        generated_at=time.strftime("%Y-%m-%d %H:%M:%S %z"),
    )
    if out is not None:
        Path(out).write_text(html, encoding="utf-8")
    return html


def export_repro_pkg(
    runs: Iterable[MatchedRun],
    matrix: GapMatrix | None = None,
    *,
    out: str | Path = "repro.zip",
) -> Path:
    """Export profiles + prompts + raw outputs into a verbatim-reproducible zip.

    The integrator can unzip this and re-run each model under the exact same
    harness assumptions — this is the artifact an RFP 答辩 submits.
    """
    runs = list(runs)
    out_path = Path(out)
    buf = io.BytesIO()
    manifest: dict = {
        "tool": "harnessprobe",
        "version": _version(),
        "bench": runs[0].bench if runs else "aime",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "models": [],
    }
    if matrix is not None:
        manifest["matrix"] = {
            "bench": matrix.bench,
            "n_problems": matrix.n_problems,
            "rows": [
                {
                    "vendor": r.vendor,
                    "model_id": r.model_id,
                    "published_score": r.published_score,
                    "matched_score": r.matched_score,
                    "gap": r.gap,
                    "n_correct": r.n_correct,
                    "n_problems": r.n_problems,
                }
                for r in matrix.rows
            ],
        }

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for run in runs:
            slug = f"{run.vendor}_{run.model_id}".replace("/", "_").replace(" ", "_")
            # profile dump (YAML-ish, human readable)
            pf = run.profile
            zf.writestr(
                f"models/{slug}/profile.txt",
                _profile_dump(pf),
            )
            per_problem = []
            for res in run.results:
                per_problem.append(
                    {
                        "problem_id": res.problem_id,
                        "prompt": res.prompt,
                        "response": res.response,
                        "expected": res.expected,
                        "guessed": res.guessed,
                        "correct": res.correct,
                    }
                )
                zf.writestr(
                    f"models/{slug}/prompts/{res.problem_id}.txt",
                    res.prompt,
                )
                zf.writestr(
                    f"models/{slug}/responses/{res.problem_id}.txt",
                    res.response,
                )
            zf.writestr(
                f"models/{slug}/results.json",
                json.dumps(
                    {
                        "vendor": run.vendor,
                        "model_id": run.model_id,
                        "bench": run.bench,
                        "n_problems": run.n_problems,
                        "n_correct": run.n_correct,
                        "matched_score": run.matched_score,
                        "published_score": run.published_score,
                        "gap": run.gap,
                        "elapsed_s": run.elapsed_s,
                        "stub": run.stub,
                        "results": per_problem,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
            )
            manifest["models"].append(
                {
                    "vendor": run.vendor,
                    "model_id": run.model_id,
                    "bench": run.bench,
                    "matched_score": run.matched_score,
                    "published_score": run.published_score,
                    "gap": run.gap,
                    "n_correct": run.n_correct,
                    "n_problems": run.n_problems,
                    "stub": run.stub,
                }
            )
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    out_path.write_bytes(buf.getvalue())
    return out_path


def _version() -> str:
    try:
        from harnessprobe import __version__

        return __version__
    except Exception:  # noqa: BLE001
        return "0.0.0"


def _profile_dump(pf) -> str:
    """Human-readable dump of a HarnessProfile for the repro pkg."""
    lines = [
        f"vendor: {pf.vendor}",
        f"model_id: {pf.model_id}",
        f"model_name: {pf.model_name}",
        f"reasoning_effort: {pf.reasoning_effort}",
        f"temperature: {pf.temperature}",
        f"max_tokens: {pf.max_tokens}",
        f"stop_tokens: {list(pf.stop_tokens)}",
        f"decoding: {dict(pf.decoding)}",
        f"tool_call_template.style: {pf.tool_call_template.style}",
        f"base_url: {pf.base_url}",
        f"api_key_env: {pf.api_key_env}",
        "published_score:",
    ]
    for k, v in pf.published_score.items():
        lines.append(f"  {k}: {v}")
    lines.append("provenance:")
    for s in pf.provenance:
        lines.append(f"  - {s}")
    lines.append("")
    lines.append("system_prompt:")
    lines.append(pf.system_prompt)
    return "\n".join(lines)
