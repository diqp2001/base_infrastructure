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

        orm_cls = type(portfolio_obj).__name__
        portfolio_type = getattr(portfolio_obj, 'portfolio_type', '') or ''
        entity_name = portfolio_type
        portfolio_factor_name = portfolio_type + 'ValueFactor'
        
            
        portfolio_factor_repo  = self.factory.get_local_repository(portfolio_factor_name)
        #create factor for portfolio value
        portfolio_factor = portfolio_factor_repo._create_or_get(portfolio_factor_name,entity_name) if portfolio_factor_repo else None
        
        
        total = Decimal("0")
        # Get all holdings for this portfolio
        all_holdings = (
            self.session.query(HoldingModel)
            .filter_by(container_id=portfolio_id)
            .all()
        )

        for h in all_holdings:
            if h.asset_id is None:
                continue
            #get the holding type from the holding model
            holding_type = getattr(h, 'holding_type')
            #get the repository for the holding type
            repo = self.factory.get_local_repository(holding_type) if self.factory else None
            #get the mapper for the repository
            mapper = getattr(repo, 'mapper', None)
            #check if the mapper's asset_class (an holding always has a asset_class and a container_class) is a subclass of PortfolioDomain
            is_sub_portfolio = (
                mapper is not None and issubclass(mapper.asset_class, PortfolioDomain)
            )
            #get the entity class from the mapper
            entity_cls = getattr(mapper, 'entity_class', None) if mapper else None
            if entity_cls is not None:
                #get the factor name for the holding type
                factor_name =  entity_cls.__name__ + 'ValueFactor'
            #get the repository for the factor name for the holding type
            repo = self.factory.get_local_repository(factor_name)
            #create or get the factor for the holding type
            holding_factor = repo._create_or_get(factor_name,holding_type) if repo else None

            # Determine the currency the holding value is denominated in.
            # Prefer the asset's own currency_id; if the asset IS a currency
            # (no currency_id attribute), use the asset's id directly.
            asset_orm = self.session.query(FinancialAssetModel).filter_by(id=h.asset_id).first()
            holding_currency_id = getattr(asset_orm, 'currency_id', None)
            if holding_currency_id is None and asset_orm is not None:
                if getattr(asset_orm, 'asset_type', None) == 'currency':
                    holding_currency_id = h.asset_id

            if is_sub_portfolio:
                # Sub-portfolio link: asset_id is the child portfolio id — recurse bottom-up
                holding_value = self.calculate_value(h.asset_id, as_of_date)
                _holding_fv_kwargs = {'value': str(holding_value)}
                self.logger.debug(
                    f"Holding {h.id} ({holding_type}) → sub-portfolio {h.asset_id}: {holding_value}"
                )
            else:
                factor_value = (
                    factor_value_repo._create_or_get(
                        None, None,
                        factor=holding_factor, entity=h, date=as_of_date,
                        currency_id=holding_currency_id,
                    )
                    if factor_value_repo and holding_factor else None
                )

            
            

        if factor_value_repo is not None and portfolio_factor is not None and portfolio_obj is not None:
            factor_value = factor_value_repo._create_or_get(
                None,
                factor=portfolio_factor,
                entity=portfolio_obj,
                date=as_of_date,
            )
            if factor_value is not None and getattr(factor_value, 'value', None) is not None:
                total = Decimal(str(factor_value.value))
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
                    price = self._resolve_value(asset, as_of_date)
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

    

    def _get_position_model(self, holding):
        """Return the PositionModel linked to this holding, or None."""
        from src.infrastructure.models.finance.position import PositionModel
        if not getattr(holding, 'position_id', None):
            return None
        return self.session.query(PositionModel).filter_by(id=holding.position_id).first()

    def _get_position_qty(self, holding) -> Decimal:
        """Return position quantity linked to this holding, or 0 if not found."""
        pos = self._get_position_model(holding)
        if pos is None or pos.quantity is None:
            return Decimal("0")
        return Decimal(str(pos.quantity))

    def _resolve_value(self, asset, as_of_date: datetime) -> Decimal:
        """
        Get asset value via the factor/factor_value system.

        The ValueFactor name is derived dynamically from the asset ORM class:
          e.g. CompanyShareModel → company_share_value / company_share_value_factor
               ETFShareModel     → etf_share_value    / etf_share_value_factor

        Priority:
          1. Existing FactorValue in DB for the asset's ValueFactor
          2. market_data_service fallback — fetches from broker and persists as FactorValue
          3. Return 0 if no price available
        """
        ticker = getattr(asset, "symbol", None)
        factor_value_repo = self.factory.factor_value_local_repo if self.factory else None

        # Derive factor name/type from the asset ORM class name
        orm_cls = type(asset).__name__
        entity_name = orm_cls[:-5] if orm_cls.endswith('Model') else orm_cls
        entity_snake = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', entity_name).lower()
        value_factor_name = entity_snake + '_value'
        value_factor_type = entity_snake + '_value_factor'

        # 1 — create or get the asset's ValueFactor entity
        value_factor = self._create_or_get_factor(value_factor_name, 'value', value_factor_type)

        # 2 — look up existing FactorValue for this asset + date
        if factor_value_repo and value_factor and value_factor.id:
            date_str = as_of_date.strftime("%Y-%m-%d %H:%M:%S")
            existing = factor_value_repo.get_by_factor_entity_date(
                value_factor.id, asset.id, date_str
            )
            if existing and existing.value:
                val = Decimal(str(existing.value))
                if val > Decimal("0"):
                    return val

        # 3 — market_data_service fallback; persist result as ValueFactor FactorValue
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
                            price = Decimal(str(close_val))
                            if factor_value_repo and value_factor and value_factor.id:
                                factor_value_repo._create_or_get_legacy(
                                    factor_id=value_factor.id,
                                    entity_id=asset.id,
                                    date=as_of_date,
                                    value=str(price),
                                )
                            return price
                except Exception as e:
                    self.logger.warning(
                        f"_resolve_value: market service fallback failed for {ticker}: {e}"
                    )

        self.logger.debug(f"_resolve_value: no value found for asset_id={asset.id}")
        return Decimal("0")

    

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
