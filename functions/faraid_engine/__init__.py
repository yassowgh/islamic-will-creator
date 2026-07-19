"""Faraid engine - deterministic Islamic inheritance calculation.

Public API:
    calculate(madhhab, heirs, settings) -> CalculationResult
    settle_estate(EstateInput) -> EstateBreakdown
    monetize(result, distributable) -> list of rows with GBP amounts

This engine implements published classical rules per school and flags
uncertainty for scholar review. It is not legal or religious advice.
"""
from .model import (
    ENGINE_VERSION, CalculationResult, FaraidError, HeirInput, Madhhab,
    Rel, Settings, Share, Blocked,
)
from .estate import EstateInput, EstateBreakdown, settle_estate, monetize
from .sunni import calculate_sunni
from .jafari import calculate_jafari

__version__ = ENGINE_VERSION


def calculate(madhhab, heirs, settings=None) -> CalculationResult:
    madhhab = Madhhab(madhhab)
    if madhhab == Madhhab.JAFARI:
        return calculate_jafari(heirs, settings)
    return calculate_sunni(madhhab, heirs, settings)
