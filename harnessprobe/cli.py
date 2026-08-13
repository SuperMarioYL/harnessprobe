"""HarnessProbe CLI — the single entry point a procurement lead runs.

``harnessprobe match`` runs the per-vendor matched-harness comparison and
prints a GapMatrix; ``harnessprobe report`` renders the HTML report;
``harnessprobe repro`` exports the verbatim-reproducible package.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from harnessprobe import __version__
from harnessprobe.matrix import GapMatrix, build_matrix
from harnessprobe.profile import ProfileError, list_profiles, load_profile
from harnessprobe.report import export_repro_pkg, render_report
from harnessprobe.runner import MatchedRun, run_match

app = typer.Typer(
    name="harnessprobe",
    help="Reverse-engineer per-vendor benchmark-harness assumptions into a matched-score GapMatrix.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

DEFAULT_STATE = ".harnessprobe-last.json"
KNOWN_MODELS = ["deepseek-v4", "qwen3-8", "kimi-k3"]


def _parse_models(models: str) -> list[str]:
    if not models:
        return list(KNOWN_MODELS)
    return [m.strip() for m in models.split(",") if m.strip()]


def _save_state(path: Path, runs: list[MatchedRun], matrix: GapMatrix) -> None:
    data = {
        "version": __version__,
        "bench": matrix.bench,
        "n_problems": matrix.n_problems,
        "all_stub": matrix.all_stub,
        "matrix": [
            {
                "vendor": r.vendor,
                "model_id": r.model_id,
                "bench": r.bench,
                "published_score": r.published_score,
                "matched_score": r.matched_score,
                "n_correct": r.n_correct,
                "n_problems": r.n_problems,
                "gap": r.gap,
                "stub": r.stub,
            }
            for r in matrix.rows
        ],
        "runs": [
            {
                "vendor": r.vendor,
                "model_id": r.model_id,
                "bench": r.bench,
                "matched_score": r.matched_score,
                "published_score": r.published_score,
                "n_correct": r.n_correct,
                "n_problems": r.n_problems,
                "elapsed_s": r.elapsed_s,
                "stub": r.stub,
            }
            for r in runs
        ],
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _print_matrix(matrix: GapMatrix) -> None:
    table = Table(
        title=f"GapMatrix — {matrix.bench.upper()} ({matrix.n_problems} problems)",
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("Vendor", style="bold")
    table.add_column("Model", style="cyan")
    table.add_column("Published", justify="right")
    table.add_column("Matched", justify="right", style="green")
    table.add_column("Gap", justify="right", style="bold")
    table.add_column("Correct", justify="right")
    table.add_column("Mode", justify="center")
    for row in matrix.sort_by_matched():
        gap_style = "red" if (row.gap is not None and row.gap < 0) else "yellow" if row.gap == 0 else "green"
        table.add_row(
            row.vendor,
            row.model_id,
            row.published_str,
            row.matched_str,
            f"[{gap_style}]{row.gap_str}[/{gap_style}]",
            f"{row.n_correct}/{row.n_problems}",
            "stub" if row.stub else "live",
        )
    console.print(table)
    lg = matrix.largest_gap
    if lg is not None and lg.gap is not None:
        console.print(
            f"\n[bold]Largest harness inflation:[/bold] {lg.vendor}/{lg.model_id} "
            f"— published {lg.published_str}, matched {lg.matched_str}, "
            f"gap [red]{lg.gap_str}[/red] pts."
        )
    if matrix.all_stub:
        console.print(
            "\n[dim]Note: running in STUB mode (no API keys). Set DEEPSEEK_API_KEY / "
            "DASHSCOPE_API_KEY / MOONSHOT_API_KEY for live scores. "
            "Stub scores are deterministic but not vendor-representative.[/dim]"
        )


@app.command()
def match(
    models: str = typer.Option(
        ",".join(KNOWN_MODELS),
        "--models", "-m",
        help="Comma-separated profile keys: deepseek-v4,qwen3-8,kimi-k3",
    ),
    bench: str = typer.Option("aime", "--bench", "-b", help="benchmark key (aime)"),
    n: int = typer.Option(30, "--n", "-n", help="number of problems"),
    base_url: str = typer.Option("", "--base-url", help="override OpenAI-compatible base URL"),
    api_key: str = typer.Option("", "--api-key", help="override API key (else env vars)"),
    save: Path = typer.Option(Path(DEFAULT_STATE), "--save", help="state file path"),
    html: Optional[Path] = typer.Option(None, "--html", help="also render HTML report to this path"),
    repro: Optional[Path] = typer.Option(None, "--repro", help="also export repro pkg to this path"),
    require_live: bool = typer.Option(False, "--require-live", help="error if no API key (no stub)"),
) -> None:
    """Run per-vendor matched-harness comparison; print the GapMatrix."""
    keys = _parse_models(models)
    runs: list[MatchedRun] = []
    for key in keys:
        try:
            profile = load_profile(key)
        except ProfileError as e:
            err_console.print(f"[red]profile {key!r}:[/red] {e}")
            raise typer.Exit(code=2)
        if require_live:
            env_name = profile.api_key_env or ""
            if not (api_key or (env_name and os.environ.get(env_name))):
                err_console.print(
                    f"[red]--require-live set but no API key for {key} "
                    f"(env {env_name or 'none'} unset)[/red]"
                )
                raise typer.Exit(code=3)
        err_console.print(f"[cyan]matching[/cyan] {key} ({profile.model_name}) on {bench}…")

        def _prog(vendor: str, idx: int, total: int) -> None:
            err_console.print(f"  {vendor}: {idx}/{total}", highlight=False)

        run = run_match(
            profile,
            bench=bench,
            n=n,
            base_url=base_url or None,
            api_key=api_key or None,
            progress=_prog,
        )
        runs.append(run)
        err_console.print(
            f"  -> matched {run.matched_score:.2f}% "
            f"({'stub' if run.stub else 'live'}, {run.n_correct}/{run.n_problems})"
        )
    matrix = build_matrix(runs)
    _save_state(save, runs, matrix)
    _print_matrix(matrix)
    if html:
        render_report(matrix, runs, out=html)
        console.print(f"\n[green]HTML report:[/green] {html}")
    if repro:
        export_repro_pkg(runs, matrix, out=repro)
        console.print(f"[green]repro pkg:[/green] {repro}")


@app.command()
def report(
    state: Path = typer.Option(Path(DEFAULT_STATE), "--state", "-s", help="state file from a prior `match`"),
    out: Path = typer.Option("report.html", "--out", "-o", help="output HTML path"),
) -> None:
    """Render the HTML matched-score report from a saved match state.

    For the full per-problem repro artifact use `harnessprobe repro` or run
    `match --html` which carries the live run objects.
    """
    if not state.exists():
        err_console.print(f"[red]state file not found:[/red] {state} — run `harnessprobe match` first")
        raise typer.Exit(code=1)
    data = _load_state(state)
    rows_data = data.get("matrix", [])
    matrix = GapMatrix(
        bench=data.get("bench", "aime"),
        n_problems=data.get("n_problems", 0),
        all_stub=data.get("all_stub", False),
    )
    from harnessprobe.matrix import MatrixRow

    matrix.rows = [
        MatrixRow(
            vendor=r["vendor"],
            model_id=r["model_id"],
            bench=r["bench"],
            published_score=r["published_score"],
            matched_score=r["matched_score"],
            n_correct=r["n_correct"],
            n_problems=r["n_problems"],
            gap=r["gap"],
            stub=r["stub"],
        )
        for r in rows_data
    ]
    html = render_report(matrix, runs=None, out=out)
    console.print(f"[green]HTML report:[/green] {out} ({len(html)} bytes)")


@app.command()
def repro(
    state: Path = typer.Option(Path(DEFAULT_STATE), "--state", "-s", help="state file"),
    out: Path = typer.Option("repro.zip", "--out", "-o", help="output zip path"),
) -> None:
    """Export a reproducible package (profiles + prompts + raw outputs) from state.

    Re-runs the matched comparison from the state's model list (stub-safe) to
    rebuild per-problem traces, then zips them.
    """
    if not state.exists():
        err_console.print(f"[red]state file not found:[/red] {state}")
        raise typer.Exit(code=1)
    data = _load_state(state)
    # re-run to rebuild traces (stub-safe)
    runs: list[MatchedRun] = []
    for row in data.get("matrix", []):
        vendor = row["vendor"]
        key = next((k for k in list_profiles() if k.startswith(vendor)), vendor)
        try:
            profile = load_profile(key)
        except ProfileError as e:
            err_console.print(f"[red]{e}[/red]")
            raise typer.Exit(code=2)
        run = run_match(profile, bench=data.get("bench", "aime"), n=data.get("n_problems", 30))
        runs.append(run)
    matrix = build_matrix(runs)
    export_repro_pkg(runs, matrix, out=out)
    console.print(f"[green]repro pkg:[/green] {out}")


@app.command()
def profiles() -> None:
    """List bundled HarnessProfile keys."""
    table = Table(title="Bundled profiles", show_lines=False)
    table.add_column("Key", style="cyan")
    table.add_column("Vendor")
    table.add_column("Model", style="bold")
    table.add_column("Published AIME")
    for key in list_profiles():
        try:
            p = load_profile(key)
            table.add_row(
                key,
                p.vendor,
                p.model_name,
                f"{p.published_score.get('aime', '—')}%",
            )
        except ProfileError as e:
            table.add_row(key, "?", f"[red]{e}[/red]", "—")
    console.print(table)


@app.command()
def version() -> None:
    """Print the version."""
    console.print(f"harnessprobe {__version__}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
