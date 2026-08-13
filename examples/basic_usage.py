"""Example: programmatic use of HarnessProbe as a library.

Run: python examples/basic_usage.py
"""

from harnessprobe import build_matrix, export_repro_pkg, load_profile, render_report, run_match


def main() -> None:
    # 1. Load the three bundled vendor profiles (the proprietary-data primitive).
    profiles = [load_profile(k) for k in ("deepseek-v4", "qwen3-8", "kimi-k3")]

    # 2. Run each profile on the AIME subset (stub mode if no API keys set).
    runs = [run_match(p, bench="aime", n=10) for p in profiles]

    # 3. Build the matched-score GapMatrix.
    matrix = build_matrix(runs)
    for row in matrix.sort_by_matched():
        print(
            f"{row.vendor:9} {row.model_id:24} "
            f"published={row.published_str:>6}  matched={row.matched_str:>6}  "
            f"gap={row.gap_str:>7}  ({row.n_correct}/{row.n_problems})"
        )

    # 4. Render the HTML report + export the reproducible package.
    render_report(matrix, runs, out="example-report.html")
    export_repro_pkg(runs, matrix, out="example-repro.zip")
    print("\nWrote example-report.html and example-repro.zip")


if __name__ == "__main__":
    main()
