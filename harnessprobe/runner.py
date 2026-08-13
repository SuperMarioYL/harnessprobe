"""Runner — apply a HarnessProfile to a benchmark subset, produce a MatchedRun.

A ``MatchedRun`` is one (model endpoint, HarnessProfile, benchmark subset)
triple scored into a single matched reproducible percentage. The runner is
single-process, single-threaded, and the only network touchpoint is the
:class:`~harnessprobe.adapters.openai_compat.OpenAICompatAdapter`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from harnessprobe.adapters.openai_compat import OpenAICompatAdapter
from harnessprobe.bench import aime
from harnessprobe.profile import HarnessProfile


@dataclass
class ProblemResult:
    """One problem's outcome under the matched harness."""

    problem_id: str
    prompt: str
    response: str
    expected: int
    guessed: int | None
    correct: bool
    stub: bool = False


@dataclass
class MatchedRun:
    """The scored result of running one profile on a benchmark subset."""

    vendor: str
    model_id: str
    bench: str
    profile: HarnessProfile
    n_problems: int
    n_correct: int
    matched_score: float  # percentage 0-100
    published_score: float | None  # percentage 0-100, from the profile, if any
    results: list[ProblemResult] = field(default_factory=list)
    elapsed_s: float = 0.0
    stub: bool = False

    @property
    def gap(self) -> float | None:
        """Signed gap = matched_score - published_score (negative = harness inflated)."""
        if self.published_score is None:
            return None
        return round(self.matched_score - self.published_score, 2)


def run_match(
    profile: HarnessProfile,
    bench: str = "aime",
    *,
    n: int = 30,
    base_url: str | None = None,
    api_key: str | None = None,
    bench_path: str | None = None,
    progress: Any | None = None,
) -> MatchedRun:
    """Run ``profile`` on ``bench`` (aime) and return a scored MatchedRun.

    ``progress`` is an optional callable ``fn(vendor, idx, n)`` for live output.
    """
    bench = (bench or "aime").lower()
    if bench != "aime":
        raise ValueError(f"unknown bench {bench!r}; v0.1 supports 'aime' only")

    problems = aime.load_subset(n, path=bench_path)
    adapter = OpenAICompatAdapter(profile, base_url=base_url, api_key=api_key)
    results: list[ProblemResult] = []
    n_correct = 0
    t0 = time.time()

    for i, prob in enumerate(problems):
        prompt = aime.format_prompt(prob)
        is_stub = adapter.is_stub
        ctx = {
            "expected": prob.answer,
            "index": i,
            "problem_id": prob.id,
        }
        try:
            comp = adapter.complete(prompt, context=ctx)
            comp_text = comp.text
            is_stub = comp.stub
        except Exception as e:  # noqa: BLE001 — keep the run alive, mark wrong
            comp_text = f"[runner error: {e}]"
        guess = aime._extract_int(comp_text)
        ok = guess is not None and guess == prob.answer
        if ok:
            n_correct += 1
        results.append(
            ProblemResult(
                problem_id=prob.id,
                prompt=prompt,
                response=comp_text,
                expected=prob.answer,
                guessed=guess,
                correct=ok,
                stub=is_stub,
            )
        )
        if progress:
            try:
                progress(profile.vendor, i + 1, len(problems))
            except Exception:  # noqa: BLE001
                pass

    elapsed = time.time() - t0
    matched = round(100.0 * n_correct / max(1, len(problems)), 2)
    pub = profile.published_score.get(bench)
    pub_score = None if pub is None else float(pub)

    return MatchedRun(
        vendor=profile.vendor,
        model_id=profile.model_id,
        bench=bench,
        profile=profile,
        n_problems=len(problems),
        n_correct=n_correct,
        matched_score=matched,
        published_score=pub_score,
        results=results,
        elapsed_s=round(elapsed, 3),
        stub=adapter.is_stub,
    )
