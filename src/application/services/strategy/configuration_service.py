"""
Former module of StrategyConfigurationService: the strategy use cases are StrategyService (strategy_service.py) since
the Strategy replaced StrategyConfiguration (2026-11-19). Kept so old imports keep working.
"""

from src.application.services.strategy.strategy_service import (  # noqa: F401
    ConfigurationInvalid,
    StrategyConfigurationService,
    StrategyInvalid,
    StrategyService,
)
