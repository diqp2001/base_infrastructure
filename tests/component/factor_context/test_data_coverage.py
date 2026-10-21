"""BI-029: coverage of stored series on the seeded SQLite market (factor_world.py): gaps visible to consumers."""

from datetime import timedelta

import pytest

from src.application.services.data.entities.factor.data_coverage_service import DataCoverageService
from src.domain.entities.factor.bar_calendar import is_trading_day
from src.domain.entities.factor.coverage import Gap
from src.infrastructure.models.factor.factor_value import FactorValueModel
from tests.component.factor_context.factor_world import LAST_BAR, FactorWorld

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture
def world():
    w = FactorWorld()
    yield w
    w.close()


def close_factor(world):
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    return world.s.query(CompanyShareFactorModel).filter_by(name="close", frequency="1d").first()


def report(world, days=10):
    start = world.days[-days].date()
    return DataCoverageService(world.f).coverage(close_factor(world), world.share["AAPL"], start, LAST_BAR.date(),
                                                 as_of=LAST_BAR + timedelta(days=1))


def trading(world):
    return [d for d in world.days if is_trading_day(d.date())]


def test_the_seeded_series_is_complete(world):
    r = report(world)
    assert r.is_complete() and r.gaps == ()


def test_bars_seeded_on_exchange_holidays_are_reported_not_counted(world):
    """The fixture puts bars on every weekday; 25 Dec and 1 Jan are NYSE closures."""
    r = report(world)
    assert set(r.unexpected) == {d.date() for d in world.days[-10:] if not is_trading_day(d.date())}
    assert r.unexpected and len(r.expected) + len(r.unexpected) == 10 and r.is_complete()


def test_deleted_bars_show_as_one_gap(world):
    missing = trading(world)[-6:-3]
    world.s.query(FactorValueModel).filter(FactorValueModel.factor_id == close_factor(world).id,
                                           FactorValueModel.entity_id == world.share["AAPL"].id,
                                           FactorValueModel.date.in_(missing)).delete(synchronize_session=False)
    world.s.commit()
    r = report(world)
    assert r.gaps == (Gap(missing[0].date(), missing[-1].date(), 3),)
    assert r.completeness == pytest.approx((len(r.expected) - 3) / len(r.expected))


def test_other_entities_do_not_fill_a_gap(world):
    """Coverage is per series: MSFT's bar on a day does not cover AAPL's missing bar."""
    day = trading(world)[-2]
    world.s.query(FactorValueModel).filter(FactorValueModel.factor_id == close_factor(world).id,
                                           FactorValueModel.entity_id == world.share["AAPL"].id,
                                           FactorValueModel.date == day).delete(synchronize_session=False)
    world.s.commit()
    assert report(world).missing == (day.date(),)
