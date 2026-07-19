import pytest

from faraid_engine import FaraidError, HeirInput, Rel, calculate
from .conftest import build


def test_husband_and_wife_rejected():
    with pytest.raises(FaraidError):
        calculate("hanafi", build(husband=1, wife=1))


def test_more_than_four_wives_rejected():
    with pytest.raises(FaraidError):
        calculate("hanafi", build(wife=5))


def test_two_fathers_rejected():
    with pytest.raises(FaraidError):
        calculate("hanafi", build(father=2))


def test_zero_count_rejected():
    with pytest.raises(FaraidError):
        calculate("hanafi", [HeirInput(Rel.SON, 0)])


def test_jafari_via_sunni_entry_rejected():
    from faraid_engine.sunni import calculate_sunni
    from faraid_engine.model import Madhhab
    with pytest.raises(FaraidError):
        calculate_sunni(Madhhab.JAFARI, build(son=1))


def test_engine_version_recorded():
    res = calculate("shafii", build(son=1))
    assert res.engine_version
    assert res.to_dict()["madhhab"] == "shafii"
