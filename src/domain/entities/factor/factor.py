"""
src/domain/entities/factor/factor.py
"""

from __future__ import annotations
from abc import ABC
from typing import ClassVar, Optional


class Factor(ABC):
    """Abstract base class for all factors."""

    FREQUENCIES: ClassVar[dict[str, dict]] = {
        # seconds
        "1s":   {"label": "1 Second",      "seconds": 1,        "ibkr_label": "1 secs"},
        "5s":   {"label": "5 Seconds",     "seconds": 5,        "ibkr_label": "5 secs"},
        "10s":  {"label": "10 Seconds",    "seconds": 10,       "ibkr_label": "10 secs"},
        "15s":  {"label": "15 Seconds",    "seconds": 15,       "ibkr_label": "15 secs"},
        "30s":  {"label": "30 Seconds",    "seconds": 30,       "ibkr_label": "30 secs"},
        # minutes
        "1m":   {"label": "1 Minute",      "seconds": 60,       "ibkr_label": "1 min"},
        "2m":   {"label": "2 Minutes",     "seconds": 120,      "ibkr_label": "2 mins"},
        "3m":   {"label": "3 Minutes",     "seconds": 180,      "ibkr_label": "3 mins"},
        "5m":   {"label": "5 Minutes",     "seconds": 300,      "ibkr_label": "5 mins"},
        "10m":  {"label": "10 Minutes",    "seconds": 600,      "ibkr_label": "10 mins"},
        "15m":  {"label": "15 Minutes",    "seconds": 900,      "ibkr_label": "15 mins"},
        "20m":  {"label": "20 Minutes",    "seconds": 1200,     "ibkr_label": "20 mins"},
        "30m":  {"label": "30 Minutes",    "seconds": 1800,     "ibkr_label": "30 mins"},
        # hours
        "1h":   {"label": "1 Hour",        "seconds": 3600,     "ibkr_label": "1 hour"},
        "2h":   {"label": "2 Hours",       "seconds": 7200,     "ibkr_label": "2 hours"},
        "3h":   {"label": "3 Hours",       "seconds": 10800,    "ibkr_label": "3 hours"},
        "4h":   {"label": "4 Hours",       "seconds": 14400,    "ibkr_label": "4 hours"},
        "8h":   {"label": "8 Hours",       "seconds": 28800,    "ibkr_label": "8 hours"},
        # day / week / month
        "1d":   {"label": "1 Day",         "seconds": 86400,    "ibkr_label": "1 day"},
        "1w":   {"label": "1 Week",        "seconds": 604800,   "ibkr_label": "1 week"},
        "1mth": {"label": "1 Month (30d)", "seconds": 2592000,  "ibkr_label": "1 month"},
    }

    # Factor names whose values are read straight from an IBKR historical bar
    # (see IBKRFactorValueRepository._extract_factor_value_from_bar).
    BAR_FIELD_NAMES: ClassVar[frozenset] = frozenset({
        "open", "high", "low", "close", "volume", "barcount",
        "implied_volatility", "historical_volatility",
    })

    # Upper bound used by monitoring (stale feed alert). Bar lookups for a decision use the
    # trading-calendar rule instead (bar_calendar.bar_is_current: a newer bar due -> fetch).
    MAX_BAR_STALENESS_SECONDS: ClassVar[float] = 4 * 86400

    @classmethod
    def frequency_seconds(cls, frequency: Optional[str]) -> Optional[int]:
        """Length of one bar in seconds for a FREQUENCIES key, or None if unknown."""
        if not frequency:
            return None
        meta = cls.FREQUENCIES.get(frequency) or cls.FREQUENCIES.get(str(frequency).lower())
        return meta["seconds"] if meta else None

    def bar_availability_offset_seconds(self) -> int:
        """Seconds between a stored value's timestamp and the moment it is known.

        IBKR stamps historical bars with their START time, so the close of the
        bar stamped 12:00 in an 8h series is only known at 20:00.  For raw bar
        factors (non-calculated, name in BAR_FIELD_NAMES) this returns the bar
        length; a value stamped ``t`` may only be used at decision time
        ``>= t + offset``.  Calculated factors are stamped at the decision time
        they were computed for, so their offset is 0.
        """
        if self.source == "calculated":
            return 0
        if str(self.name).lower() not in self.BAR_FIELD_NAMES:
            return 0
        return self.frequency_seconds(self.frequency) or 0

    @classmethod
    def bar_size_to_frequency(cls, bar_size_setting: str) -> Optional[str]:
        """Convert an IBKR bar_size_setting string (e.g. '8 hours') to a FREQUENCIES key (e.g. '8h')."""
        if not bar_size_setting:
            return None
        for key, meta in cls.FREQUENCIES.items():
            if meta.get("ibkr_label") == bar_size_setting:
                return key
        # Normalise singular/plural edge case ("1 sec" → "1 secs")
        normalised = bar_size_setting if bar_size_setting.endswith('s') else bar_size_setting + 's'
        for key, meta in cls.FREQUENCIES.items():
            if meta.get("ibkr_label") == normalised:
                return key
        return None

    GROUPS: ClassVar[dict[str, dict]] = {
        # ── canonical keys (use these for new factors) ──────────────────────
        "price":        {"label": "Price",        "description": "Market price data"},
        "return":       {"label": "Return",        "description": "Price return / P&L"},
        "holding":      {"label": "Holding",       "description": "Single holding metrics"},
        "portfolio":    {"label": "Portfolio",     "description": "Aggregated portfolio metrics"},
        "momentum":     {"label": "Momentum",      "description": "Momentum / trend signals"},
        "technical":    {"label": "Technical",     "description": "Technical indicator signals"},
        "volatility":   {"label": "Volatility",    "description": "Risk / volatility metrics"},
        "fundamental":  {"label": "Fundamental",   "description": "Fundamental financial data"},
        "economic":     {"label": "Economic",      "description": "Macro-economic indicators"},
        "risk":         {"label": "Risk",          "description": "Risk measures (VaR, CVaR…)"},
        "valuation":    {"label": "Valuation",     "description": "Valuation ratios and metrics"},
        "greek":        {"label": "Greek",         "description": "Options / structured product Greeks"},
        "liquidity":    {"label": "Liquidity",     "description": "Liquidity metrics"},
        "value":        {"label": "Value",         "description": "Market value / portfolio value metrics"},
        "volume":       {"label": "Volume",        "description": "Volume and turnover metrics"},
        "order":        {"label": "Order",         "description": "Order-level factors (quantity, price)"},
        "transaction":  {"label": "Transaction",   "description": "Transaction-level factors"},
        "position":     {"label": "Position",      "description": "Position-level factors"},
        "price_model":  {"label": "Price Model",   "description": "Option pricing model outputs (BSM, Heston, …)"},
    }

    SUBGROUPS: ClassVar[dict[str, dict]] = {
        # ── canonical keys (use these for new factors) ──────────────────────
        # price
        "mid_price_true": {"label": "True Mid Price",  "typical_group": "price"},
        "mid_price":      {"label": "Mid Price",       "typical_group": "price"},
        "close":          {"label": "Close Price",     "typical_group": "price"},
        "open":           {"label": "Open Price",      "typical_group": "price"},
        "high":           {"label": "High Price",      "typical_group": "price"},
        "low":            {"label": "Low Price",       "typical_group": "price"},
        "last":           {"label": "Last Price",      "typical_group": "price"},
        "bid":            {"label": "Bid Price",       "typical_group": "price"},
        "ask":            {"label": "Ask Price",       "typical_group": "price"},
        "rate":           {"label": "Rate",            "typical_group": "price"},
        "ohlc":           {"label": "OHLC",            "typical_group": "price"},
        # return
        "daily":          {"label": "Daily",           "typical_group": "return"},
        "minutes":        {"label": "Minutes",         "typical_group": "return"},
        # holding / portfolio
        "value":          {"label": "Value",           "typical_group": "holding"},
        "quantity":       {"label": "Quantity",        "typical_group": "holding"},
        "weight":         {"label": "Weight",          "typical_group": "portfolio"},
        # volatility
        "realized":       {"label": "Realized",        "typical_group": "volatility"},
        "implied":        {"label": "Implied",         "typical_group": "volatility"},
        # technical / ML scores
        "signal":         {"label": "Signal",          "typical_group": "technical"},
        "indicator":      {"label": "Indicator",       "typical_group": "technical"},
        "score":          {"label": "Score",           "typical_group": "fundamental"},
        # bond / fixed income
        "yield":          {"label": "Yield",           "typical_group": "bond"},
        "spread":         {"label": "Spread",          "typical_group": "bond"},
        "duration":       {"label": "Duration",        "typical_group": "bond"},
        "convexity":      {"label": "Convexity",       "typical_group": "bond"},
        "interest_rate":  {"label": "Interest Rate",   "typical_group": "bond"},
        # greeks
        "delta":          {"label": "Delta",           "typical_group": "greek"},
        "gamma":          {"label": "Gamma",           "typical_group": "greek"},
        "vega":           {"label": "Vega",            "typical_group": "greek"},
        "theta":          {"label": "Theta",           "typical_group": "greek"},
        "rho":            {"label": "Rho",             "typical_group": "greek"},
        # value / asset
        "asset":                {"label": "Asset",               "typical_group": "value"},
        # return frequency-based
        "weekly":               {"label": "Weekly",              "typical_group": "return"},
        "monthly":              {"label": "Monthly",             "typical_group": "return"},
        # volume
        "turnover":             {"label": "Turnover",            "typical_group": "volume"},
        "trend":                {"label": "Trend",               "typical_group": "volume"},
        # price
        "range":                {"label": "Range",               "typical_group": "price"},
        # order / trading lifecycle
        "price":                {"label": "Price",               "typical_group": "order"},
        # option base factors (OHLCV price data for an option contract)
        "option":               {"label": "Option",              "typical_group": "price"},
        # option pricing models
        "black_scholes":        {"label": "Black-Scholes",       "typical_group": "price_model"},
        "binomial_tree":        {"label": "Binomial Tree",       "typical_group": "price_model"},
        "stochastic_volatility":{"label": "Stochastic Vol",      "typical_group": "price_model"},
        "stochastic_rates":     {"label": "Stochastic Rates",    "typical_group": "price_model"},
        "sabr":                 {"label": "SABR",                "typical_group": "price_model"},
        "jump_diffusion":       {"label": "Jump Diffusion",      "typical_group": "price_model"},
        "local_volatility":     {"label": "Local Volatility",    "typical_group": "price_model"},
        # ── legacy values (pre-canonical; migrate to lowercase over time) ───
        "Price":         {"label": "Price (legacy)",        "legacy": True, "canonical": "mid_price"},
        "Yield":         {"label": "Yield (legacy)",        "legacy": True, "canonical": "yield"},
        "Spread":        {"label": "Spread (legacy)",       "legacy": True, "canonical": "spread"},
        "Duration":      {"label": "Duration (legacy)",     "legacy": True, "canonical": "duration"},
        "Convexity":     {"label": "Convexity (legacy)",    "legacy": True, "canonical": "convexity"},
        "Interest Rate": {"label": "Interest Rate (legacy)","legacy": True, "canonical": "interest_rate"},
        "Delta":         {"label": "Delta (legacy)",        "legacy": True, "canonical": "delta"},
        "Gamma":         {"label": "Gamma (legacy)",        "legacy": True, "canonical": "gamma"},
        "Vega":          {"label": "Vega (legacy)",         "legacy": True, "canonical": "vega"},
        "Theta":         {"label": "Theta (legacy)",        "legacy": True, "canonical": "theta"},
        "Rho":           {"label": "Rho (legacy)",          "legacy": True, "canonical": "rho"},
    }

    DATA_TYPES: ClassVar[dict[str, dict]] = {
        # ── canonical keys ───────────────────────────────────────────────────
        "decimal":    {"label": "Decimal",    "python_type": "Decimal", "description": "High-precision financial value"},
        "numeric":    {"label": "Numeric",    "python_type": "float",   "description": "General floating-point number"},
        "integer":    {"label": "Integer",    "python_type": "int",     "description": "Whole number"},
        "boolean":    {"label": "Boolean",    "python_type": "bool",    "description": "True / False flag"},
        "string":     {"label": "String",     "python_type": "str",     "description": "Text value"},
        "percentage": {"label": "Percentage", "python_type": "float",   "description": "Value in [0, 1] or [0, 100]"},
        # ── legacy ──────────────────────────────────────────────────────────
        "float":      {"label": "Float (legacy)", "python_type": "float", "legacy": True, "canonical": "numeric"},
    }

    SOURCES: ClassVar[dict[str, dict]] = {
        # ── canonical keys ───────────────────────────────────────────────────
        "ibkr":                 {"label": "Interactive Brokers",   "ibkr_supported": True},
        "calculated":           {"label": "Calculated",            "ibkr_supported": False},
        "fmp":                  {"label": "Financial Modeling Prep","ibkr_supported": False},
        "yahoo":                {"label": "Yahoo Finance",          "ibkr_supported": False},
        "alpha_vantage":        {"label": "Alpha Vantage",         "ibkr_supported": False},
        "quandl":               {"label": "Quandl",                "ibkr_supported": False},
        
    }

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
    ):
        self.id = factor_id  # Repository will assign sequential ID if None
        self.name = name

        if group not in self.GROUPS:
            raise ValueError(f"Invalid group '{group}'. Allowed values: {list(self.GROUPS.keys())}")
        self.group = group

        if subgroup is not None and subgroup not in self.SUBGROUPS:
            raise ValueError(f"Invalid subgroup '{subgroup}'. Allowed values: {list(self.SUBGROUPS.keys())}")
        self.subgroup = subgroup

        if frequency is not None and frequency not in self.FREQUENCIES:
            raise ValueError(f"Invalid frequency '{frequency}'. Allowed values: {list(self.FREQUENCIES.keys())}")
        self.frequency = frequency

        if data_type is not None and data_type not in self.DATA_TYPES:
            raise ValueError(f"Invalid data_type '{data_type}'. Allowed values: {list(self.DATA_TYPES.keys())}")
        self.data_type = data_type

        if source is not None and source not in self.SOURCES:
            raise ValueError(f"Invalid source '{source}'. Allowed values: {list(self.SOURCES.keys())}")
        self.source = source

        self.definition = definition

    


