"""Universe domain rules, in memory: a listing of constituents (financial assets, factors), never weighted."""

from datetime import date

import pytest

from src.domain.entities.universe.investment_universe import InvestmentUniverse
from src.domain.entities.universe.universe import DuplicateMembership, Universe
from src.domain.entities.universe.universe_factor import UniverseFactor
from src.domain.entities.universe.universe_financial_asset import UniverseFinancialAsset


def test_a_universe_is_created_with_its_identity_fields():
    u = Universe("US banks", description="26 US banks", version=2)
    assert (u.name, u.description, u.universe_type, u.version) == ("US banks", "26 US banks", "Universe", 2)
    assert u.financial_assets == [] and u.factors == []


@pytest.mark.parametrize("kwargs", [dict(name=""), dict(name="  "), dict(name="u", version=0)])
def test_required_fields_are_enforced(kwargs):
    with pytest.raises(ValueError):
        Universe(**kwargs)


def test_members_carry_no_weight_or_rank():
    for member in (UniverseFinancialAsset(1, 10), UniverseFactor(1, 20)):
        assert not hasattr(member, "weight") and not hasattr(member, "rank")


def test_financial_assets_are_added_once():
    u = Universe("u", id=7)
    member = u.add_financial_asset(10)
    assert (member.universe_id, member.financial_asset_id) == (7, 10)
    u.add_financial_asset(11)
    with pytest.raises(DuplicateMembership):
        u.add_financial_asset(10)
    assert u.financial_asset_ids() == [10, 11]


def test_dated_memberships_may_repeat_but_never_overlap():
    u = Universe("djia")
    u.add_financial_asset(10, start_date=date(2020, 1, 1), end_date=date(2021, 1, 1))
    u.add_financial_asset(10, start_date=date(2022, 1, 1))                  # re-entered later: allowed
    with pytest.raises(DuplicateMembership):
        u.add_financial_asset(10, start_date=date(2020, 6, 1), end_date=date(2020, 9, 1))
    with pytest.raises(DuplicateMembership):
        u.add_financial_asset(10)                                            # undated = always: overlaps
    assert u.financial_asset_ids(on=date(2020, 6, 1)) == [10]
    assert u.financial_asset_ids(on=date(2021, 6, 1)) == []
    assert u.has_financial_asset(10, on=date(2023, 1, 1))


def test_a_membership_window_must_end_after_it_starts():
    with pytest.raises(ValueError):
        UniverseFinancialAsset(1, 10, start_date=date(2021, 1, 1), end_date=date(2021, 1, 1))


def test_factors_are_added_once_and_removed():
    u = Universe("factors")
    u.add_factor(5)
    u.add_factor(6)
    with pytest.raises(DuplicateMembership):
        u.add_factor(5)
    assert u.remove_factor(5) and not u.remove_factor(5)
    assert u.factor_ids() == [6]


def test_removing_a_financial_asset():
    u = Universe("u")
    u.add_financial_asset(10, start_date=date(2020, 1, 1), end_date=date(2021, 1, 1))
    u.add_financial_asset(10, start_date=date(2022, 1, 1))
    assert u.remove_financial_asset(10, start_date=date(2022, 1, 1))
    assert [m.start_date for m in u.financial_assets] == [date(2020, 1, 1)]
    assert u.remove_financial_asset(10) and u.financial_assets == []


def test_duplicate_members_are_refused_when_building_from_storage():
    with pytest.raises(DuplicateMembership):
        Universe("u", factors=[UniverseFactor(1, 5), UniverseFactor(1, 5)])


def test_an_investment_universe_is_a_universe():
    u = InvestmentUniverse("DIA holdings", entity_type="CompanyShare", currency_id=3)
    assert isinstance(u, Universe)
    assert (u.universe_type, u.entity_type, u.currency_id, u.version) == ("InvestmentUniverse", "CompanyShare", 3, 1)
    u.add_financial_asset(10)
    assert u.financial_asset_ids() == [10]
