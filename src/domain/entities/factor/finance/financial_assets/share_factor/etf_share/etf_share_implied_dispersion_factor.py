"""
src/domain/entities/factor/finance/financial_assets/share_factor/etf_share/etf_share_implied_dispersion_factor.py

Implied ATM option dispersion of an ETF share at a time t, for options maturing about `months` ahead:

    D_call = sum_i w_i CallPremium_i / S_i,t - CallPremium_ETF / ETF_t       (puts: the same with put premiums)

Inputs are the ATM option series stored on each underlying (ETFShareFactor / CompanyShareFactor, group 'price',
subgroup 'implied', produced from the broker's option quotes - see atm_option_series_name):
    atm_<right>_premium_<m>m   the ATM option's bid / ask mid divided by the underlying's price at the quote time
    atm_<right>_dte_<m>m       days to the option's expiry (the expiry listed closest to `months` ahead)
The same expiry rule is applied to the ETF and to every constituent; a constituent whose expiry is more than
MAX_DTE_GAP days away from the ETF's is left out (the measure max_dte_gap records the largest gap).

Name: implied_<call|put>_<dispersion|etf|basket|weight_coverage|constituents|max_dte_gap>_<1..6>m.
Resolution branch A - calculate() receives (values at the value's time):
    'etf_premium' / 'etf_dte'                   [value]                      (ETFShareFactor)
    'constituent_premium' / 'constituent_dte'   {constituent symbol: [value]} (CompanyShareFactor, per entity)
    'weights'                                   {constituent symbol: weight} in force at t (injected)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_dispersion_factor import (
    ETFShareDispersionFactor, normalize_weights,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_factor import ETFShareFactor

MAX_DTE_GAP = 7                    # days between a constituent's expiry and the ETF's (same expiry rule)
ATM_FIELDS = ("premium", "bid", "ask", "strike", "moneyness", "iv", "dte")


def atm_option_series_name(right: str, field: str, months: int) -> str:
    """A leaf series of the ATM option on an underlying, e.g. atm_call_premium_1m (premium / bid / ask: per unit of
    the underlying's price; strike; moneyness = K / S - 1; iv; dte = days to expiry)."""
    return f"atm_{right}_{field}_{months}m"


def _first(values) -> Optional[float]:
    return float(values[0]) if values else None


class ETFShareImpliedDispersionFactor(ETFShareDispersionFactor):
    """Implied ATM call / put dispersion of an ETF share (see the module docstring)."""

    KIND = "implied"
    MEASURES = ("dispersion", "etf", "basket", "weight_coverage", "constituents", "max_dte_gap")

    def __init__(self, name: str = "implied_call_dispersion_1m", **kwargs):
        super().__init__(name=name, **kwargs)

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
            CompanyShareFactor,
        )
        if not self.months:
            return []
        premium = atm_option_series_name(self.right, "premium", self.months)
        dte = atm_option_series_name(self.right, "dte", self.months)
        return [
            DependencySpec(factor_type=ETFShareFactor, group="price", subgroup="implied", frequency="1d", name_in=[premium],
                           key="etf_premium"),
            DependencySpec(factor_type=ETFShareFactor, group="price", subgroup="implied", frequency="1d", name_in=[dte],
                           key="etf_dte"),
            DependencySpec(factor_type=CompanyShareFactor, group="price", subgroup="implied", frequency="1d", name_in=[premium],
                           key="constituent_premium", per_entity=True),
            DependencySpec(factor_type=CompanyShareFactor, group="price", subgroup="implied", frequency="1d", name_in=[dte],
                           key="constituent_dte", per_entity=True),
        ]

    def calculate(self, dependencies: Dict[str, Any]) -> Optional[float]:
        weights = dependencies.get("weights") or {}
        if not self.months or not weights:
            return None
        etf_premium, etf_dte = _first(dependencies.get("etf_premium")), _first(dependencies.get("etf_dte"))
        premiums = {s: _first(v) for s, v in (dependencies.get("constituent_premium") or {}).items()}
        dtes = {s: _first(v) for s, v in (dependencies.get("constituent_dte") or {}).items()}
        gaps = {s: abs(dtes[s] - etf_dte) for s in premiums if etf_dte is not None and dtes.get(s) is not None}
        usable = {s: p for s, p in premiums.items() if p is not None and p >= 0 and s in gaps and gaps[s] <= MAX_DTE_GAP}
        w, coverage = normalize_weights(weights, usable)
        if etf_premium is None or etf_premium < 0 or not w:
            return self._select(None, coverage)
        basket = sum(wi * usable[s] for s, wi in w.items())
        return self._select({"dispersion": basket - etf_premium, "etf": etf_premium, "basket": basket,
                             "constituents": float(len(w)), "max_dte_gap": max(gaps.values()) if gaps else None},
                            coverage)
