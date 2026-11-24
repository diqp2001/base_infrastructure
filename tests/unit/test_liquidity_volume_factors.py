"""
The liquidity / volume factors over 5d..12m (company_share_liquidity_volume_factors, 2026-11-23): formulas on known
numbers, every touch point wired (FactorMapper dispatch, repositories, library), and the CSM feature engine
computing them when its opt-in group is on.
"""

import math

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share import (
    company_share_liquidity_volume_factors as lv,
)

CLASSES = lv.LIQUIDITY_VOLUME_FACTOR_CLASSES


def test_twenty_seven_factors_with_their_periods():
    names = [c().name for c in CLASSES]
    assert len(CLASSES) == 27 and len(set(names)) == 27
    assert "amihud_illiquidity_12m" in names and "relative_volume_6m" in names and "avg_price_range_3m" in names
    assert lv.CompanyShareAvgDollarVolume12MFactor.PERIOD == 252 and lv.CompanyShareAmihudIlliquidity5DFactor.PERIOD == 5


def test_formulas_on_known_numbers():
    closes = [100.0, 110.0, 99.0, 99.0, 108.9, 108.9]       # returns +10%, -10%, 0, +10%, 0
    volumes = [1000.0, 2000.0, 1000.0, 3000.0, 2000.0, 2000.0]
    deps = {"closes": closes, "volumes": volumes, "highs": [c * 1.1 for c in closes], "lows": [c * 0.9 for c in closes]}
    f = lv.CompanyShareAvgDollarVolume5DFactor()
    assert f.calculate(deps) == pytest.approx(sum(c * v for c, v in zip(closes[-5:], volumes[-5:])) / 5)
    returns = [0.10, -0.10, 0.0, 0.10, 0.0]
    amihud = sum(abs(r) / (c * v) for r, c, v in zip(returns, closes[1:], volumes[-5:])) / 5 * 1e9
    assert lv.CompanyShareAmihudIlliquidity5DFactor().calculate(deps) == pytest.approx(amihud)
    w = volumes[-5:]
    assert lv.CompanyShareVolumeVolatility5DFactor().calculate(deps) == pytest.approx(np.std(w, ddof=1) / np.mean(w))
    vpt = sum(v * r for v, r in zip(volumes[-5:], returns)) / sum(volumes[-5:])
    assert lv.CompanyShareVolumePriceTrend5DFactor().calculate(deps) == pytest.approx(vpt)
    assert lv.CompanyShareAvgPriceRange5DFactor().calculate(deps) == pytest.approx(0.2)
    year = {"volumes": [1.0] * 247 + [2.0] * 5}
    assert lv.CompanyShareRelativeVolume5DFactor().calculate(year) == pytest.approx(2.0 / (257 / 252))


def test_no_value_on_an_incomplete_window_or_a_zero_volume():
    assert lv.CompanyShareAvgDollarVolume1MFactor().calculate({"closes": [1.0] * 5, "volumes": [1.0] * 5}) is None
    zero = {"closes": [100.0] * 6, "volumes": [0.0] * 6}
    assert lv.CompanyShareAmihudIlliquidity5DFactor().calculate(zero) is None
    assert lv.CompanyShareVolumePriceTrend5DFactor().calculate(zero) is None
    assert lv.CompanyShareRelativeVolume1MFactor().calculate({"volumes": [1.0] * 100}) is None


def test_every_factor_is_wired_through_the_infrastructure():
    from src.application.services.data.entities.factor.factor_library.finance.financial_assets import (
        company_share_library as library,
    )
    from src.infrastructure.repositories.mappers.factor.factor_mapper import DISCRIMINATOR_CLASS_MAP
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    from src.infrastructure.models import ModelBase
    engine = create_engine("sqlite://")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    factory = RepositoryFactory(session)
    entries = {v["name"]: v for k, v in vars(library).items() if isinstance(v, dict)
               for v in v.values() if isinstance(v, dict) and "class" in v}
    for cls in CLASSES:
        identity = f"company_share_{cls().name}_factor"
        assert DISCRIMINATOR_CLASS_MAP[identity] is cls
        repo = factory.get_local_repository(cls.__name__)
        assert repo is not None and repo.mapper.get_factor_entity() is cls
        created = repo._create_or_get(cls, cls().name)
        assert isinstance(created, cls) and created.id is not None
        again = repo._create_or_get(cls, cls().name)
        assert again.id == created.id                                    # read back, not duplicated
        assert entries[cls().name]["class"] is cls
    session.close()


def test_the_csm_engine_computes_them_when_the_group_is_on():
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
        CSMFeatureConfig,
    )
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import CSMFeatureEngine
    rng = np.random.default_rng(4)
    days = pd.bdate_range("2023-01-02", periods=300)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(days))))
    frame = pd.DataFrame({"close": close, "volume": rng.integers(1_000, 5_000, len(days)).astype(float),
                          "high": close * 1.01, "low": close * 0.99}, index=days)
    on = CSMFeatureEngine(CSMFeatureConfig(liquidity_volume=True)).features_at("X", frame, [days[-1], days[100]])
    names = [c().name for c in CLASSES]
    assert on.loc[days[-1], names].notna().all()                         # every window complete at day 300
    assert on.loc[days[100], ["avg_dollar_volume_12m", "relative_volume_1m"]].isna().all()   # 12m window not yet
    off = CSMFeatureEngine(CSMFeatureConfig()).features_at("X", frame, [days[-1]])
    assert not set(names) & set(off.columns)
    assert math.isfinite(on.loc[days[-1], "amihud_illiquidity_1m"])


# -- share turnover (2026-11-24): volume / shares outstanding from the balance sheet --

TURNOVER = lv.TURNOVER_FACTOR_CLASSES


def test_turnover_is_mean_volume_over_the_latest_share_count():
    assert [c().name for c in TURNOVER] == ["turnover_5d", "turnover_1m", "turnover_3m", "turnover_6m", "turnover_12m"]
    deps = {"volumes": [1e6] * 16 + [2e6] * 5, "shares_outstanding": [5e8]}
    assert lv.CompanyShareTurnover5DFactor().calculate(deps) == pytest.approx(2e6 / 5e8)
    assert lv.CompanyShareTurnover1MFactor().calculate(deps) == pytest.approx((16e6 + 10e6) / 21 / 5e8)
    assert lv.CompanyShareTurnover3MFactor().calculate(deps) is None              # window incomplete
    assert lv.CompanyShareTurnover5DFactor().calculate({"volumes": [1.0] * 5}) is None             # no share count
    assert lv.CompanyShareTurnover5DFactor().calculate({"volumes": [1.0] * 5, "shares_outstanding": [0.0]}) is None
    assert not set(TURNOVER) & set(CLASSES)                                        # not a bar-only factor


def test_turnover_reads_the_quarterly_balance_sheet_share_count():
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_factor import (  # noqa: E501
        BALANCE_SHEET, STATEMENT_FIELDS, STATEMENT_SOURCES,
    )
    assert lv.SHARES_OUTSTANDING in STATEMENT_FIELDS[BALANCE_SHEET]
    volume, shares = lv.CompanyShareTurnover1MFactor().calculate_dependencies
    assert volume.name_in == ["volume"] and volume.lookback == 21
    assert (shares.group, shares.subgroup, shares.frequency) == ("fundamental", BALANCE_SHEET, "1q")
    assert shares.name_in == [lv.SHARES_OUTSTANDING] and list(shares.source_in) == list(STATEMENT_SOURCES)


def test_turnover_factors_are_wired_through_the_infrastructure():
    from src.infrastructure.repositories.mappers.factor.factor_mapper import DISCRIMINATOR_CLASS_MAP
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    from src.infrastructure.models import ModelBase
    engine = create_engine("sqlite://")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    factory = RepositoryFactory(session)
    for cls in TURNOVER:
        assert DISCRIMINATOR_CLASS_MAP[f"company_share_{cls().name}_factor"] is cls
        created = factory.get_local_repository(cls.__name__)._create_or_get(cls, cls().name)
        assert isinstance(created, cls) and (created.group, created.subgroup) == ("volume", "turnover")
    session.close()
