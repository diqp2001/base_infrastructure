"""Point-in-time fundamental candidates of the cross-sectional classifier (csm_fundamentals) and their use in the
10-minute project. Statements are in-memory fakes of FinancialStatementSourcePort: no API, no database."""

from datetime import date, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd
import pytest

from src.application.managers.project_managers.cross_sectionnal_project_10m import config as c
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMFeatureConfig,
    CSMLabelConfig,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import (
    CSMFeatureEngine,
    build_dataset,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_fundamentals import (
    CSMFundamentals,
    available_candidates,
    fundamental_factor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_growth_factor import (
    CompanyShareFundamentalGrowthFactor,
)
from src.domain.ports.factor.financial_statement_source_port import FinancialStatementSourcePort, StatementRecord

QUARTER_ENDS = [date(2024, 3, 31), date(2024, 6, 30), date(2024, 9, 30), date(2024, 12, 31),
                date(2025, 3, 31), date(2025, 6, 30), date(2025, 9, 30), date(2025, 12, 31)]
PUBLISHED = [d + timedelta(days=40) for d in QUARTER_ENDS]          # filed 40 days after the quarter
KNOWN = [d + timedelta(days=1) for d in PUBLISHED]                   # public the day after (StatementRecord.available_at)


class FakeStatements(FinancialStatementSourcePort):
    FREQUENCIES = ("1q", "1y")

    def __init__(self, statement: str, values: Dict[str, Dict[str, List[float]]], ends=QUARTER_ENDS,
                 published=PUBLISHED):
        self.STATEMENT = statement
        self.values = values                 # {symbol: {field: one value per quarter}}
        self.ends, self.published = ends, published
        self.calls = 0

    def fetch(self, symbol, frequency):
        self.calls += 1
        if frequency != "1q" or symbol not in self.values:
            return []
        fields = self.values[symbol]
        return [StatementRecord(symbol=symbol, statement=self.STATEMENT, frequency="1q", period=f"Q{(i % 4) + 1}",
                                fiscal_year=end.year, period_end=end, filing_date=filed, accepted_at=None,
                                reported_currency="USD", cik=None,
                                values={f: v[i] for f, v in fields.items()})
                for i, (end, filed) in enumerate(zip(self.ends, self.published))]


def income(values):
    return {"income_statement": FakeStatements("income_statement", values)}


def at(d: date, days: int = 0) -> pd.Timestamp:
    return pd.Timestamp(d) + pd.Timedelta(days=days)


NI = [10.0, 11.0, 12.0, 13.0, 15.0, 16.0, 18.0, 20.0]


# -- names --
def test_candidate_names_map_to_their_domain_factors():
    f = fundamental_factor("fund_net_income_growth_yoy_1q")
    assert isinstance(f, CompanyShareFundamentalGrowthFactor) and f.name == "net_income_growth_yoy"
    assert f.frequency == "1q" and f.usable
    assert fundamental_factor("fund_roe_ttm_1q").ttm
    for bad in ("roe_ttm_1q", "fund_roe_ttm", "fund_roe_ttm_1y", "fund_no_such_measure_1q",
                "fund_earnings_yield_1q"):          # valuation (reads a daily close) is not a candidate
        with pytest.raises(ValueError):
            fundamental_factor(bad)


def test_every_configured_10m_candidate_is_a_usable_fundamental_factor():
    assert set(c.FUNDAMENTAL_FEATURES) <= set(available_candidates())
    cfg = c.build_csm_configuration()
    assert cfg.features.fundamental_names() == list(c.FUNDAMENTAL_FEATURES)
    assert set(c.FUNDAMENTAL_FEATURES) <= set(cfg.features.feature_names())
    assert c.get_config()["fundamentals_source"] == "eulerpool"


# -- point in time --
def test_a_value_is_known_only_from_its_publication_and_equals_the_domain_calculate():
    fund = CSMFundamentals([income({"A": {"netIncome": NI}})], ["fund_net_income_growth_yoy_1q"])
    s = lambda t: fund.series("A", "fund_net_income_growth_yoy_1q", pd.DatetimeIndex([t])).iloc[0]
    # the 5th quarter (Q1 2025) gives the first year-on-year value, from its publication on
    assert np.isnan(s(at(KNOWN[4], -1)))
    expected = CompanyShareFundamentalGrowthFactor("net_income_growth_yoy", frequency="1q").calculate(
        {"value": [NI[0], NI[4]]})
    assert s(at(KNOWN[4])) == pytest.approx(expected) == pytest.approx(15 / 10 - 1)
    # the next quarter replaces it only once published
    assert s(at(KNOWN[5], -1)) == pytest.approx(expected)
    assert s(at(KNOWN[5])) == pytest.approx(16 / 11 - 1)


def test_ttm_and_balance_sheet_average_use_the_resolver_windows():
    equity = [100.0, 102.0, 104.0, 106.0, 110.0, 112.0, 114.0, 116.0]
    providers = [{**income({"A": {"netIncome": NI}}),
                  "balance_sheet": FakeStatements("balance_sheet", {"A": {"totalStockholdersEquity": equity}})}]
    fund = CSMFundamentals(providers, ["fund_roe_ttm_1q"])
    v = fund.series("A", "fund_roe_ttm_1q", pd.DatetimeIndex([at(KNOWN[7])])).iloc[0]
    # net income of the last four quarters / (equity four quarters ago + now) / 2
    assert v == pytest.approx(sum(NI[4:]) / ((equity[3] + equity[7]) / 2))


def test_a_stale_series_expires_and_a_missing_quarter_breaks_the_window():
    fund = CSMFundamentals([income({"A": {"netIncome": NI}})], ["fund_net_income_growth_1q"])
    s = lambda t: fund.series("A", "fund_net_income_growth_1q", pd.DatetimeIndex([t])).iloc[0]
    assert np.isfinite(s(at(KNOWN[7], 199)))
    assert np.isnan(s(at(KNOWN[7], 201)))                     # max_age of quarterly statements: 200 days
    ends, published = QUARTER_ENDS[:4] + QUARTER_ENDS[5:], PUBLISHED[:4] + PUBLISHED[5:]
    gap = {"income_statement": FakeStatements("income_statement", {"A": {"netIncome": NI[:4] + NI[5:]}},
                                              ends=ends, published=published)}
    fund = CSMFundamentals([gap], ["fund_net_income_growth_1q"])
    assert np.isnan(fund.series("A", "fund_net_income_growth_1q", pd.DatetimeIndex([at(KNOWN[5])])).iloc[0])


def test_the_next_provider_serves_a_share_the_first_does_not_and_statements_are_fetched_once():
    first, second = income({"A": {"netIncome": NI}}), income({"B": {"netIncome": [2 * v for v in NI]}})
    fund = CSMFundamentals([first, second], ["fund_net_income_growth_1q"])
    t = pd.DatetimeIndex([at(KNOWN[7])])
    assert fund.panel("fund_net_income_growth_1q", ["A", "B", "C"], t).iloc[0].round(6).tolist()[:2] == \
        [round(20 / 18 - 1, 6)] * 2
    assert np.isnan(fund.series("C", "fund_net_income_growth_1q", t).iloc[0])
    fund.panel("fund_net_income_growth_1q", ["A", "B"], t)
    # every provider is asked once per share (a value may switch provider over time), never again
    assert first["income_statement"].calls == second["income_statement"].calls == 3


def test_a_failed_request_gives_no_value_and_is_logged():
    class Down(FakeStatements):
        def fetch(self, symbol, frequency):
            raise ConnectionError("down")
    logs = []
    fund = CSMFundamentals([{"income_statement": Down("income_statement", {})}], ["fund_net_income_growth_1q"],
                           errors=(ConnectionError,), log=logs.append)
    assert np.isnan(fund.series("A", "fund_net_income_growth_1q", pd.DatetimeIndex([at(KNOWN[7])])).iloc[0])
    assert logs and "down" in logs[0]


# -- dataset --
def test_the_dataset_carries_the_fundamental_columns_as_of_each_bar():
    features = CSMFeatureConfig(fundamentals=("fund_net_income_growth_1q",))
    fund = CSMFundamentals([income({"A": {"netIncome": NI}, "B": {"netIncome": NI[::-1]}})],
                           features.fundamental_names())
    index = pd.date_range(at(KNOWN[6], -2), at(KNOWN[7], 2), freq="1D")
    closes = pd.DataFrame({"A": np.linspace(10, 11, len(index)), "B": np.linspace(20, 19, len(index))}, index=index)
    data = build_dataset(closes, features, CSMLabelConfig(), CSMFeatureEngine(features, fundamentals=fund))
    col = data.frame["fund_net_income_growth_1q"].unstack("asset")
    assert col.loc[at(KNOWN[6], -1), "A"] == pytest.approx(16 / 15 - 1)
    assert col.loc[at(KNOWN[6]), "A"] == pytest.approx(18 / 16 - 1)
    assert col.loc[at(KNOWN[7]), "A"] == pytest.approx(20 / 18 - 1)
    assert col.loc[at(KNOWN[7]), "B"] == pytest.approx(10 / 11 - 1)
    # without a fundamentals source the column exists but is empty (the study's coverage filter drops it)
    empty = build_dataset(closes, features, CSMLabelConfig(), CSMFeatureEngine(features))
    assert empty.frame["fund_net_income_growth_1q"].isna().all()


def test_synthetic_10_minute_run_trains_on_the_fundamentals():
    from src.application.managers.project_managers.cross_sectionnal_project_10m.backtesting.synthetic_demo import (
        run_synthetic_demo,
    )
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import (
        STMProgressTracker,
    )
    tickers = [f"T{i}" for i in range(8)]
    rng = np.random.default_rng(3)
    ni = {t: {"netIncome": list(rng.uniform(5, 15, 8))} for t in tickers}
    assets = {t: {"totalAssets": list(rng.uniform(900, 1100, 8))} for t in tickers}
    equity = {t: {"totalStockholdersEquity": list(rng.uniform(90, 110, 8))} for t in tickers}
    eps = {t: {"epsDiluted": list(rng.uniform(1, 2, 8))} for t in tickers}
    # eight quarters up to June 2026, the last one public in August 2026 (the synthetic bars start in September)
    ends = list(pd.date_range("2024-09-30", periods=8, freq="QE").date)
    published = [d + timedelta(days=40) for d in ends]
    providers = [{"income_statement": FakeStatements("income_statement", {t: {**ni[t], **eps[t]} for t in tickers},
                                                     ends=ends, published=published),
                  "balance_sheet": FakeStatements("balance_sheet", {t: {**assets[t], **equity[t]} for t in tickers},
                                                  ends=ends, published=published)}]
    # quarterly candidates only: the fakes serve no fiscal years
    quarterly = [n for n in c.FUNDAMENTAL_FEATURES if n.endswith("_1q")]
    fund = CSMFundamentals(providers, quarterly)
    tracker = STMProgressTracker()
    logs = []
    tracker.log = logs.append
    tracker.start("demo")
    _, results, cycle = run_synthetic_demo(tracker, backtest_sessions=1, n_trials=4, training_sessions=3,
                                           tickers=tickers, keep_cycle=True, fundamentals=fund)
    try:
        assert cycle.feature_engine.fundamentals is fund
        assert any(r.retrained for r in results)
        left_out = " ".join(m for m in logs if "candidates left out" in m)
        assert not [n for n in quarterly if n in left_out]                    # every quarterly one is in the study
        assert all(n in left_out for n in c.FUNDAMENTAL_FEATURES if n.endswith("_1y"))
    finally:
        cycle.factory.session.close()
