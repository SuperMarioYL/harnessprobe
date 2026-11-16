"""AIME-format arithmetic practice set + integer-answer grader.

AIME answers are integers in ``[0, 999]``; that makes grading unambiguous (exact
integer match, no judge LLM) and harness-sensitive (system prompt / stop tokens /
reasoning-effort all move the needle), which is exactly what a matched-harness
comparison needs.

The bundled ``AIME_PRACTICE_SUBSET`` is a 30-problem set written in AIME format
(short standalone math problems with a single integer answer in range). It is a
practice set, not the official AIME-2024 exam and not a reproduction of it: the
item ids are stable identifiers (``aime-practice-NN``), not exam numbers. Every
stored answer is re-derived independently from its statement by
``tests/test_bench_key.py``, and that test is the authority on the key — if an
answer and the test disagree, the answer is wrong.

Swap in a different set by dropping a JSON file and pointing ``load_subset`` at
it; the grader is unchanged.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

BENCH_KEY = "aime"


@dataclass(frozen=True)
class AIMEProblem:
    """One AIME-format problem with an integer answer in [0, 999]."""

    id: str
    problem: str
    answer: int


def _extract_int(text: str) -> int | None:
    """Pull the final answer integer out of a model response.

    Convention (AIME grading): the answer is the integer inside the last
    ``\\boxed{...}``; failing that, the last bare integer in the response.
    """
    boxes = re.findall(r"\\boxed\{\s*([+-]?\d+)\s*\}", text)
    if boxes:
        try:
            return int(boxes[-1])
        except ValueError:
            pass
    nums = re.findall(r"(?<![\d.])(\d{1,3})(?!\d)", text)
    if nums:
        try:
            return int(nums[-1])
        except ValueError:
            pass
    return None


def grade(problem: AIMEProblem, response: str) -> bool:
    """Grade a single response against the problem's answer."""
    guess = _extract_int(response)
    return guess is not None and guess == problem.answer


# ---------------------------------------------------------------------------
# Bundled 30-problem AIME-format practice set
# ---------------------------------------------------------------------------
# Answers are integers in [0, 999] and are re-derived from each statement by
# tests/test_bench_key.py. Ids are stable practice identifiers, not exam items.

AIME_PRACTICE_SUBSET: list[AIMEProblem] = [
    AIMEProblem("aime-practice-01",
        "Find the number of ways to place the integers 1 through 9 in a 3x3 grid "
        "so that the sum of the numbers in each row and each column is the same.",
        72),
    AIMEProblem("aime-practice-02",
        "Find the remainder when 3^100 is divided by 7.",
        4),
    AIMEProblem("aime-practice-03",
        "A square has diagonal length 10. Find the area of the square.",
        50),
    AIMEProblem("aime-practice-04",
        "A right circular cone has base radius 3 and height 4. Find its lateral "
        "surface area divided by pi.",
        15),
    AIMEProblem("aime-practice-05",
        "Find the greatest integer strictly less than (3 + sqrt(5))^2.",
        27),
    AIMEProblem("aime-practice-06",
        "A sequence is defined by a_1 = 1 and a_{n+1} = a_n + n for n >= 1. "
        "Find a_{10} mod 100.",
        46),
    AIMEProblem("aime-practice-07",
        "How many positive integers less than 1000 have the sum of their digits "
        "equal to 5?",
        21),
    AIMEProblem("aime-practice-08",
        "Let f(x) = x^4 - 4x^2 + 2. Find the sum of the absolute values of the "
        "roots of f(x) = 0, rounded to the nearest integer.",
        5),
    AIMEProblem("aime-practice-09",
        "In how many ways can 8 identical balls be distributed into 3 distinct "
        "boxes such that each box has at least one ball?",
        21),
    AIMEProblem("aime-practice-10",
        "Find the number of positive divisors of 10!.",
        270),
    AIMEProblem("aime-practice-11",
        "Two distinct numbers are selected at random from the set "
        "{1, 2, 3, ..., 10}. What is the probability their sum is even? "
        "Express as p/q in lowest terms and find p+q.",
        13),
    AIMEProblem("aime-practice-12",
        "Find the remainder when 7^{100} is divided by 100.",
        1),
    AIMEProblem("aime-practice-13",
        "How many 4-digit positive integers have digits that are strictly increasing?",
        126),
    AIMEProblem("aime-practice-14",
        "A circle of radius 5 is inscribed in a square. Find the area of the region "
        "inside the square but outside the circle, rounded to the nearest integer.",
        21),
    AIMEProblem("aime-practice-15",
        "Find the sum of all integers n such that n^2 - 19n + 99 is a perfect square.",
        38),
    AIMEProblem("aime-practice-16",
        "Three fair coins are tossed. What is the probability of getting at least "
        "two heads? Express as p/q in lowest terms; find p+q.",
        3),
    AIMEProblem("aime-practice-17",
        "Find the number of trailing zeros in 100!.",
        24),
    AIMEProblem("aime-practice-18",
        "The Fibonacci sequence is 1, 1, 2, 3, 5, 8, ... Find the units digit of "
        "the 100th Fibonacci number.",
        5),
    AIMEProblem("aime-practice-19",
        "How many integers between 1 and 1000 inclusive are divisible by 7 or 11?",
        220),
    AIMEProblem("aime-practice-20",
        "A regular hexagon has side length 6. Find its area divided by sqrt(3).",
        54),
    AIMEProblem("aime-practice-21",
        "Find the coefficient of x^3 in the expansion of (2x + 3)^5.",
        720),
    AIMEProblem("aime-practice-22",
        "How many ways can 5 people sit around a circular table?",
        24),
    AIMEProblem("aime-practice-23",
        "Find the smallest positive integer n such that n! is divisible by 10^6.",
        25),
    AIMEProblem("aime-practice-24",
        "The sum of three consecutive odd integers is 51. Find the largest.",
        19),
    AIMEProblem("aime-practice-25",
        "A bag contains 4 red and 6 blue marbles. Two are drawn without replacement. "
        "Find the probability both are red as p/q in lowest terms; find p+q.",
        17),
    AIMEProblem("aime-practice-26",
        "Find the value of log_2(8) + log_3(27) + log_5(125).",
        9),
    AIMEProblem("aime-practice-27",
        "Find the number of distinct arrangements of the letters in BANANA.",
        60),
    AIMEProblem("aime-practice-28",
        "A triangle has sides 5, 12, 13. Find its area.",
        30),
    AIMEProblem("aime-practice-29",
        "Find the sum of all prime numbers less than 20.",
        77),
    AIMEProblem("aime-practice-30",
        "Find the 100th term of the arithmetic sequence 7, 12, 17, 22, ...",
        502),
]


def load_subset(n: int | None = 30, *, path: str | None = None) -> list[AIMEProblem]:
    """Return the practice subset (first ``n`` problems), or load a JSON override.

    A JSON override file is a list of ``{"id","problem","answer"}`` objects;
    this lets a user swap in a different problem set without code.
    """
    if n is not None and n < 1:
        raise ValueError(f"n must be >= 1 (got {n})")
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        probs = [
            AIMEProblem(d["id"], d["problem"], int(d["answer"])) for d in data
        ]
        return probs if n is None else probs[:n]
    subset = AIME_PRACTICE_SUBSET
    return subset if n is None else subset[:n]


def format_prompt(problem: AIMEProblem) -> str:
    """Format a problem into the prompt string sent under the harness profile."""
    return (
        f"{problem.problem}\n\n"
        "Solve the problem. The answer is an integer between 0 and 999 "
        "(inclusive). Put your final answer inside \\boxed{}."
    )
