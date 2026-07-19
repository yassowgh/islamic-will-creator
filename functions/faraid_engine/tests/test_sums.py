"""Property test: for a wide sweep of heir combinations, every Sunni
calculation distributes exactly the whole estate (total == 1)."""
from fractions import Fraction
from itertools import combinations

import pytest

from faraid_engine import calculate
from .conftest import build

POOL = ["husband", "mother", "father", "daughter", "son",
        "paternal_grandfather", "full_sister", "maternal_brother",
        "sons_daughter", "full_brother", "paternal_sister",
        "maternal_grandmother", "full_paternal_uncle"]

COMBOS = (list(combinations(POOL, 2)) + list(combinations(POOL[:9], 3)))
COMBOS = [c for c in COMBOS if not ("husband" in c and "wife" in c)]


@pytest.mark.parametrize("madhhab", ["hanafi", "shafii"])
@pytest.mark.parametrize("combo", COMBOS,
                         ids=["+".join(c) for c in COMBOS])
def test_total_is_whole_estate(madhhab, combo):
    res = calculate(madhhab, build(**{k: 1 for k in combo}))
    total = res.total_distributed()
    assert total == Fraction(1), (
        f"{combo}: distributed {total}; notes={res.notes}; "
        f"warnings={res.warnings}")
