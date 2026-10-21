"""BI-035: code paths that raised NameError (ruff F821) now run. No DB, no TWS."""

import pytest

from src.application.services.misbuffet.algorithm.security import SecurityHolding
from src.application.services.misbuffet.algorithm.symbol import Symbol
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_return_factor import (
    CompanySharePortfolioReturnFactor,
)
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_variance_factor import (
    CompanySharePortfolioVarianceFactor,
)
from src.infrastructure.repositories.local_repo.factor.finance.portfolio.company_share_portfolio.company_share_portfolio_return_factor_repository import (
    CompanySharePortfolioReturnFactorRepository,
)
from src.infrastructure.repositories.local_repo.factor.finance.portfolio.company_share_portfolio.company_share_portfolio_variance_factor_repository import (
    CompanySharePortfolioVarianceFactorRepository,
)


def test_security_holding_can_be_created():
    holding = SecurityHolding(Symbol.create_equity("SPY"), quantity=10, average_price=101.5)
    assert holding.quantity_float == 10 and holding.average_price_float == 101.5
    assert holding.is_long and holding.is_invested and holding.market_price == 101.5


@pytest.mark.parametrize("repo_class, entity_class", [
    (CompanySharePortfolioReturnFactorRepository, CompanySharePortfolioReturnFactor),
    (CompanySharePortfolioVarianceFactorRepository, CompanySharePortfolioVarianceFactor),
])
def test_portfolio_factor_repositories_return_their_entity_class(repo_class, entity_class):
    assert repo_class(session=None).get_factor_entity() is entity_class


@pytest.mark.parametrize("module, blueprint, url, manager", [
    ("src.interfaces.flask.api.controllers.backtest_controller", "backtest_api", "/api/test_managers/backtest",
     "TestProjectBacktestManager"),
    ("src.interfaces.flask.api.controllers.backtest_controller", "backtest_api", "/api/test_managers/live_trading",
     "TestProjectLiveTradingManager"),
    ("src.interfaces.flask.web.controllers.dashboard_controller", "web_bp", "/api/test_managers/backtest",
     "TestProjectBacktestManager"),
    ("src.interfaces.flask.web.controllers.dashboard_controller", "web_bp", "/api/test_managers/live_trading",
     "TestProjectLiveTradingManager"),
])
def test_routes_of_removed_managers_answer_410(module, blueprint, url, manager):
    import importlib

    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(getattr(importlib.import_module(module), blueprint))
    response = app.test_client().post(url, json={"algorithm": "any"})     # dashboard routes reject an empty body
    assert response.status_code == 410
    assert response.get_json()["success"] is False and manager in response.get_json()["error"]
