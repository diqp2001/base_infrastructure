"""Daily closes of the project: the shared daily price sources
(src/application/services/data/backtest_preload/daily_price_sources.py), and the IBKR file-cache fetch through the
dispersion screener's read-only gateway connection (project-specific, so it stays in the project)."""

from datetime import date
from typing import Dict, List

from src.application.services.data.backtest_preload.daily_price_sources import (  # noqa: F401
    CacheFileReader,
    DailyHistoryUpdater,
    PreferredPrices,
    cache_path,
    fetch_eulerpool,
)


def fetch_ibkr(symbols: List[str], start: date, end: date, folder: str, progress=print) -> Dict[str, str]:
    """Fill the IBKR cache (READ-ONLY gateway connection of the screener: market data only). {symbol: problem}."""
    from src.application.managers.project_managers.etf_dispersion_screener_project import config as screener
    from src.application.managers.project_managers.etf_dispersion_screener_project.realized_history import (
        _connect as connect_history,
    )
    from src.domain.ports.finance.dispersion.option_market_data_port import MarketDataUnavailable
    config = screener.get_config()
    config["price_history_dir"] = folder
    progress(f"connecting to IBKR {config['ibkr']['host']}:{config['ibkr']['port']} (read-only, client id "
             f"{config['ibkr']['history_client_id']})")
    prices, resolver, client = connect_history(config, config["results_dir"], end.isoformat())
    problems: Dict[str, str] = {}
    try:
        for i, symbol in enumerate(symbols, 1):
            progress(f"{symbol} ({i} of {len(symbols)})")
            try:
                u = resolver([symbol], end)[symbol]
                if u is None:
                    problems[symbol] = "not a US-listed share at the broker"
                elif not prices.daily_closes(u, start, end):
                    problems[symbol] = "no daily history"
            except MarketDataUnavailable as e:
                problems[symbol] = f"market data unavailable: {e}"[:160]
    finally:
        client.disconnect()
    progress(f"done: {len(problems)} symbols without IBKR prices {problems}")
    return problems
