"""Tests for GapMatrix building + gap computation."""

from __future__ import annotations

from harnessprobe.matrix import GapMatrix, MatrixRow, build_matrix
from harnessprobe.profile import load_profile
from harnessprobe.runner import MatchedRun, run_match


def _make_row(vendor, model_id, pub, matched, n=10) -> MatrixRow:
    return MatrixRow(
        vendor=vendor,
        model_id=model_id,
        bench="aime",
        published_score=pub,
        matched_score=matched,
        n_correct=int(matched / 100 * n),
        n_problems=n,
        gap=round(matched - pub, 2) if pub is not None else None,
        stub=True,
    )


class TestMatrixRow:
    def test_gap_str_negative(self) -> None:
        r = _make_row("deepseek", "m", 80.0, 70.0)
        assert r.gap_str == "-10.00"

    def test_gap_str_positive(self) -> None:
        r = _make_row("deepseek", "m", 70.0, 80.0)
        assert r.gap_str == "+10.00"

    def test_gap_str_none(self) -> None:
        r = _make_row("deepseek", "m", None, 70.0)
        assert r.gap_str == "—"

    def test_published_str_none(self) -> None:
        r = _make_row("deepseek", "m", None, 70.0)
        assert r.published_str == "—"


class TestGapMatrix:
    def test_build_from_runs(self) -> None:
        runs = [run_match(load_profile(k), n=6) for k in ["deepseek-v4", "qwen3-8", "kimi-k3"]]
        m = build_matrix(runs)
        assert len(m) == 3
        assert m.bench == "aime"
        assert m.n_problems == 6
        assert m.all_stub is True

    def test_sort_by_matched_desc(self) -> None:
        rows = [
            _make_row("qwen", "q", 77, 46.67),
            _make_row("deepseek", "d", 79.8, 70.0),
            _make_row("kimi", "k", 75.5, 53.33),
        ]
        m = GapMatrix(bench="aime", rows=rows, n_problems=30)
        ordered = m.sort_by_matched()
        assert ordered[0].vendor == "deepseek"
        assert ordered[0].matched_score == 70.0
        assert ordered[-1].matched_score == 46.67

    def test_largest_gap_most_negative(self) -> None:
        rows = [
            _make_row("deepseek", "d", 79.8, 70.0),   # -9.8
            _make_row("qwen", "q", 77.2, 46.67),       # -30.53
            _make_row("kimi", "k", 75.5, 53.33),       # -22.17
        ]
        m = GapMatrix(bench="aime", rows=rows)
        lg = m.largest_gap
        assert lg is not None
        assert lg.vendor == "qwen"
        assert lg.gap == -30.53

    def test_largest_gap_none_when_no_published(self) -> None:
        rows = [_make_row("x", "y", None, 50.0)]
        m = GapMatrix(bench="aime", rows=rows)
        assert m.largest_gap is None

    def test_empty_matrix(self) -> None:
        m = build_matrix([])
        assert len(m) == 0
        assert m.bench == "aime"

    def test_iter_and_len(self) -> None:
        rows = [_make_row("a", "b", 50, 40), _make_row("c", "d", 60, 55)]
        m = GapMatrix(bench="aime", rows=rows)
        assert len(m) == 2
        assert [r.vendor for r in m] == ["a", "c"]
