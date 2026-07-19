"""Ja'fari (Imami) scenarios - class system, no ta'sib, awl rejected,
radd within class. Sources: Sistani, Islamic Laws ch.38; Mughniyya,
The Five Schools (al-islam.org). See docs/VALIDATION.md."""
from fractions import Fraction

import pytest

from faraid_engine import HeirInput, Rel, calculate
from .conftest import build, run

F = Fraction
J = "jafari"


def test_husband_parents_no_umariyyatan():
    # Mother takes a FULL third of the whole estate - key Sunni/Shia split.
    run(J, {"husband": "1/2", "mother": "1/3", "father": "1/6"},
        husband=1, mother=1, father=1)


def test_wife_parents():
    run(J, {"wife": "1/4", "mother": "1/3", "father": "5/12"},
        wife=1, mother=1, father=1)


def test_awl_rejected_deficiency_on_daughters():
    # husband 1/4, parents 1/3, daughters keep only what remains: 5/12.
    res = run(J, {"husband": "1/4", "father": "1/6", "mother": "1/6",
                  "daughter": "5/12"},
              husband=1, mother=1, father=1, daughter=2)
    assert not res.awl_applied
    assert any("awl" in n.lower() for n in res.notes)


def test_husband_two_daughters_deficiency():
    run(J, {"husband": "1/4", "daughter": "3/4"}, husband=1, daughter=2)


def test_husband_one_daughter_radd():
    run(J, {"husband": "1/4", "daughter": "3/4"}, husband=1, daughter=1)


def test_wife_one_daughter_radd():
    run(J, {"wife": "1/8", "daughter": "7/8"}, wife=1, daughter=1)


def test_father_two_daughters_radd():
    # 1/6 + 2/3 = 5/6; surplus returned 1:4 -> father 1/5, daughters 4/5.
    run(J, {"father": "1/5", "daughter": "4/5"}, father=1, daughter=2)


def test_son_only():
    run(J, {"son": "1"}, son=1)


def test_daughter_only():
    run(J, {"daughter": "1"}, daughter=1)


def test_father_son():
    run(J, {"father": "1/6", "son": "5/6"}, father=1, son=1)


def test_parents_son():
    run(J, {"father": "1/6", "mother": "1/6", "son": "2/3"},
        father=1, mother=1, son=1)


def test_son_daughter_two_to_one():
    run(J, {"son": "2/3", "daughter": "1/3"}, son=1, daughter=1)


def test_mother_hajib_restricted():
    # father + 2 full brothers restrict the mother to 1/6.
    res = run(J, {"wife": "1/4", "mother": "1/6", "father": "7/12"},
              wife=1, mother=1, father=1, full_brother=2)
    assert any("hajb" in n or "restricted" in n for n in res.notes)


def test_class1_excludes_class2():
    res = run(J, {"daughter": "1"}, daughter=1, full_brother=3,
              paternal_grandfather=1)
    assert len(res.blocked) == 2


def test_grandchildren_substitute():
    res = run(J, {"sons_son": "2/3", "sons_daughter": "1/3"},
              sons_son=1, sons_daughter=1)
    assert res.warnings  # per-stirpes approximation flagged


# ---------- Class II ----------
def test_husband_full_brother():
    run(J, {"husband": "1/2", "full_brother": "1/2"},
        husband=1, full_brother=1)


def test_uterine_with_full_brother():
    run(J, {"maternal_brother": "1/6", "full_brother": "5/6"},
        maternal_brother=1, full_brother=1)


def test_two_uterines_third():
    run(J, {"maternal_brother": "1/3", "full_brother": "2/3"},
        maternal_brother=2, full_brother=1)


def test_full_blocks_consanguine():
    res = run(J, {"full_brother": "1"}, full_brother=1, paternal_brother=1)
    assert any(b.relationship == Rel.PATERNAL_BROTHER for b in res.blocked)


def test_jafari_grandfather_shares_as_brother():
    # No Hanafi-style total exclusion: grandfather counts as a brother.
    run(J, {"paternal_grandfather": "1/2", "full_brother": "1/2"},
        paternal_grandfather=1, full_brother=1)


def test_maternal_grandmother_only():
    run(J, {"maternal_grandmother": "1"}, maternal_grandmother=1)


def test_sisters_only_radd():
    run(J, {"full_sister": "1"}, full_sister=1)


def test_siblings_exclude_nephews():
    res = run(J, {"full_brother": "1"}, full_brother=1, full_brothers_son=2)
    assert any(b.relationship == Rel.FULL_NEPHEW for b in res.blocked)


# ---------- Class III ----------
def test_full_uncle_takes_all():
    run(J, {"full_paternal_uncle": "1"}, full_paternal_uncle=1)


def test_husband_uncle():
    run(J, {"husband": "1/2", "full_paternal_uncle": "1/2"},
        husband=1, full_paternal_uncle=1)


def test_class2_excludes_class3():
    res = run(J, {"full_sister": "1"}, full_sister=1, full_paternal_uncle=1)
    assert any(b.relationship == Rel.FULL_UNCLE for b in res.blocked)


# ---------- spouse rules ----------
def test_sole_husband_takes_all():
    run(J, {"husband": "1"}, husband=1)


def test_sole_wife_quarter_with_warning():
    res = calculate(J, build(wife=1))
    assert res.share_of(Rel.WIFE) == F(1, 4)
    assert res.warnings


def test_wife_land_note_present():
    res = calculate(J, build(wife=1, son=1))
    assert any("land" in n for n in res.notes)


def test_non_muslim_barred_jafari():
    res = calculate(J, [HeirInput(Rel.SON, is_muslim=False),
                        HeirInput(Rel.DAUGHTER)])
    assert res.share_of(Rel.DAUGHTER) == 1
