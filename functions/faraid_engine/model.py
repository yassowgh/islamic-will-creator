"""Data model for the faraid engine.

All arithmetic uses fractions.Fraction - never floats - so results are exact.
Primary sources: Qur'an 4:11, 4:12, 4:176. See docs/VALIDATION.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction

ENGINE_VERSION = "1.0.0"


class Madhhab(str, Enum):
    HANAFI = "hanafi"
    MALIKI = "maliki"
    SHAFII = "shafii"
    HANBALI = "hanbali"
    JAFARI = "jafari"


class Rel(str, Enum):
    """Supported heir relationships (relative to the deceased)."""
    HUSBAND = "husband"
    WIFE = "wife"                          # up to 4; share split equally
    SON = "son"
    DAUGHTER = "daughter"
    SONS_SON = "sons_son"
    SONS_DAUGHTER = "sons_daughter"
    FATHER = "father"
    MOTHER = "mother"
    GRANDFATHER = "paternal_grandfather"
    PATERNAL_GRANDMOTHER = "paternal_grandmother"
    MATERNAL_GRANDMOTHER = "maternal_grandmother"
    FULL_BROTHER = "full_brother"
    FULL_SISTER = "full_sister"
    PATERNAL_BROTHER = "paternal_brother"   # consanguine
    PATERNAL_SISTER = "paternal_sister"
    MATERNAL_BROTHER = "maternal_brother"   # uterine
    MATERNAL_SISTER = "maternal_sister"
    FULL_NEPHEW = "full_brothers_son"
    PATERNAL_NEPHEW = "paternal_brothers_son"
    FULL_UNCLE = "full_paternal_uncle"
    PATERNAL_UNCLE = "paternal_paternal_uncle"
    FULL_COUSIN = "full_uncles_son"
    PATERNAL_COUSIN = "paternal_uncles_son"


MALE_DESCENDANTS = {Rel.SON, Rel.SONS_SON}
FEMALE_DESCENDANTS = {Rel.DAUGHTER, Rel.SONS_DAUGHTER}
DESCENDANTS = MALE_DESCENDANTS | FEMALE_DESCENDANTS
SIBLING_RELS = {
    Rel.FULL_BROTHER, Rel.FULL_SISTER, Rel.PATERNAL_BROTHER,
    Rel.PATERNAL_SISTER, Rel.MATERNAL_BROTHER, Rel.MATERNAL_SISTER,
}
UTERINE = {Rel.MATERNAL_BROTHER, Rel.MATERNAL_SISTER}


@dataclass
class HeirInput:
    relationship: Rel
    count: int = 1
    is_muslim: bool = True
    caused_death: bool = False   # homicide barrier
    label: str = ""


@dataclass
class Share:
    relationship: Rel
    count: int
    total: Fraction
    reason: str = ""
    is_residuary: bool = False

    @property
    def per_person(self) -> Fraction:
        return self.total / self.count if self.count else Fraction(0)


@dataclass
class Blocked:
    relationship: Rel
    count: int
    reason: str


@dataclass
class CalculationResult:
    madhhab: Madhhab
    engine_version: str = ENGINE_VERSION
    shares: list = field(default_factory=list)
    blocked: list = field(default_factory=list)
    awl_applied: bool = False
    radd_applied: bool = False
    notes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def share_of(self, rel: Rel) -> Fraction:
        for s in self.shares:
            if s.relationship == rel:
                return s.total
        return Fraction(0)

    def total_distributed(self) -> Fraction:
        return sum((s.total for s in self.shares), Fraction(0))

    def as_table(self) -> list:
        rows = []
        for s in self.shares:
            rows.append({
                "relationship": s.relationship.value,
                "count": s.count,
                "fraction": f"{s.total.numerator}/{s.total.denominator}",
                "per_person_fraction":
                    f"{s.per_person.numerator}/{s.per_person.denominator}",
                "percentage": round(float(s.total) * 100, 4),
                "reason": s.reason,
            })
        return rows

    def to_dict(self) -> dict:
        return {
            "engineVersion": self.engine_version,
            "madhhab": self.madhhab.value,
            "sharesTable": self.as_table(),
            "blocked": [
                {"relationship": b.relationship.value, "count": b.count,
                 "reason": b.reason} for b in self.blocked
            ],
            "awlApplied": self.awl_applied,
            "raddApplied": self.radd_applied,
            "notes": self.notes,
            "warnings": self.warnings,
        }


@dataclass
class Settings:
    """Documented fiqh settings (see README + docs/VALIDATION.md)."""
    # Surplus (radd) returns to fard heirs proportionally EXCLUDING the
    # spouse (classical majority; contemporary UK default).
    radd_includes_spouse: bool = False
    # When the spouse is the ONLY heir, contemporary practice commonly
    # returns the surplus to the spouse rather than bayt al-mal.
    radd_to_sole_spouse: bool = True
    # Ja'fari: dominant opinion - wife inherits the VALUE of buildings and
    # trees but not land itself. Surfaced as a note, not a math change.
    jafari_wife_land_note: bool = True


class FaraidError(ValueError):
    pass


def validate_heirs(heirs: list) -> None:
    counts = {}
    for h in heirs:
        if h.count < 1:
            raise FaraidError(f"count must be >= 1 for {h.relationship.value}")
        counts[h.relationship] = counts.get(h.relationship, 0) + h.count
    if counts.get(Rel.HUSBAND, 0) and counts.get(Rel.WIFE, 0):
        raise FaraidError("A deceased cannot leave both a husband and a wife.")
    if counts.get(Rel.HUSBAND, 0) > 1:
        raise FaraidError("At most one husband.")
    if counts.get(Rel.WIFE, 0) > 4:
        raise FaraidError("At most four wives.")
    for r in (Rel.FATHER, Rel.MOTHER, Rel.GRANDFATHER,
              Rel.PATERNAL_GRANDMOTHER, Rel.MATERNAL_GRANDMOTHER):
        if counts.get(r, 0) > 1:
            raise FaraidError(f"At most one {r.value}.")
