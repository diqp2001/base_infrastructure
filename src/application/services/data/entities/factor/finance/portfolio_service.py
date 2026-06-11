"""
Portfolio Service - recursive portfolio valuation via the holding tree.

Valuation order per holding:
  1. Sub-portfolio holding (CompanySharePortfolioPortfolioHolding)
       → recurse into the sub-portfolio
  2. Leaf holding (CompanyShare, Currency, ...)
       → qty * price
       Price priority: DB FactorValue → market_data_service (IBKR or local)
"""

import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class PortfolioService:
    """
    Service for recursive portfolio value calculations.

    Responsibilities:
    - Traverse the holding tree (main portfolio → sub-portfolios → leaf assets)
    - Resolve asset prices from DB FactorValues or via market_data_service
    - Aggregate values bottom-up to the main portfolio
    """

    def __init__(self, session, factory, market_data_service=None):
        """
        Args:
            session:              SQLAlchemy session
            factory:              Repository factory (unused today, kept for symmetry)
            market_data_service:  Optional MarketDataService used as price fallback
        """
        self.session = session
        self.factory = factory
        self.market_data_service = market_data_service
        self.logger = logger

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_value(
        self, portfolio_id: int, as_of_date: Optional[datetime] = None
    ) -> Decimal:
        """
        Recursively compute total portfolio value by traversing the holding tree.

        Tree structure handled:
          Portfolio (main)
            ├─ CompanySharePortfolioPortfolioHolding
            │    └─ asset = CompanySharePortfolio (sub-portfolio)  → recurse
            └─ Other holdings (currency cash, direct assets)       → qty * price
        """
        from src.infrastructure.models.finance.holding.holding import HoldingModel
        from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import (
            CompanySharePortfolioPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.holding.currency_portfolio_portfolio_holding import (
            CurrencyPortfolioPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

        if as_of_date is None:
            as_of_date = datetime.now()

        holdings = (
            self.session.query(HoldingModel)
            .filter_by(container_id=portfolio_id)
            .all()
        )

        total = Decimal("0")

        for h in holdings:
            if isinstance(h, (CompanySharePortfolioPortfolioHoldingModel, CurrencyPortfolioPortfolioHoldingModel)):
                # Asset is another portfolio — recurse
                sub_value = self.calculate_value(h.asset_id, as_of_date)
                total += sub_value
                self.logger.debug(
                    f"Sub-portfolio {h.asset_id} value: {sub_value}"
                )
            else:
                # Leaf holding — price × qty
                qty = self._get_position_qty(h)
                if qty == Decimal("0"):
                    continue

                asset = (
                    self.session.query(FinancialAssetModel)
                    .filter_by(id=h.asset_id)
                    .first()
                )
                if asset is None:
                    continue

                if getattr(asset, "asset_type", "") == "currency":
                    price = Decimal("1")
                else:
                    price = self._resolve_price(asset, as_of_date)

                holding_value = qty * price
                total += holding_value
                self.logger.debug(
                    f"Holding {h.id} (asset_id={h.asset_id}): "
                    f"qty={qty} * price={price} = {holding_value}"
                )

        self.logger.info(f"Portfolio {portfolio_id} total value: {total}")
        return total

    def get_portfolio_breakdown(
        self, portfolio_id: int, as_of_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Breakdown of portfolio value by holding, including sub-portfolios.
        """
        from src.infrastructure.models.finance.holding.holding import HoldingModel
        from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import (
            CompanySharePortfolioPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.holding.currency_portfolio_portfolio_holding import (
            CurrencyPortfolioPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

        if as_of_date is None:
            as_of_date = datetime.now()

        holdings = (
            self.session.query(HoldingModel)
            .filter_by(container_id=portfolio_id)
            .all()
        )

        breakdown = []
        total = Decimal("0")

        for h in holdings:
            if isinstance(h, (CompanySharePortfolioPortfolioHoldingModel, CurrencyPortfolioPortfolioHoldingModel)):
                sub_value = self.calculate_value(h.asset_id, as_of_date)
                total += sub_value
                breakdown.append({
                    "holding_id": h.id,
                    "type": "sub_portfolio",
                    "asset_id": h.asset_id,
                    "value": sub_value,
                })
            else:
                qty = self._get_position_qty(h)
                asset = (
                    self.session.query(FinancialAssetModel).filter_by(id=h.asset_id).first()
                )
                if asset is None:
                    continue
                if getattr(asset, "asset_type", "") == "currency":
                    price = Decimal("1")
                else:
                    price = self._resolve_price(asset, as_of_date)
                holding_value = qty * price
                total += holding_value
                breakdown.append({
                    "holding_id": h.id,
                    "type": "asset",
                    "asset_id": h.asset_id,
                    "symbol": getattr(asset, "symbol", None),
                    "quantity": float(qty),
                    "price": float(price),
                    "value": holding_value,
                })

        return {
            "portfolio_id": portfolio_id,
            "total_value": total,
            "as_of_date": as_of_date,
            "holdings_count": len(holdings),
            "holdings_breakdown": breakdown,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_position_qty(self, holding) -> Decimal:
        """Return position quantity linked to this holding, or 0 if not found."""
        from src.infrastructure.models.finance.position import PositionModel

        if not holding.position_id:
            return Decimal("0")
        pos = (
            self.session.query(PositionModel).filter_by(id=holding.position_id).first()
        )
        if pos is None or pos.quantity is None:
            return Decimal("0")
        return Decimal(str(pos.quantity))

    def _resolve_price(self, asset, as_of_date: datetime) -> Decimal:
        """
        Get close price for a financial asset.

        Priority:
          1. Latest FactorValue in DB (group='price', name contains 'close')
          2. market_data_service._get_point_in_time_data (IBKR or local)
          3. Return 0 if no price available
        """
        ticker = getattr(asset, "symbol", None)

        # 1 — DB lookup
        price = self._get_close_price_from_db(asset.id, as_of_date)
        if price is not None:
            return price

        # 2 — market_data_service fallback (fetches from broker and persists to DB)
        if self.market_data_service and ticker:
            entity_class = self._domain_class_for_asset(asset)
            if entity_class:
                try:
                    price_df = self.market_data_service._get_point_in_time_data(
                        ticker, entity_class, as_of_date, "1 day", "1 D"
                    )
                    if price_df is not None and not price_df.empty:
                        row = price_df.iloc[-1]
                        close_val = row.get("close", row.get("Close"))
                        if close_val and float(close_val) > 0:
                            return Decimal(str(close_val))
                except Exception as e:
                    self.logger.warning(
                        f"_resolve_price: market service fallback failed for {ticker}: {e}"
                    )

        self.logger.debug(f"_resolve_price: no price found for asset_id={asset.id}")
        return Decimal("0")

    def _get_close_price_from_db(
        self, asset_id: int, as_of_date: datetime
    ) -> Optional[Decimal]:
        """
        Query the most recent 'close' FactorValue for this asset on or before as_of_date.
        Factors created by market_data_service use group='price' and have 'close' in their name.
        """
        from src.infrastructure.models.factor.factor import FactorModel as FactorORM
        from src.infrastructure.models.factor.factor_value import FactorValueModel

        try:
            fv = (
                self.session.query(FactorValueModel)
                .join(FactorORM, FactorValueModel.factor_id == FactorORM.id)
                .filter(
                    FactorValueModel.entity_id == asset_id,
                    FactorORM.group == "price",
                    FactorORM.name.contains("close"),
                    FactorValueModel.date <= as_of_date,
                )
                .order_by(FactorValueModel.date.desc())
                .first()
            )
            if fv and fv.value:
                val = Decimal(str(fv.value))
                return val if val > Decimal("0") else None
        except Exception as e:
            self.logger.debug(f"_get_close_price_from_db failed for asset {asset_id}: {e}")
        return None

    def _domain_class_for_asset(self, asset):
        """
        Map an ORM financial asset model to its domain class so
        market_data_service can look up ENTITY_FACTOR_MAPPING.
        Extend as new asset types are added.
        """
        from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel
        from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare

        if isinstance(asset, CompanyShareModel):
            return CompanyShare
        return None
