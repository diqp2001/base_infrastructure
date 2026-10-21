"""
BI-036: a raw IBKR factor is ONE series — name = bar field, subgroup = IBKR whatToShow. Ingestion fetches exactly
that type; readers pick the series (MIDPOINT before TRADES for prices, legacy 'ohlc' last) and never mix them.
Seeded SQLite market (factor_world.py: legacy 'ohlc' closes).
"""

from types import SimpleNamespace

import pytest

from src.domain.entities.factor.source_policy import (
    WHAT_TO_SHOW, exact_choice, reading_order, validate_raw_definition,
)
from src.infrastructure.models.factor.factor import CompanyShareFactorModel
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.repositories.ibkr_repo.factor.what_to_show import source_choice
from tests.component.factor_context.factor_catalog import factor_classes
from tests.component.factor_context.factor_world import FactorWorld

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture
def world():
    w = FactorWorld()
    yield w
    w.close()


def factor(name):
    return dict(factor_classes())[name]


def add_series(world, subgroup, shift, ticker="AAPL", name="close"):
    """A second close series for `ticker`: the legacy closes + `shift`, under subgroup = whatToShow."""
    legacy = world.s.query(CompanyShareFactorModel).filter_by(name=name, subgroup="ohlc").first()
    series = CompanyShareFactorModel(name=name, group="price", subgroup=subgroup, frequency="1d",
                                     data_type="numeric", source="ibkr", definition=f"{name} {subgroup}",
                                     factor_type="company_share_factor")
    world.s.add(series)
    world.s.commit()
    rows = world.s.query(FactorValueModel).filter_by(factor_id=legacy.id, entity_id=world.share[ticker].id).all()
    for r in rows:
        world.s.add(FactorValueModel(factor_id=series.id, entity_id=r.entity_id, entity_type=r.entity_type,
                                     date=r.date, value=repr(float(r.value) + shift)))
    world.s.commit()
    return series


# ---- domain rules -----------------------------------------------------------------------------

def test_reading_order_and_exact_choice():
    assert reading_order("CompanyShareOption", "price", "close") == ("MIDPOINT", "TRADES")
    assert reading_order("CompanyShare", "price", "volume") == ("TRADES",)
    assert exact_choice("BID").order[0].value == "BID" and not exact_choice("BID").fallback_allowed
    assert "CALCULATED" not in WHAT_TO_SHOW and {"TRADES", "MIDPOINT", "BID", "ASK", "BID_ASK"} <= WHAT_TO_SHOW


@pytest.mark.parametrize("name, subgroup, ok", [("close", "MIDPOINT", True), ("close", "ohlc", False),
                                                ("volume", "TRADES", True), ("volume", "MIDPOINT", False)])
def test_new_raw_ibkr_definitions_name_their_series(name, subgroup, ok):
    if ok:
        validate_raw_definition(name, "price", subgroup, "ibkr")
    else:
        with pytest.raises(ValueError):
            validate_raw_definition(name, "price", subgroup, "ibkr")
    validate_raw_definition(name, "price", "ohlc", "calculated")          # only raw IBKR definitions are bound


# ---- ingestion: exactly the factor's type -----------------------------------------------------------

def test_ingestion_requests_exactly_the_series_type():
    assert [d.value for d in source_choice(SimpleNamespace(group="price", subgroup="TRADES", name="close")).order] \
        == ["TRADES"]
    assert [d.value for d in source_choice(SimpleNamespace(group="price", subgroup="BID_ASK", name="close")).order] \
        == ["BID_ASK"]
    legacy = source_choice(SimpleNamespace(group="price", subgroup="ohlc", name="close"))
    assert [d.value for d in legacy.order] == ["MIDPOINT", "TRADES"]          # legacy definitions: unchanged policy


def test_repository_defaults_and_refusals(world):
    repo = world.f.get_local_repository("CompanyShareFactor")
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
        CompanyShareFactor,
    )
    assert repo._create_or_get(CompanyShareFactor, "close", group="price", frequency="8h").subgroup == "MIDPOINT"
    assert repo._create_or_get(CompanyShareFactor, "volume", group="price", frequency="8h").subgroup == "TRADES"
    assert repo._create_or_get(CompanyShareFactor, "close", group="price", subgroup="ohlc", frequency="8h") is None


# ---- reading: one series, in order ---------------------------------------------------------------

def test_a_mark_reads_the_midpoint_series_not_a_mix(world):
    add_series(world, "TRADES", shift=1.0)
    add_series(world, "MIDPOINT", shift=0.5)
    value, deps = world.resolve(factor("CompanyShareMidPriceFactor"), world.share["AAPL"])
    assert value == pytest.approx(world.closes["AAPL"][-1] + 0.5)
    assert len(deps["CompanyShareFactor"]) == 1                           # one series: not MIDPOINT + TRADES + ohlc


def test_trades_is_read_when_there_is_no_midpoint_data(world):
    add_series(world, "TRADES", shift=1.0)
    value, _ = world.resolve(factor("CompanyShareMidPriceFactor"), world.share["AAPL"])
    assert value == pytest.approx(world.closes["AAPL"][-1] + 1.0)


def test_a_window_comes_from_one_series(world):
    add_series(world, "MIDPOINT", shift=0.5)
    _, deps = world.resolve(factor("CompanySharePriceVsMA20Factor"), world.share["AAPL"])
    prices = [float(v) for v in deps["CompanyShareFactor"]]
    assert prices == pytest.approx([c + 0.5 for c in world.closes["AAPL"][-20:]])


def test_legacy_series_still_serve_when_no_what_to_show_series_exists(world):
    value, _ = world.resolve(factor("CompanyShareMidPriceFactor"), world.share["AAPL"])
    assert value == pytest.approx(world.closes["AAPL"][-1])
