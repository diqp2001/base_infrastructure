"""The portfolio is valued at the engine clock — the last bar of a backtest included (it equals backtest_end)."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.application.services.misbuffet.algorithm.unified_portfolio_manager import UnifiedPortfolioManager


def _manager(algorithm_time):
    upm = UnifiedPortfolioManager.__new__(UnifiedPortfolioManager)
    upm._algorithm = SimpleNamespace(
        time=algorithm_time, portfolio=SimpleNamespace(total_portfolio_value=0.0), bar_size_setting="1 day",
        config={"backtest_start": "2026-06-01 16:00:00", "backtest_end": "2026-06-03 16:00:00"})
    upm._current_portfolio_entity = SimpleNamespace(id=1, initial_cash=1_000_000)
    upm.portfolio_repo = SimpleNamespace(session=None)
    upm.repository_factory = None
    upm.logger = None
    return upm


@pytest.mark.parametrize("when", [datetime(2026, 6, 2, 16), datetime(2026, 6, 3, 16), datetime(2026, 10, 25, 12)])
def test_the_portfolio_is_valued_at_the_engine_clock(when):
    seen = {}

    def calculate_value(self, portfolio_id, as_of_date=None, frequency=None):
        seen["as_of"] = as_of_date
        return 1_009_237.20

    with patch("src.application.services.data.entities.factor.finance.portfolio_service.PortfolioService.__init__",
               lambda self, *a, **k: None), \
            patch("src.application.services.data.entities.factor.finance.portfolio_service.PortfolioService"
                  ".calculate_value", calculate_value):
        value = _manager(when).get_portfolio_value()
    assert seen["as_of"] == when            # last bar (06-03 16:00 == backtest_end) and live time included
    assert value == pytest.approx(1_009_237.20)
