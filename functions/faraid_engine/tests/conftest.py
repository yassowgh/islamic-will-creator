import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fractions import Fraction

import pytest

from faraid_engine import HeirInput, Rel, calculate

F = Fraction
REL = {r.value: r for r in Rel}


def build(**counts):
    """build(husband=1, daughter=2, ...) -> list[HeirInput]"""
    heirs = []
    for key, cnt in counts.items():
        heirs.append(HeirInput(REL[key], cnt))
    return heirs


def run(madhhab, expected, **counts):
    res = calculate(madhhab, build(**counts))
    got = {s.relationship.value: s.total for s in res.shares if s.total}
    want = {k: F(v) for k, v in expected.items() if F(v) != 0}
    assert got == want, f"{madhhab}: expected {want}, got {got}"
    total = sum(got.values(), F(0))
    if want:
        assert total == 1, f"{madhhab}: shares sum to {total}, not 1"
    return res


@pytest.fixture
def frac():
    return F
