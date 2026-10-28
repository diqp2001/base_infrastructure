"""
Factor models and the kinds of series a factor regression can use (pure definitions, no I/O).

A factor regression needs factor RETURN series. They are distinct from what the factors table mostly stores
(security-level characteristics such as a 20-day return or a turnover of one share):

    EXTERNAL            published factor-mimicking returns (Kenneth R. French data library: Mkt-RF, SMB, HML,
                        RMW, CMA, RF), imported explicitly, never fabricated
    MARKET_PROXY        a market excess return built from stored prices (an ETF close minus a T-bill rate):
                        a proxy for CAPM, not the academic Mkt-RF
    MIMICKING_PORTFOLIO the long-short quantile portfolio of a security-level characteristic in a universe
                        (built by the factor research), a custom factor return
"""

from __future__ import annotations

from typing import Dict, List, Tuple

EXTERNAL, MARKET_PROXY, MIMICKING_PORTFOLIO = "external", "market_proxy", "mimicking_portfolio"
SERIES_KINDS = (EXTERNAL, MARKET_PROXY, MIMICKING_PORTFOLIO)

MKT_RF, SMB, HML, RMW, CMA, RF = "MKT_RF", "SMB", "HML", "RMW", "CMA", "RF"

FACTOR_MODELS: Dict[str, Tuple[str, List[str]]] = {
    "capm": ("CAPM", [MKT_RF]),
    "ff3": ("Fama-French 3-factor", [MKT_RF, SMB, HML]),
    "ff5": ("Fama-French 5-factor", [MKT_RF, SMB, HML, RMW, CMA]),
}
CUSTOM = "custom"

FACTOR_DESCRIPTIONS: Dict[str, str] = {
    MKT_RF: "market excess return (market minus risk-free)",
    SMB: "small minus big (size)",
    HML: "high minus low book-to-market (value)",
    RMW: "robust minus weak operating profitability",
    CMA: "conservative minus aggressive investment",
    RF: "risk-free rate (one-month T-bill)",
}

# how a strategy's reported returns relate to the risk-free rate
TOTAL, EXCESS = "total", "excess"
CONVENTIONS = {
    TOTAL: "total return of a funded portfolio: the risk-free rate is subtracted once",
    EXCESS: "return of a self-financing (long-short / position-scaled) strategy: already an excess return, the "
            "risk-free rate is not subtracted",
}

FREQUENCIES = {"D": ("daily", 252), "W-FRI": ("weekly", 52), "M": ("monthly", 12)}


def model_factors(model: str, custom: List[str] = None) -> List[str]:
    if model == CUSTOM:
        if not custom:
            raise ValueError("a custom model needs at least one factor")
        return list(custom)
    if model not in FACTOR_MODELS:
        raise ValueError(f"unknown factor model '{model}' (use {sorted(FACTOR_MODELS)} or '{CUSTOM}')")
    return list(FACTOR_MODELS[model][1])
