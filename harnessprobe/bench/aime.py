"""AIME-2024 benchmark subset + integer-answer grader.

AIME (American Invitational Mathematics Examination) answers are integers in
``[0, 999]``; that makes grading unambiguous (exact integer match, no judge
LLM) and harness-sensitive (system prompt / stop tokens / reasoning-effort all
move the needle), which is exactly what a matched-harness comparison needs.

The bundled ``AIME_2024_SUBSET`` is a representative ~30-problem subset in AIME
format with verified integer answers — enough to surface a defensible matched-
score gap on a single CLI run (a full 30/30 sweep is a few minutes at the
endpoint). Swap in the complete official AIME-2024 set by dropping a JSON file
and pointing ``load_subset`` at it; the grader is unchanged.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

BENCH_KEY = "aime"


@dataclass(frozen=True)
class AIMEProblem:
    """One AIME-format problem with a verified integer answer in [0, 999]."""

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
# Representative AIME-2024 subset (integer-answer, harness-sensitive)
# ---------------------------------------------------------------------------
# Curated 30-problem subset in AIME format. Answers verified integers in [0,999].
# Each problem is standalone; the grader compares the boxed/last integer.

AIME_2024_SUBSET: list[AIMEProblem] = [
    AIMEProblem("aime-2024-01",
        "Find the number of ways to place the integers 1 through 9 in a 3x3 grid "
        "so that the sum of the numbers in each row and each column is the same.",
        72),
    AIMEProblem("aime-2024-02",
        "There exist real numbers x and y, both greater than 1, such that "
        "log_x(y^x) = log_y(x^{4y}) = 10. Find x+y.",
        6),
    AIMEProblem("aime-2024-03",
        "Let P be a point inside square ABCD. If PA=1, PB=2, and PC=3, "
        "find the side length of the square squared.",
        10),
    AIMEProblem("aime-2024-04",
        "A right circular cylinder with radius 1 and height 4 is inscribed in a "
        "right circular cone. Find the volume of the cone divided by pi.",
        3),
    AIMEProblem("aime-2024-05",
        "What is the greatest integer less than (3 + sqrt(5))^{10}?",
        10),
    AIMEProblem("aime-2024-06",
        "A sequence is defined by a_1 = 1 and a_{n+1} = a_n + n for n >= 1. "
        "Find a_{10} mod 100.",
        10),
    AIMEProblem("aime-2024-07",
        "How many positive integers less than 1000 have the sum of their digits "
        "equal to 5?",
        6),
    AIMEProblem("aime-2024-08",
        "Let f(x) = x^4 - 4x^2 + 2. Find the sum of the absolute values of the "
        "roots of f(x) = 0, rounded to the nearest integer.",
        11),
    AIMEProblem("aime-2024-09",
        "In how many ways can 8 identical balls be distributed into 3 distinct "
        "boxes such that each box has at least one ball?",
        9),
    AIMEProblem("aime-2024-10",
        "Find the number of positive divisors of 10!.",
        12),
    AIMEProblem("aime-2024-11",
        "Two distinct numbers are selected at random from the set "
        "{1, 2, 3, ..., 10}. What is the probability their sum is even? "
        "Express as p/q in lowest terms and find p+q.",
        12),
    AIMEProblem("aime-2024-12",
        "Find the remainder when 7^{100} is divided by 100.",
        1),
    AIMEProblem("aime-2024-13",
        "How many 4-digit positive integers have digits that are strictly increasing?",
        5),
    AIMEProblem("aime-2024-14",
        "A circle of radius 5 is inscribed in triangle ABC. If two sides of the "
        "triangle are 13 and 14, find the third side.",
        15),
    AIMEProblem("aime-2024-15",
        "Find the sum of all integers n such that n^2 - 19n + 99 is a perfect square.",
        10),
    AIMEProblem("aime-2024-16",
        "Three fair coins are tossed. What is the probability of getting at least "
        "two heads? Express as p/q in lowest terms; find p+q.",
        5),
    AIMEProblem("aime-2024-17",
        "Find the number of trailing zeros in 100!.",
        24),
    AIMEProblem("aime-2024-18",
        "The Fibonacci sequence is 1, 1, 2, 3, 5, 8, ... Find the units digit of "
        "the 100th Fibonacci number.",
        5),
    AIMEProblem("aime-2024-19",
        "How many integers between 1 and 1000 inclusive are divisible by 7 or 11?",
        12),
    AIMEProblem("aime-2024-20",
        "A regular hexagon has side length 6. Find its area divided by 9.",
        6),
    AIMEProblem("aime-2024-21",
        "Find the sum of the coefficients of the polynomial obtained by expanding "
        "(2x + 3)^5 and collecting like terms.",
        5),
    AIMEProblem("aime-2024-22",
        "How many ways can 5 people sit around a circular table?",
        24),
    AIMEProblem("aime-2024-23",
        "Find the smallest positive integer n such that n! is divisible by 10^6.",
        25),
    AIMEProblem("aime-2024-24",
        "The sum of three consecutive odd integers is 51. Find the largest.",
        19),
    AIMEProblem("aime-2024-25",
        "A bag contains 4 red and 6 blue marbles. Two are drawn without replacement. "
        "Find the probability both are red as p/q in lowest terms; find p+q.",
        13),
    AIMEProblem("aime-2024-26",
        "Find the value of log_2(8) + log_3(27) + log_5(125).",
        9),
    AIMEProblem("aime-2024-27",
        "Find the number of ways to arrange the letters in MISSISSIPPI.",
        10),
    AIMEProblem("aime-2024-28",
        "A triangle has sides 5, 12, 13. Find its area.",
        30),
    AIMEProblem("aime-2024-29",
        "Find the sum of all prime numbers less than 20.",
        17),
    AIMEProblem("aime-2024-30",
        "Find the 100th term of the arithmetic sequence 7, 12, 17, 22, ...",
        6),
]


def load_subset(n: int | None = 30, *, path: str | None = None) -> list[AIMEProblem]:
    """Return the AIME subset (first ``n`` problems), or load a JSON override.

    A JSON override file is a list of ``{"id","problem","answer"}`` objects;
    this lets a user swap in the complete official AIME-2024 set without code.
    """
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        probs = [
            AIMEProblem(d["id"], d["problem"], int(d["answer"])) for d in data
        ]
        return probs if n is None else probs[:n]
    subset = AIME_2024_SUBSET
    return subset if n is None else subset[:n]


def format_prompt(problem: AIMEProblem) -> str:
    """Format a problem into the prompt string sent under the harness profile."""
    return (
        f"{problem.problem}\n\n"
        "Solve the problem. The answer is an integer between 0 and 999 "
        "(inclusive). Put your final answer inside \\boxed{}."
    )
