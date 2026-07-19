from fractions import Fraction

import pytest

from faraid_engine import (EstateInput, FaraidError, settle_estate,
                           monetize, calculate)
from .conftest import build

F = Fraction


def test_order_of_deductions():
    b = settle_estate(EstateInput(
        gross_estate=F(100000), funeral_costs=F(3000), debts=F(7000),
        unpaid_mahr=F(5000), unpaid_zakat=F(1000), kaffarat=F(500),
        fidya=F(500), wasiyya_fraction=F(1, 10)))
    assert b.net_estate == F(83000)
    assert b.wasiyya_amount == F(8300)
    assert b.distributable == F(74700)


def test_wasiyya_exactly_one_third_allowed():
    b = settle_estate(EstateInput(gross_estate=F(90000),
                                  wasiyya_fraction=F(1, 3)))
    assert b.wasiyya_amount == F(30000)


def test_wasiyya_above_one_third_blocked():
    with pytest.raises(FaraidError, match="one-third"):
        settle_estate(EstateInput(gross_estate=F(90000),
                                  wasiyya_fraction=F(34, 100)))


def test_negative_values_rejected():
    with pytest.raises(FaraidError):
        settle_estate(EstateInput(gross_estate=F(100), debts=F(-1)))


def test_debts_exceed_estate():
    with pytest.raises(FaraidError, match="nothing to distribute"):
        settle_estate(EstateInput(gross_estate=F(1000), debts=F(2000)))


def test_no_wasiyya_default():
    b = settle_estate(EstateInput(gross_estate=F(50000)))
    assert b.distributable == F(50000)


def test_monetize_exact_split():
    res = calculate("hanafi", build(husband=1, son=1))
    rows = monetize(res, F(100000))
    amounts = {r["relationship"]: r["amount_gbp"] for r in rows}
    assert amounts == {"husband": 25000.0, "son": 75000.0}


def test_monetize_rounds_to_pence():
    res = calculate("hanafi", build(wife=1, son=1))
    rows = monetize(res, F(1000))
    total = round(sum(r["amount_gbp"] for r in rows), 2)
    assert abs(total - 1000.0) < 0.02
