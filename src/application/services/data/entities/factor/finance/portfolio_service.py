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
import re
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

        For every holding whose container_id == portfolio_id:
          - If the holding's asset_id resolves to a PortfolioModel → recurse bottom-up
          - Otherwise → leaf asset: value = qty * price (or 1 for currency)
        Holding values accumulate into the portfolio total, then portfolio_value is persisted.
        """
        from src.infrastructure.models.finance.holding.holding import HoldingModel
        from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

        if as_of_date is None:
            as_of_date = datetime.now()

        from src.domain.entities.finance.portfolio.portfolio import Portfolio as PortfolioDomain

        factor_value_repo = self.factory.factor_value_local_repo if self.factory else None
        portfolio_obj = self.session.query(PortfolioModel).filter_by(id=portfolio_id).first()

        if portfolio_obj is not None:
            orm_cls = type(portfolio_obj).__name__
            entity_name = orm_cls[:-5] if orm_cls.endswith('Model') else orm_cls
            portfolio_factor_name = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', entity_name).lower() + '_value'
        else:
            portfolio_factor_name = 'portfolio_value'
        portfolio_factor = self._create_or_get_factor(portfolio_factor_name, 'value', 'portfolio_value_factor')

        total = Decimal("0")

        all_holdings = (
            self.session.query(HoldingModel)
            .filter_by(container_id=portfolio_id)
            .all()
        )

        for h in all_holdings:
            if h.asset_id is None:
                continue

            holding_type = getattr(h, 'holding_type', '') or ''
            repo = self.factory.get_local_repository(holding_type) if self.factory else None
            mapper = getattr(repo, 'mapper', None)

            is_sub_portfolio = (
                mapper is not None and issubclass(mapper.asset_class, PortfolioDomain)
            )

            entity_cls = getattr(mapper, 'entity_class', None) if mapper else None
            if entity_cls is not None:
                factor_name = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', entity_cls.__name__).lower() + '_value'
            else:
                factor_name = 'holding_value'
            holding_factor = self._create_or_get_factor(factor_name, 'holding', 'holding_value_factor')

            if is_sub_portfolio:
                # Sub-portfolio link: asset_id is the child portfolio id — recurse bottom-up
                holding_value = self.calculate_value(h.asset_id, as_of_date)
                self.logger.debug(
                    f"Holding {h.id} ({holding_type}) → sub-portfolio {h.asset_id}: {holding_value}"
                )
            else:
                # Leaf asset holding: qty × price
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
                self.logger.debug(
                    f"Holding {h.id} ({holding_type}, asset_id={h.asset_id}): "
                    f"qty={qty} × price={price} = {holding_value}"
                )

            total += holding_value
            if factor_value_repo is not None and holding_factor is not None:
                factor_value_repo._create_or_get(
                    None,
                    factor=holding_factor,
                    entity=h,
                    date=as_of_date,
                    value=str(holding_value),
                )

        if factor_value_repo is not None and portfolio_factor is not None and portfolio_obj is not None:
            factor_value_repo._create_or_get(
                None,
                factor=portfolio_factor,
                entity=portfolio_obj,
                date=as_of_date,
                value=str(total),
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
        from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel
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
            if h.asset_id is None:
                continue

            sub_portfolio = (
                self.session.query(PortfolioModel).filter_by(id=h.asset_id).first()
            )

            if sub_portfolio is not None:
                sub_value = self.calculate_value(sub_portfolio.id, as_of_date)
                total += sub_value
                breakdown.append({
                    "holding_id": h.id,
                    "type": "sub_portfolio",
                    "asset_id": sub_portfolio.id,
                    "name": getattr(sub_portfolio, "name", None),
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

    def _create_or_get_factor(self, name: str, group: str, factor_type: str):
        """Return an existing FactorModel row for (name, group) or create one."""
        from src.infrastructure.models.factor.factor import FactorModel as FactorORM
        if not hasattr(self, '_factor_cache'):
            self._factor_cache: dict = {}
        key = (name, group)
        if key not in self._factor_cache:
            factor = self.session.query(FactorORM).filter_by(name=name, group=group).first()
            if not factor:
                factor = FactorORM(
                    name=name,
                    group=group,
                    factor_type=factor_type,
                    frequency='1d',
                    data_type='numeric',
                    source='calculated',
                )
                self.session.add(factor)
                sp = self.session.begin_nested()
                try:
                    self.session.flush()
                    sp.commit()
                except Exception as e:
                    sp.rollback()
                    self.logger.warning(f"_create_or_get_factor flush failed ({name}/{group}): {e}")
                    return None
            self._factor_cache[key] = factor
        return self._factor_cache[key]

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
