"""
Market Making Project Configuration

Configuration settings for the market making project including database,
pricing, and risk management parameters.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from decimal import Decimal


@dataclass
class DatabaseConfig:
    """Database configuration for market making data storage."""
    database_url: str = "sqlite:///market_making.db"
    echo_queries: bool = False
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class PricingConfig:
    """Configuration for derivatives pricing parameters."""
    volatility_models: List[str] = None
    curve_interpolation_method: str = "cubic_spline"
    black_scholes_enabled: bool = True
    binomial_tree_steps: int = 100
    monte_carlo_paths: int = 10000
    
    def __post_init__(self):
        if self.volatility_models is None:
            self.volatility_models = ["garch", "stochastic_volatility", "implied_vol"]


@dataclass
class RiskConfig:
    """Risk management configuration."""
    max_position_size: Decimal = Decimal("1000000")
    max_portfolio_var: Decimal = Decimal("0.05")
    max_sector_concentration: Decimal = Decimal("0.30")
    stop_loss_threshold: Decimal = Decimal("0.02")
    profit_taking_threshold: Decimal = Decimal("0.05")


@dataclass
class TradingConfig:
    """Trading and execution configuration."""
    default_quote_size: Decimal = Decimal("100")
    bid_ask_spread_factor: Decimal = Decimal("0.001")
    inventory_target: Decimal = Decimal("0")
    rebalance_frequency: str = "hourly"
    execution_delay_ms: int = 100


@dataclass
class BacktestConfig:
    """Backtesting configuration."""
    initial_capital: Decimal = Decimal("1000000")
    transaction_cost_bps: Decimal = Decimal("5")
    market_impact_model: str = "linear"
    benchmark_symbol: str = "SPY"
    rebalance_frequency: str = "daily"


@dataclass
class MarketMakingConfig:
    """Main configuration class combining all settings."""
    database: DatabaseConfig = None
    pricing: PricingConfig = None
    risk: RiskConfig = None
    trading: TradingConfig = None
    backtest: BacktestConfig = None
    
    # Asset class specific settings
    supported_asset_classes: List[str] = None
    default_asset_class: str = "equity"
    
    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig()
        if self.pricing is None:
            self.pricing = PricingConfig()
        if self.risk is None:
            self.risk = RiskConfig()
        if self.trading is None:
            self.trading = TradingConfig()
        if self.backtest is None:
            self.backtest = BacktestConfig()
        if self.supported_asset_classes is None:
            self.supported_asset_classes = ["equity", "fixed_income", "commodity"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "database": {
                "database_url": self.database.database_url,
                "echo_queries": self.database.echo_queries,
                "pool_size": self.database.pool_size,
                "max_overflow": self.database.max_overflow,
            },
            "pricing": {
                "volatility_models": self.pricing.volatility_models,
                "curve_interpolation_method": self.pricing.curve_interpolation_method,
                "black_scholes_enabled": self.pricing.black_scholes_enabled,
                "binomial_tree_steps": self.pricing.binomial_tree_steps,
                "monte_carlo_paths": self.pricing.monte_carlo_paths,
            },
            "risk": {
                "max_position_size": str(self.risk.max_position_size),
                "max_portfolio_var": str(self.risk.max_portfolio_var),
                "max_sector_concentration": str(self.risk.max_sector_concentration),
                "stop_loss_threshold": str(self.risk.stop_loss_threshold),
                "profit_taking_threshold": str(self.risk.profit_taking_threshold),
            },
            "trading": {
                "default_quote_size": str(self.trading.default_quote_size),
                "bid_ask_spread_factor": str(self.trading.bid_ask_spread_factor),
                "inventory_target": str(self.trading.inventory_target),
                "rebalance_frequency": self.trading.rebalance_frequency,
                "execution_delay_ms": self.trading.execution_delay_ms,
            },
            "backtest": {
                "initial_capital": str(self.backtest.initial_capital),
                "transaction_cost_bps": str(self.backtest.transaction_cost_bps),
                "market_impact_model": self.backtest.market_impact_model,
                "benchmark_symbol": self.backtest.benchmark_symbol,
                "rebalance_frequency": self.backtest.rebalance_frequency,
            },
            "supported_asset_classes": self.supported_asset_classes,
            "default_asset_class": self.default_asset_class,
        }


def get_default_config() -> MarketMakingConfig:
    """Get default market making configuration."""
    return MarketMakingConfig()