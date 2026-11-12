"""The calculated fundamental factors' formulas from their dependency series (no database)."""

import pytest

from src.domain.entities.factor.dependency_spec import DependencySpec
from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_factor import (
    IDENTITIES, METADATA_FIELDS, STATEMENT_FIELDS,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_growth_factor import (
    CompanyShareFundamentalGrowthFactor as Growth,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_leverage_factor import (
    CompanyShareFundamentalLeverageFactor as Leverage,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_profitability_factor import (
    CompanyShareFundamentalProfitabilityFactor as Profitability,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_valuation_factor import (
    CompanyShareFundamentalValuationFactor as Valuation,
)
from tests.fmp.fake_fmp import STATEMENTS, row


def test_margins_and_returns():
    assert Profitability("gross_margin").calculate({"gross_profit": [400.0], "revenue": [1000.0]}) == pytest.approx(0.4)
    assert Profitability("fcf_margin").calculate({"free_cash_flow": [-50.0], "revenue": [1000.0]}) == pytest.approx(-0.05)
    # ROE on the average of the opening and closing equity
    assert Profitability("roe").calculate({"net_income": [150.0], "equity": [1900.0, 2100.0]}) == pytest.approx(0.075)
    # ROIC: EBIT 200 taxed at 40 / 190, over the average (debt + equity - cash)
    deps = {"ebit": [200.0], "income_tax_expense": [40.0], "income_before_tax": [190.0], "total_debt": [1000.0, 1000.0],
            "total_equity": [2000.0, 2200.0], "cash": [300.0, 300.0]}
    assert Profitability("roic").calculate(deps) == pytest.approx(200 * (1 - 40 / 190) / 2800)
    assert Profitability("roic").calculate({**deps, "income_before_tax": [-10.0]}) is None


def test_the_ttm_variants_sum_four_quarters_and_average_the_stocks_over_them():
    roe = Profitability("roe_ttm")
    assert roe.ttm and roe.measure == "roe"
    specs = {s.result_key: s for s in roe.calculate_dependencies}
    assert (specs["net_income"].lookback, specs["equity"].lookback, specs["equity"].endpoints) == (4, 5, True)
    assert specs["net_income"].frequency is DependencySpec.SELF and specs["net_income"].name_in == ["netIncome"]
    value = roe.calculate({"net_income": [10.0, 20.0, 30.0, 40.0], "equity": [900.0, 1100.0]})
    assert value == pytest.approx(100.0 / 1000.0)
    assert roe.calculate({"net_income": [10.0, 20.0, 30.0], "equity": [900.0, 1100.0]}) is None   # a quarter missing
    assert not Profitability("roe_ttm", frequency="1y").usable                                      # TTM: quarterly only
    assert Profitability("roe_ttm", frequency="1y").calculate_dependencies == []


@pytest.mark.parametrize("factor, deps", [
    (Profitability("gross_margin"), {"gross_profit": [400.0], "revenue": [0.0]}),          # zero denominator
    (Profitability("net_margin"), {"net_income": [10.0], "revenue": [-5.0]}),              # negative revenue
    (Profitability("roe"), {"net_income": [10.0], "equity": [-100.0, -50.0]}),             # negative equity
    (Profitability("gross_margin"), {"revenue": [1000.0]}),                                # input missing
    (Profitability("gross_margin"), {"gross_profit": [None], "revenue": [1000.0]}),        # null value
    (Leverage("net_debt_to_ebitda"), {"net_debt": [700.0], "ebitda": [0.0]}),
    (Leverage("debt_to_equity"), {"total_debt": [100.0], "total_equity": [0.0]}),
])
def test_no_value_from_a_missing_input_or_a_meaningless_denominator(factor, deps):
    assert factor.calculate(deps) is None


def test_leverage():
    assert Leverage("debt_to_equity").calculate({"total_debt": [1000.0], "total_equity": [2000.0]}) == 0.5
    assert Leverage("net_debt_to_ebitda").calculate({"net_debt": [-300.0], "ebitda": [600.0]}) == -0.5   # net cash
    specs = {s.result_key: s for s in Leverage("net_debt_to_ebitda_ttm").calculate_dependencies}
    assert specs["ebitda"].lookback == 4 and specs["net_debt"].lookback is None     # a flow summed, a stock as is


def test_growth_lags_follow_the_frequency():
    qoq, yoy, ttm, annual = (Growth("revenue_growth"), Growth("revenue_growth_yoy"), Growth("revenue_growth_ttm"),
                             Growth("revenue_growth", frequency="1y"))
    assert [(s.lookback, s.endpoints) for s in qoq.calculate_dependencies] == [(2, True)]
    assert [(s.lookback, s.endpoints) for s in yoy.calculate_dependencies] == [(5, True)]
    assert [(s.lookback, s.endpoints) for s in ttm.calculate_dependencies] == [(8, False)]
    assert [(s.lookback, s.endpoints) for s in annual.calculate_dependencies] == [(2, True)]
    assert qoq.calculate({"value": [100.0, 110.0]}) == pytest.approx(0.1)
    assert yoy.calculate({"value": [80.0, 120.0]}) == pytest.approx(0.5)
    assert ttm.calculate({"value": [1, 1, 1, 1, 2, 2, 2, 2]}) == pytest.approx(1.0)
    assert qoq.calculate({"value": [-100.0, 50.0]}) is None and qoq.calculate({"value": [0.0, 50.0]}) is None
    assert qoq.calculate({"value": [100.0, -50.0]}) == pytest.approx(-1.5)          # a positive base to a loss
    assert qoq.calculate({"value": [100.0]}) is None
    # not meaningful: year on year of a yearly series, TTM of a balance sheet stock
    for odd in (Growth("revenue_growth_yoy", frequency="1y"), Growth("total_assets_growth_ttm"),
                Growth("revenue_growth_yoy_ttm")):
        assert not odd.usable and odd.calculate_dependencies == [] and odd.calculate({"value": [1.0, 2.0]}) is None
    assert Growth("eps_growth").item.field == "epsDiluted"


def test_valuation_reads_the_close():
    ey = Valuation("earnings_yield_ttm")
    keys = {s.result_key: s for s in ey.calculate_dependencies}
    assert keys["close"].name_in == ["close"] and keys["close"].frequency == "1d" and keys["eps"].lookback == 4
    assert ey.calculate({"eps": [1.0, 1.0, 1.0, 2.0], "close": [100.0]}) == pytest.approx(0.05)
    assert ey.calculate({"eps": [1.0, 1.0, 1.0, 2.0]}) is None
    fcf = Valuation("fcf_yield_ttm")
    assert {s.result_key: s.lookback for s in fcf.calculate_dependencies}["shares"] is None   # a count, never summed
    assert fcf.calculate({"free_cash_flow": [50.0] * 4, "shares": [10.0], "close": [20.0]}) == pytest.approx(1.0)


def test_names_metadata_and_point_in_time_policy():
    assert Profitability("gross_margin").subgroup == "profitability" and Growth("revenue_growth").group == "fundamental"
    for odd in (Profitability("revenue_growth"), Growth("gross_margin"), Leverage("nonsense_ttm")):
        assert odd.measure is None and odd.calculate_dependencies == [] and odd.calculate({}) is None
    raw = CompanyShareFactor("revenue", group="fundamental", subgroup="income_statement", frequency="1q", source="fmp")
    assert raw.point_in_time_policy() == Factor.POINT_IN_TIME_POLICY["1q"]
    assert raw.bar_availability_offset_seconds() == 0
    assert Profitability("gross_margin").point_in_time_policy() is None                 # calculated: recomputed
    assert CompanyShareFactor("close", group="price", frequency="1d", source="ibkr").point_in_time_policy() is None
    assert Factor.frequency_seconds("1q") * 4 == Factor.frequency_seconds("1y")
    assert "netIncome" in STATEMENT_FIELDS["income_statement"] and "netIncome" in STATEMENT_FIELDS["cash_flow"]
    assert set(METADATA_FIELDS) == {"date", "filingDate", "acceptedDate", "fiscalYear", "period", "reportedCurrency",
                                    "cik"}


def test_the_documented_identities_hold_on_the_fixture():
    endpoint = {"income_statement": "income-statement", "balance_sheet": "balance-sheet-statement",
                "cash_flow": "cash-flow-statement"}
    checked = 0
    for statement, total, parts in IDENTITIES:
        values = row(endpoint[statement], 5, "Q2")
        if total in values and all(f in values for _, f in parts):
            expected = sum(values[f] if sign == "+" else -values[f] for sign, f in parts)
            assert values[total] == pytest.approx(expected), total
            checked += 1
    assert checked >= 4 and set(STATEMENTS) == set(endpoint.values())
