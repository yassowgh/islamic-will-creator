"""Estate settlement order (all madhhabs):
1. funeral and burial expenses; 2. debts (incl. unpaid mahr, zakat,
kaffarat, fidya); 3. wasiyya capped at one-third of the net estate
(hadith of Sa'd ibn Abi Waqqas, Bukhari 2742 / Muslim 1628);
4. faraid distribution of the remainder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from .model import FaraidError

F = Fraction
WASIYYA_CAP = F(1, 3)


@dataclass
class EstateInput:
    gross_estate: Fraction              # GBP as exact Fraction
    funeral_costs: Fraction = F(0)
    debts: Fraction = F(0)
    unpaid_mahr: Fraction = F(0)
    unpaid_zakat: Fraction = F(0)
    kaffarat: Fraction = F(0)
    fidya: Fraction = F(0)
    wasiyya_fraction: Fraction = F(0)   # of the net estate, 0..1/3


@dataclass
class EstateBreakdown:
    gross_estate: Fraction
    total_deductions: Fraction
    net_estate: Fraction
    wasiyya_amount: Fraction
    distributable: Fraction
    notes: list = field(default_factory=list)


def settle_estate(e: EstateInput) -> EstateBreakdown:
    for name in ("gross_estate", "funeral_costs", "debts", "unpaid_mahr",
                 "unpaid_zakat", "kaffarat", "fidya"):
        if getattr(e, name) < 0:
            raise FaraidError(f"{name} cannot be negative")
    if e.wasiyya_fraction < 0 or e.wasiyya_fraction > WASIYYA_CAP:
        raise FaraidError(
            "The wasiyya (bequest) may not exceed one-third of the net "
            "estate. The Prophet (peace be upon him) told Sa'd ibn Abi "
            "Waqqas: 'A third, and a third is much' (Bukhari 2742, "
            "Muslim 1628).")
    deductions = (e.funeral_costs + e.debts + e.unpaid_mahr
                  + e.unpaid_zakat + e.kaffarat + e.fidya)
    if deductions > e.gross_estate:
        raise FaraidError(
            "Deductions (funeral costs and debts) exceed the gross "
            "estate; there is nothing to distribute. Debts are settled "
            "first in Islamic law.")
    net = e.gross_estate - deductions
    wasiyya = net * e.wasiyya_fraction
    b = EstateBreakdown(
        gross_estate=e.gross_estate, total_deductions=deductions,
        net_estate=net, wasiyya_amount=wasiyya,
        distributable=net - wasiyya)
    b.notes.append("Order applied: funeral costs, then debts (including "
                   "unpaid mahr, zakat, kaffarat, fidya), then wasiyya "
                   "(max 1/3 of net), then faraid.")
    return b


def monetize(result, distributable: Fraction) -> list:
    """Attach GBP values (exact, rounded to pence) to a shares table."""
    rows = []
    for s in result.shares:
        amount = distributable * s.total
        rows.append({
            "relationship": s.relationship.value,
            "fraction": f"{s.total.numerator}/{s.total.denominator}",
            "percentage": round(float(s.total) * 100, 4),
            "amount_gbp": round(float(amount), 2),
            "reason": s.reason,
        })
    return rows
