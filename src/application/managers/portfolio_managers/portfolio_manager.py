# src/application/managers/portfolio_managers/portfolio_manager.py
from src.application.managers.manager import Manager

class PortfolioManager(Manager):
    """Base class for managing portfolios."""
    def manage_portfolio(self, portfolio_id: int):
        """Base logic for portfolio management."""
        raise NotImplementedError("This method should be overridden by subclasses.")
