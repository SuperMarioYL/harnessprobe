"""Tests for the runner — stub adapter path (no network/keys needed)."""

from __future__ import annotations

import pytest

from harnessprobe.bench.aime import (
    AIME_2024_SUBSET,
    AIMEProblem,
    _extract_int,
    grade,
    load_subset,
)
from harnessprobe.profile import load_profile
from harnessprobe.runner import MatchedRun, run_match


class TestAIMEGrader:
    def test_extract_boxed(self) -> None:
        assert _extract_int("blah \\boxed{42} done") == 42

    def test_extract_last_boxed(self) -> None:
        assert _extract_int("\\boxed{1} then \\boxed{99}") == 99

    def test_extract_last_bare_int(self) -> None:
        assert _extract_int("the answer is 73") == 73

    def test_extract_none(self) -> None:
        assert _extract_int("no numbers here") is None

    def test_grade_correct(self) -> None:
        p = AIMEProblem("t", "q", 42)
        assert grade(p, "\\boxed{42}") is True

    def test_grade_wrong(self) -> None:
        p = AIMEProblem("t", "q", 42)
        assert grade(p, "\\boxed{7}") is False


class TestAIMESubset:
    def test_subset_has_30(self) -> None:
        assert len(AIME_2024_SUBSET) == 30

    def test_load_subset_n(self) -> None:
        assert len(load_subset(5)) == 5
        assert len(load_subset(30)) == 30
        assert len(load_subset(None)) == 30

    @pytest.mark.parametrize("prob", AIME_2024_SUBSET)
    def test_all_answers_in_range(self, prob: AIMEProblem) -> None:
        assert 0 <= prob.answer <= 999, f"{prob.id} answer {prob.answer} out of AIME range"
        assert prob.problem and prob.id


class TestRunnerStub:
    def test_run_match_single_model(self) -> None:
        p = load_profile("deepseek-v4")
        run = run_match(p, bench="aime", n=10)
        assert isinstance(run, MatchedRun)
        assert run.vendor == "deepseek"
        assert run.bench == "aime"
        assert run.n_problems == 10
        assert run.n_correct <= 10
        assert 0 <= run.matched_score <= 100
        assert run.stub is True  # no API key in test env
        assert len(run.results) == 10
        assert run.published_score == 79.8

    def test_run_match_all_three_models(self) -> None:
        for key in ["deepseek-v4", "qwen3-8", "kimi-k3"]:
            p = load_profile(key)
            run = run_match(p, n=8)
            assert run.vendor == p.vendor
            assert run.n_problems == 8
            # stub produces deterministic, vendor-differentiated results
            assert run.matched_score >= 0

    def test_stub_deterministic(self) -> None:
        """Same profile + same problems → identical matched_score (determinism)."""
        p = load_profile("kimi-k3")
        r1 = run_match(p, n=10)
        r2 = run_match(p, n=10)
        assert r1.matched_score == r2.matched_score
        assert r1.n_correct == r2.n_correct

    def test_vendor_differentiated_spread(self) -> None:
        """Stub spread differs by vendor (so the matrix reads realistically)."""
        scores = {}
        for key in ["deepseek-v4", "qwen3-8", "kimi-k3"]:
            run = run_match(load_profile(key), n=30)
            scores[run.vendor] = run.matched_score
        # not all identical
        assert len(set(scores.values())) > 1

    def test_unknown_bench_raises(self) -> None:
        p = load_profile("deepseek-v4")
        with pytest.raises(ValueError):
            run_match(p, bench="mmlu", n=5)

    def test_gap_signed(self) -> None:
        p = load_profile("deepseek-v4")
        run = run_match(p, n=10)
        if run.published_score is not None:
            assert run.gap == round(run.matched_score - run.published_score, 2)
