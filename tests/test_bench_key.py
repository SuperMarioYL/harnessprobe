"""Independent verification of the bundled practice-set answer key.

Every stored answer is re-derived here from the problem statement with code that
does not read ``AIME_PRACTICE_SUBSET[*].answer``. This test is the authority on
the key: on v0.3.0 the same checks reported 14 mismatches out of 22 items that
were mechanically checkable, which is why v0.4.0 replaced the table.
"""

from __future__ import annotations

import itertools
import math
from fractions import Fraction

from harnessprobe.bench.aime import AIME_PRACTICE_SUBSET, load_subset


def _trailing_zeros(n: int) -> int:
    count, power = 0, 5
    while power <= n:
        count += n // power
        power *= 5
    return count


def _divisor_count(n: int) -> int:
    count = 0
    for d in range(1, math.isqrt(n) + 1):
        if n % d == 0:
            count += 1 if d * d == n else 2
    return count


def _fib_units(n: int) -> int:
    a = b = 1
    for _ in range(n - 2):
        a, b = b, (a + b) % 10
    return b


def _grid_3x3_count() -> int:
    """Count 3x3 arrangements of 1..9 with equal row and column sums."""
    same = 0
    for p in itertools.permutations(range(1, 10)):
        r0, r1, r2 = p[0] + p[1] + p[2], p[3] + p[4] + p[5], p[6] + p[7] + p[8]
        if r0 != r1 or r1 != r2:
            continue
        if p[0] + p[3] + p[6] == p[1] + p[4] + p[7] == p[2] + p[5] + p[8]:
            same += 1
    return same


def _p_plus_q(favorable: int, total: int) -> int:
    f = Fraction(favorable, total)
    return f.numerator + f.denominator


def _recomputed() -> dict[str, int]:
    from itertools import combinations, product

    two_from_ten = list(combinations(range(1, 11), 2))
    marble_pairs = [
        (a, b)
        for a, b in combinations(range(10), 2)
        if a < 4 and b < 4  # indices 0-3 are the red marbles
    ]
    return {
        "aime-practice-01": _grid_3x3_count(),
        "aime-practice-02": pow(3, 100, 7),
        "aime-practice-03": 10**2 // 2,
        "aime-practice-04": 3 * math.isqrt(3**2 + 4**2),
        "aime-practice-05": math.floor((3 + math.sqrt(5)) ** 2),
        "aime-practice-06": (1 + 9 * 10 // 2) % 100,
        "aime-practice-07": sum(
            1 for i in range(1, 1000) if sum(map(int, str(i))) == 5
        ),
        "aime-practice-08": round(
            2 * (math.sqrt(2 + math.sqrt(2)) + math.sqrt(2 - math.sqrt(2)))
        ),
        "aime-practice-09": math.comb(7, 2),
        "aime-practice-10": _divisor_count(math.factorial(10)),
        "aime-practice-11": _p_plus_q(
            sum(1 for a, b in two_from_ten if (a + b) % 2 == 0),
            len(two_from_ten),
        ),
        "aime-practice-12": pow(7, 100, 100),
        "aime-practice-13": math.comb(9, 4),
        "aime-practice-14": round(100 - 25 * math.pi),
        "aime-practice-15": sum(
            n
            for n in range(-1000, 1001)
            if (v := n * n - 19 * n + 99) >= 0 and math.isqrt(v) ** 2 == v
        ),
        "aime-practice-16": _p_plus_q(
            sum(1 for toss in product((0, 1), repeat=3) if sum(toss) >= 2),
            2**3,
        ),
        "aime-practice-17": _trailing_zeros(100),
        "aime-practice-18": _fib_units(100),
        "aime-practice-19": sum(
            1 for i in range(1, 1001) if i % 7 == 0 or i % 11 == 0
        ),
        "aime-practice-20": round((3 * math.sqrt(3) / 2) * 6**2 / math.sqrt(3)),
        "aime-practice-21": math.comb(5, 3) * 2**3 * 3**2,
        "aime-practice-22": math.factorial(4),
        "aime-practice-23": next(
            n for n in range(1, 200) if _trailing_zeros(n) >= 6
        ),
        "aime-practice-24": 51 // 3 + 2,
        "aime-practice-25": _p_plus_q(len(marble_pairs), math.comb(10, 2)),
        "aime-practice-26": 3 + 3 + 3,
        "aime-practice-27": math.factorial(6) // (math.factorial(3) * math.factorial(2)),
        "aime-practice-28": 5 * 12 // 2,
        "aime-practice-29": sum(
            i
            for i in range(2, 20)
            if all(i % d for d in range(2, math.isqrt(i) + 1))
        ),
        "aime-practice-30": 7 + 99 * 5,
    }


def test_answer_key_recomputed() -> None:
    stored = {p.id: p.answer for p in AIME_PRACTICE_SUBSET}
    computed = _recomputed()
    assert set(stored) == set(computed)
    mismatches = {
        pid: (stored[pid], computed[pid])
        for pid in computed
        if stored[pid] != computed[pid]
    }
    assert not mismatches, f"answer key disagrees with independent computation: {mismatches}"


def test_ids_and_range() -> None:
    assert len(AIME_PRACTICE_SUBSET) == 30
    ids = [p.id for p in AIME_PRACTICE_SUBSET]
    assert len(set(ids)) == 30
    for p in AIME_PRACTICE_SUBSET:
        assert p.id.startswith("aime-practice-")
        assert p.problem
        assert 0 <= p.answer <= 999, f"{p.id} answer {p.answer} out of range"


def test_no_official_exam_ids() -> None:
    # The bundled set is a practice set; ids must not claim official exam provenance.
    assert not any(p.id.startswith("aime-2024") for p in AIME_PRACTICE_SUBSET)


def test_load_subset_uses_practice_set() -> None:
    assert load_subset(None) == AIME_PRACTICE_SUBSET
    assert [p.id for p in load_subset(3)] == [
        "aime-practice-01",
        "aime-practice-02",
        "aime-practice-03",
    ]
