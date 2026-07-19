"""Scenarios where the four Sunni schools genuinely differ:
grandfather-with-siblings, al-akdariyya, al-mushtaraka - plus barrier
and flag behaviour. Sources in docs/VALIDATION.md."""
from fractions import Fraction

import pytest

from faraid_engine import HeirInput, Rel, calculate
from .conftest import build, run

F = Fraction


# ---------- grandfather with siblings ----------
@pytest.mark.parametrize("madhhab", ["maliki", "shafii", "hanbali"])
def test_gf_one_full_brother_muqasama(madhhab):
    run(madhhab, {"paternal_grandfather": "1/2", "full_brother": "1/2"},
        paternal_grandfather=1, full_brother=1)


def test_gf_one_full_brother_hanafi_blocks():
    res = run("hanafi", {"paternal_grandfather": "1"},
              paternal_grandfather=1, full_brother=1)
    assert any(b.relationship == Rel.FULL_BROTHER for b in res.blocked)


@pytest.mark.parametrize("madhhab", ["maliki", "shafii", "hanbali"])
def test_gf_three_brothers_takes_third(madhhab):
    # muqasama would give 2/8; one-third is better.
    run(madhhab, {"paternal_grandfather": "1/3", "full_brother": "2/3"},
        paternal_grandfather=1, full_brother=3)


@pytest.mark.parametrize("madhhab", ["maliki", "shafii", "hanbali"])
def test_gf_two_sisters_muqasama(madhhab):
    run(madhhab, {"paternal_grandfather": "1/2", "full_sister": "1/2"},
        paternal_grandfather=1, full_sister=2)


@pytest.mark.parametrize("madhhab", ["maliki", "shafii", "hanbali"])
def test_gf_mother_brother(madhhab):
    # mother 1/3 (one sibling); residue 2/3: muqasama 1/3 vs 2/9 vs 1/6.
    run(madhhab, {"mother": "1/3", "paternal_grandfather": "1/3",
                  "full_brother": "1/3"},
        mother=1, paternal_grandfather=1, full_brother=1)


def test_gf_mother_brother_hanafi():
    run("hanafi", {"mother": "1/3", "paternal_grandfather": "2/3"},
        mother=1, paternal_grandfather=1, full_brother=1)


@pytest.mark.parametrize("madhhab", ["maliki", "shafii", "hanbali"])
def test_gf_husband_brother(madhhab):
    run(madhhab, {"husband": "1/2", "paternal_grandfather": "1/4",
                  "full_brother": "1/4"},
        husband=1, paternal_grandfather=1, full_brother=1)


@pytest.mark.parametrize("madhhab", ["maliki", "shafii", "hanbali"])
def test_gf_daughter_brother(madhhab):
    run(madhhab, {"daughter": "1/2", "paternal_grandfather": "1/4",
                  "full_brother": "1/4"},
        daughter=1, paternal_grandfather=1, full_brother=1)


def test_gf_daughter_brother_hanafi():
    run("hanafi", {"daughter": "1/2", "paternal_grandfather": "1/2"},
        daughter=1, paternal_grandfather=1, full_brother=1)


@pytest.mark.parametrize("madhhab", ["maliki", "shafii", "hanbali"])
def test_gf_paternal_siblings_only(madhhab):
    run(madhhab, {"paternal_grandfather": "1/2", "paternal_brother": "1/2"},
        paternal_grandfather=1, paternal_brother=1)


@pytest.mark.parametrize("madhhab", ["maliki", "shafii", "hanbali"])
def test_gf_full_brother_counts_paternal(madhhab):
    # 'add: consanguine brother counted, then excluded by the full brother.
    # units = 2(gf) + 2 + 2 -> gf 2/6 = 1/3 vs third 1/3 -> gf 1/3.
    res = run(madhhab, {"paternal_grandfather": "1/3",
                        "full_brother": "2/3"},
              paternal_grandfather=1, full_brother=1, paternal_brother=1)
    assert any("counted" in note for note in res.notes)


# ---------- al-akdariyya ----------
@pytest.mark.parametrize("madhhab", ["maliki", "shafii", "hanbali"])
def test_akdariyya(madhhab):
    res = run(madhhab, {"husband": "9/27", "mother": "6/27",
                        "paternal_grandfather": "8/27",
                        "full_sister": "4/27"},
              husband=1, mother=1, paternal_grandfather=1, full_sister=1)
    assert res.awl_applied


def test_akdariyya_hanafi_sister_blocked():
    res = run("hanafi", {"husband": "1/2", "mother": "1/3",
                         "paternal_grandfather": "1/6"},
              husband=1, mother=1, paternal_grandfather=1, full_sister=1)
    assert any(b.relationship == Rel.FULL_SISTER for b in res.blocked)


# ---------- al-mushtaraka ----------
@pytest.mark.parametrize("madhhab", ["maliki", "shafii"])
def test_mushtaraka_full_brother_shares(madhhab):
    run(madhhab, {"husband": "1/2", "mother": "1/6",
                  "maternal_brother": "2/9", "full_brother": "1/9"},
        husband=1, mother=1, maternal_brother=2, full_brother=1)


@pytest.mark.parametrize("madhhab", ["hanafi", "hanbali"])
def test_mushtaraka_full_brother_excluded(madhhab):
    res = run(madhhab, {"husband": "1/2", "mother": "1/6",
                        "maternal_brother": "1/3"},
              husband=1, mother=1, maternal_brother=2, full_brother=1)
    assert any("mushtaraka" in n.lower() for n in res.notes)


# ---------- barriers ----------
@pytest.mark.parametrize("madhhab",
                         ["hanafi", "maliki", "shafii", "hanbali"])
def test_non_muslim_son_barred(madhhab):
    res = calculate(madhhab, [HeirInput(Rel.SON, is_muslim=False),
                              HeirInput(Rel.FULL_BROTHER)])
    assert res.share_of(Rel.FULL_BROTHER) == 1
    assert any("religion" in b.reason for b in res.blocked)
    assert any("wasiyya" in w for w in res.warnings)


def test_homicide_barred():
    res = calculate("hanafi", [HeirInput(Rel.SON, caused_death=True),
                               HeirInput(Rel.DAUGHTER)])
    assert res.share_of(Rel.DAUGHTER) == 1
    assert any("homicide" in b.reason.lower() for b in res.blocked)


# ---------- flags / bookkeeping ----------
def test_awl_flag_set():
    res = run("shafii", {"husband": "3/7", "full_sister": "4/7"},
              husband=1, full_sister=2)
    assert res.awl_applied and not res.radd_applied


def test_radd_flag_set():
    res = run("hanafi", {"mother": "1/3", "maternal_brother": "2/3"},
              mother=1, maternal_brother=2)
    assert res.radd_applied and not res.awl_applied


def test_no_heirs_warning():
    res = calculate("hanafi", [])
    assert res.warnings and not res.shares


def test_radd_spouse_included_setting():
    from faraid_engine import Settings
    res = calculate("hanafi", build(husband=1, daughter=1),
                    Settings(radd_includes_spouse=True))
    assert res.share_of(Rel.HUSBAND) == F(1, 3)
    assert res.share_of(Rel.DAUGHTER) == F(2, 3)


def test_sole_spouse_radd_off():
    from faraid_engine import Settings
    res = calculate("hanafi", build(wife=1),
                    Settings(radd_to_sole_spouse=False))
    assert res.share_of(Rel.WIFE) == F(1, 4)
    assert res.warnings
