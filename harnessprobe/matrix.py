"""GapMatrix — the matched-score comparison the procurement lead reads.

For each (model, benchmark) the GapMatrix pairs the **vendor-published** score
against the **matched-harness reproduced** score and reports the signed gap
(negative => the vendor's harness inflated the headline number). This is the
single artifact a 信创 ML lead takes to an RFP 答辩: apples-to-apples evidence
that DeepSeek's 82.7% vs Qwen's 79.1% is (or isn't) real under matched
assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from harnessprobe.runner import MatchedRun


@dataclass
class MatrixRow:
    """One model × benchmark row in the GapMatrix."""

    vendor: str
    model_id: str
    bench: str
    published_score: float | None
    matched_score: float
    n_correct: int
    n_problems: int
    gap: float | None  # matched - published; negative = harness-inflated
    stub: bool = False

    @property
    def gap_str(self) -> str:
        if self.gap is None:
            return "—"
        sign = "+" if self.gap >= 0 else ""
        return f"{sign}{self.gap:.2f}"

    @property
    def published_str(self) -> str:
        return "—" if self.published_score is None else f"{self.published_score:.2f}"

    @property
    def matched_str(self) -> str:
        return f"{self.matched_score:.2f}"


@dataclass
class GapMatrix:
    """The full matched-score matrix across all models × the benchmark."""

    bench: str
    rows: list[MatrixRow] = field(default_factory=list)
    n_problems: int = 0
    all_stub: bool = False

    def __iter__(self):  # type: ignore[override]
        return iter(self.rows)

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def largest_gap(self) -> MatrixRow | None:
        """The row whose harness inflated the headline number the most (most-negative gap)."""
        scored = [r for r in self.rows if r.gap is not None]
        if not scored:
            return None
        return min(scored, key=lambda r: r.gap)

    def sort_by_matched(self) -> list[MatrixRow]:
        return sorted(self.rows, key=lambda r: r.matched_score, reverse=True)


def build_matrix(runs: Iterable[MatchedRun]) -> GapMatrix:
    """Assemble a GapMatrix from a set of MatchedRuns (same benchmark)."""
    runs = list(runs)
    if not runs:
        return GapMatrix(bench="aime")
    bench = runs[0].bench
    n = max((r.n_problems for r in runs), default=0)
    rows = [
        MatrixRow(
            vendor=r.vendor,
            model_id=r.model_id,
            bench=r.bench,
            published_score=r.published_score,
            matched_score=r.matched_score,
            n_correct=r.n_correct,
            n_problems=r.n_problems,
            gap=r.gap,
            stub=r.stub,
        )
        for r in runs
    ]
    return GapMatrix(bench=bench, rows=rows, n_problems=n, all_stub=all(r.stub for r in runs))
