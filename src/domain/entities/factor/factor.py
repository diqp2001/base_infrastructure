"""
src/domain/entities/factor/factor.py
"""

from __future__ import annotations
from abc import ABC
from typing import ClassVar, Optional


class Factor(ABC):
    """Abstract base class for all factors."""

    FREQUENCIES: ClassVar[dict[str, dict]] = {
        "1s":   {"label": "1 Second",      "seconds": 1,        "ibkr_label": "1 secs"},
        "5s":   {"label": "5 Seconds",     "seconds": 5,        "ibkr_label": "5 secs"},
        "1m":   {"label": "1 Minute",      "seconds": 60,       "ibkr_label": "1 min"},
        "5m":   {"label": "5 Minutes",     "seconds": 300,      "ibkr_label": "5 mins"},
        "15m":  {"label": "15 Minutes",    "seconds": 900,      "ibkr_label": "15 mins"},
        "1h":   {"label": "1 Hour",        "seconds": 3600,     "ibkr_label": "1 hour"},
        "1d":   {"label": "1 Day",         "seconds": 86400,    "ibkr_label": "1 day"},
        "1w":   {"label": "1 Week",        "seconds": 604800,   "ibkr_label": "1 week"},
        "1mth": {"label": "1 Month (30d)", "seconds": 2592000,  "ibkr_label": "1 month"},
        "1y":   {"label": "1 Year (365d)", "seconds": 31536000, "ibkr_label": "1 month"},
    }

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
        # technical
        "signal":         {"label": "Signal",          "typical_group": "technical"},
        "indicator":      {"label": "Indicator",       "typical_group": "technical"},
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

    


