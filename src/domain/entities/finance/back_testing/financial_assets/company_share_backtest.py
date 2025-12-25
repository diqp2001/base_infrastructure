"""
Company Share backtest class extending ShareBackTest with company-specific functionality.
Provides corporate governance, financial reporting, and company-specific trading features.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from src.domain.entities.finance.back_testing.financial_assets.share_backtest import ShareBackTest
from src.domain.entities.finance.back_testing.financial_assets.symbol import Symbol
from src.domain.entities.finance.back_testing.enums import SecurityType


@dataclass
class FinancialReport:
    """Value object for financial reporting data."""
    report_type: str  # e.g., "quarterly", "annual"
    revenue: Decimal
    net_income: Decimal
    earnings_per_share: Decimal
    reporting_date: datetime
    period_end: datetime
    
    def __post_init__(self):
        if self.revenue < 0:
            raise ValueError("Revenue cannot be negative")


@dataclass
class CorporateAction:
    """Value object for corporate actions."""
    action_type: str  # e.g., "dividend", "split", "spinoff", "merger"
    announcement_date: datetime
    ex_date: datetime
    record_date: Optional[datetime] = None
    payment_date: Optional[datetime] = None
    action_ratio: Optional[Decimal] = None
    cash_amount: Optional[Decimal] = None
    description: Optional[str] = None


@dataclass
class InsiderTrading:
    """Value object for insider trading activity."""
    insider_name: str
    insider_title: str
    transaction_type: str  # "buy", "sell"
    shares_traded: Decimal
    price_per_share: Decimal
    transaction_date: datetime
    total_holdings_after: Optional[Decimal] = None


class CompanyShareBackTest(ShareBackTest):
    """
    Company Share class extending ShareBackTest with company-specific functionality.
    Provides corporate governance, financial reporting, and company-specific features.
    """
    
    def __init__(self, id: int, company_name: str, ticker: str, exchange_id: int, start_date: datetime, end_date: Optional[datetime] = None):
        # Create symbol for base Security class
        symbol = Symbol(
            value=ticker.upper(),
            security_type=SecurityType.EQUITY
        )
        
        # Initialize as Share with company-specific parameters
        super().__init__(id, "COMMON", hash(company_name), start_date, end_date)
        
        # Override symbol after initialization
        self._symbol = symbol
        
        # Company-specific attributes
        self.company_name = company_name
        self.ticker = ticker.upper()
        self.exchange_id = exchange_id
        
        # Company-specific features
        self._financial_reports: List[FinancialReport] = []
        self._corporate_actions: List[CorporateAction] = []
        self._insider_trading: List[InsiderTrading] = []
        self._analyst_coverage: Dict[str, Dict] = {}  # analyst_name: {rating, target_price, etc.}
        self._governance_score: Optional[Decimal] = None
        
    @property
    def company_identifier(self) -> str:
        """Get company name."""
        return self.company_name
        
    @property
    def stock_ticker(self) -> str:
        """Get stock ticker."""
        return self.ticker
    
    @property
    def latest_eps(self) -> Optional[Decimal]:
        """Get latest earnings per share."""
        if self._financial_reports:
            latest_report = max(self._financial_reports, key=lambda r: r.reporting_date)
            return latest_report.earnings_per_share
        return None
    
    @property
    def governance_score(self) -> Optional[Decimal]:
        """Get governance score."""
        return self._governance_score
    
    @property
    def analyst_coverage_count(self) -> int:
        """Get number of analysts covering the stock."""
        return len(self._analyst_coverage)
    
    def _post_process_data(self, data: "MarketData") -> None:
        """Company-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Check for earnings announcements
        self._check_earnings_announcements(data.timestamp)
        
        # Update analyst target price comparisons
        self._update_analyst_comparisons()
    
    def _check_earnings_announcements(self, current_date: datetime) -> None:
        """Check for upcoming earnings announcements."""
        for report in self._financial_reports:
            days_until_report = (report.reporting_date - current_date).days
            if 0 <= days_until_report <= 7:  # Within a week
                # Handle pre-earnings announcement effects
                pass
    
    def _update_analyst_comparisons(self) -> None:
        """Update comparisons with analyst target prices."""
        if not self._analyst_coverage:
            return
            
        target_prices = []
        for analyst_data in self._analyst_coverage.values():
            if 'target_price' in analyst_data:
                target_prices.append(analyst_data['target_price'])
        
        if target_prices and self.price > 0:
            avg_target = sum(target_prices) / len(target_prices)
            # Calculate upside/downside vs analyst targets
            upside_potential = ((avg_target - self.price) / self.price) * Decimal('100')
    
    def add_financial_report(self, report: FinancialReport) -> None:
        """Add financial report."""
        self._financial_reports.append(report)
        self._financial_reports.sort(key=lambda r: r.reporting_date, reverse=True)
        
        # Keep only last 20 reports
        if len(self._financial_reports) > 20:
            self._financial_reports = self._financial_reports[:20]
    
    def add_corporate_action(self, action: CorporateAction) -> None:
        """Add corporate action."""
        self._corporate_actions.append(action)
        self._corporate_actions.sort(key=lambda a: a.announcement_date, reverse=True)
    
    def add_insider_trading(self, trade: InsiderTrading) -> None:
        """Add insider trading activity."""
        self._insider_trading.append(trade)
        self._insider_trading.sort(key=lambda t: t.transaction_date, reverse=True)
        
        # Keep only last 100 trades
        if len(self._insider_trading) > 100:
            self._insider_trading = self._insider_trading[:100]
    
    def update_analyst_coverage(self, analyst_name: str, rating: str, target_price: Decimal, report_date: datetime) -> None:
        """Update analyst coverage."""
        self._analyst_coverage[analyst_name] = {
            'rating': rating,
            'target_price': target_price,
            'report_date': report_date
        }
    
    def set_governance_score(self, score: Decimal) -> None:
        """Set governance score (0-100)."""
        if not 0 <= score <= 100:
            raise ValueError("Governance score must be between 0 and 100")
        self._governance_score = score
    
    def calculate_pe_ratio(self) -> Optional[Decimal]:
        """Calculate price-to-earnings ratio."""
        eps = self.latest_eps
        if eps and eps > 0 and self.price > 0:
            return self.price / eps
        return None
    
    def calculate_forward_pe(self, forward_eps: Decimal) -> Optional[Decimal]:
        """Calculate forward P/E ratio."""
        if forward_eps > 0 and self.price > 0:
            return self.price / forward_eps
        return None
    
    def get_insider_sentiment(self, days: int = 90) -> Dict[str, Decimal]:
        """Get insider trading sentiment over specified days."""
        cutoff_date = datetime.now() - datetime.timedelta(days=days)
        recent_trades = [trade for trade in self._insider_trading if trade.transaction_date >= cutoff_date]
        
        buys = sum(trade.shares_traded for trade in recent_trades if trade.transaction_type == "buy")
        sells = sum(trade.shares_traded for trade in recent_trades if trade.transaction_type == "sell")
        
        return {
            "total_buys": buys,
            "total_sells": sells,
            "net_activity": buys - sells,
            "sentiment": "bullish" if buys > sells else "bearish" if sells > buys else "neutral"
        }
    
    def get_analyst_consensus(self) -> Dict[str, any]:
        """Get analyst consensus rating and target price."""
        if not self._analyst_coverage:
            return {"rating": None, "target_price": None, "coverage_count": 0}
        
        ratings = []
        target_prices = []
        
        for analyst_data in self._analyst_coverage.values():
            if 'rating' in analyst_data:
                ratings.append(analyst_data['rating'])
            if 'target_price' in analyst_data:
                target_prices.append(analyst_data['target_price'])
        
        avg_target = sum(target_prices) / len(target_prices) if target_prices else None
        
        return {
            "coverage_count": len(self._analyst_coverage),
            "target_price": avg_target,
            "ratings": ratings
        }
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for company share position.
        May vary based on company fundamentals and governance.
        """
        position_value = abs(quantity * self.price)
        
        # Base margin rate
        base_margin = Decimal('0.25')  # 25% base
        
        # Adjust for governance score
        if self._governance_score:
            if self._governance_score >= 80:
                governance_adjustment = Decimal('-0.05')  # Better governance = lower margin
            elif self._governance_score <= 40:
                governance_adjustment = Decimal('0.10')   # Poor governance = higher margin
            else:
                governance_adjustment = Decimal('0')
        else:
            governance_adjustment = Decimal('0.05')  # Unknown governance = slightly higher
        
        final_margin_rate = base_margin + governance_adjustment
        
        if quantity >= 0:  # Long position
            return position_value * final_margin_rate
        else:  # Short position
            return position_value * (final_margin_rate + Decimal('0.25'))
    
    @property
    def asset_type(self) -> str:
        """Override for backwards compatibility."""
        return "CompanyShare"
    
    def __str__(self) -> str:
        return f"CompanyShare({self.ticker}, {self.company_name}, ${self.price})"
    
    def __repr__(self) -> str:
        return (f"CompanyShare(id={self.id}, ticker={self.ticker}, "
                f"company={self.company_name}, price={self.price}, "
                f"pe={self.calculate_pe_ratio()})")