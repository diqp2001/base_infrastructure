"""BI-030: an option price outside its no-arbitrage bounds has no implied vol (pure domain)."""

from datetime import date, datetime
from types import SimpleNamespace

import pytest

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor import (
    CompanyShareOptionImpliedVolFactor,
)

T = datetime(2026, 8, 24, 16)
CALL = SimpleNamespace(strike_price=100.0, end_date=date(2026, 12, 18), option_type="call")


def iv(option_price, stock=110.0, option=CALL, rate=0.04):
    f = CompanyShareOptionImpliedVolFactor()
    value = f.calculate({"entity": option, "target_date": T, "CompanyShareOptionValueFactor": [option_price],
                         "CompanyShareValueFactor": [stock], "CompanyShareOptionRFYieldFactor": [rate]})
    return value, getattr(f, "integrity_findings", ())


def test_a_price_inside_the_bounds_has_an_implied_vol():
    value, findings = iv(14.0)
    assert value is not None and 0.05 < value < 2.0 and findings == ()


@pytest.mark.parametrize("price, rule", [(5.0, "option_lower_bound"),    # below intrinsic ~11.3 (S 110, K 100)
                                         (115.0, "option_upper_bound")])  # a call above the share
def test_a_price_outside_the_bounds_has_no_implied_vol(price, rule):
    value, findings = iv(price)
    assert value is None and [f.rule for f in findings] == [rule]


def test_quote_noise_within_the_tolerance_is_not_a_finding():
    _, findings = iv(11.25)                                 # a few cents under the discounted intrinsic
    assert findings == ()
