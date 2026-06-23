"""
Unified Portfolio Manager

This module provides a unified portfolio management system that replaces the dual
portfolio tracking approach with a single system using domain entities and repositories.

The UnifiedPortfolioManager acts as the single source of truth for all portfolio 
operations in QCAlgorithm, eliminating the need for separate custom tracking.
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal

from application.services.data.entities.factor.factor_library.factor_definition_config import FACTOR_LIBRARY
from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.finance.portfolio.portfolio_value_factor import PortfolioValueFactor
from src.domain.entities.finance.portfolio.portfolio import Portfolio
from src.domain.entities.finance.holding.holding import Holding
from src.domain.entities.finance.holding.position import Position, PositionType
from src.domain.entities.finance.order.order import Order, OrderType, OrderSide, OrderStatus
from src.domain.entities.finance.transaction.transaction import Transaction, TransactionType, TransactionStatus


class UnifiedPortfolioManager:
    """
    Unified portfolio management system that replaces dual portfolio tracking.
    
    This manager acts as the single source of truth for all portfolio operations,
    using domain entities and repositories instead of custom tracking dictionaries.
    """

    def __init__(self, entity_service, market_data_service, logger=None):
        """
        Initialize the unified portfolio manager.
        
        Args:
            entity_service: Service providing access to all repositories
            market_data_service: Service for handling market data
            logger: Optional logger for debugging
        """
        if entity_service is None:
            raise ValueError("entity_service cannot be None")
        if entity_service.repository_factory is None:
            raise ValueError("entity_service.repository_factory cannot be None")
        
        self.repository_factory = entity_service.repository_factory
        self.entity_service = entity_service  # Keep reference for fallback market data service creation
        self.market_data_service = market_data_service
        self.logger = logger
        
        # Log market_data_service state for debugging
        if logger:
            if market_data_service is None:
                logger.warning("⚠️ UnifiedPortfolioManager initialized with None market_data_service - will create on demand")
            elif not hasattr(market_data_service, '_create_or_get'):
                logger.warning(f"⚠️ Market data service {type(market_data_service)} missing _create_or_get method")
            else:
                logger.info(f"✅ UnifiedPortfolioManager initialized with {type(market_data_service).__name__}")
        
        self._current_portfolio_entity: Optional[Portfolio] = None
        self._order_ticket_mapping: Dict[str, str] = {}  # QC order_id -> domain order_id
        self.portfolio_value_factor = None  # set by register_portfolio_with_config
        self._last_pv_snapshot_time = None  # guards one FactorValue write per bar

        # Algorithm reference injected after construction (avoids circular init)
        self._algorithm = None

        # Repository shortcuts
        self.portfolio_repo = self.repository_factory.portfolio_local_repo
        self.holding_repo = self.repository_factory.holding_local_repo
        self.position_repo = self.repository_factory.position_local_repo
        self.order_repo = self.repository_factory.order_local_repo
        self.transaction_repo = self.repository_factory.transaction_local_repo

        # TradeManager is the execution engine; UPM is its orchestrator
        from .trade_manager import TradeManager
        self._trade_manager = TradeManager(self.repository_factory, logger=logger)

    # def register_portfolio(
    #     self, 
    #     name: str, 
    #     initial_cash: float = 100000.0, 
    #     portfolio_type: str = "BACKTEST"
    # ) -> Optional[Portfolio]:
    #     """
    #     Register or retrieve a portfolio entity (legacy method).
        
    #     Args:
    #         name: Portfolio name
    #         initial_cash: Initial cash amount
    #         portfolio_type: Type of portfolio
            
    #     Returns:
    #         Portfolio entity or None if registration failed
    #     """
    #     try:
    #         # Use standardized repository method to get or create portfolio
    #         portfolio = self.portfolio_repo._create_or_get(
    #             name=name,
    #             portfolio_type=portfolio_type,
    #             initial_cash=initial_cash,
    #             currency_code="USD"
    #         )
            
    #         self._current_portfolio_entity = portfolio
            
    #         # Create portfolio value factor using market data service
    #         if self.market_data_service and hasattr(self.market_data_service, '_create_or_get'):
    #             try:
    #                 # Configure entity_config for MarketDataService._create_or_get method
    #                 entity_config = {
    #                     'entity_class': PortfolioValueFactor,
    #                     'entity_symbol': f"portfolio_value_{portfolio.name}",
    #                     'factor_type': "portfolio_value_factor",
    #                     'group': "value",
    #                     'subgroup': "portfolio",
    #                     'frequency': "1d",
    #                     'data_type': "numeric",
    #                     'source': "calculated",
    #                     'definition': f"Portfolio value factor for {portfolio.name}"
    #                 }
                    
    #                 portfolio_value_factor = self.market_data_service._create_or_get(entity_config
    #                 )
                    
    #                 if self.logger and portfolio_value_factor:
    #                     self.logger.info(f"✅ Portfolio value factor created: {portfolio_value_factor.name}")
                        
    #             except Exception as e:
    #                 if self.logger:
    #                     self.logger.warning(f"⚠️ Failed to create portfolio value factor: {e}")
            
    #         if self.logger:
    #             self.logger.info(f"✅ Portfolio registered: {portfolio.name} (ID: {portfolio.id})")
            
    #         return portfolio
            
    #     except Exception as e:
    #         if self.logger:
    #             self.logger.error(f"❌ Portfolio registration failed: {e}")
    #         return None

    def register_portfolio_with_config(
        self,
        portfolio_config: Optional[Dict[str, Any]] = None,
        name: str = None,
        initial_cash: float = None,
        portfolio_type: str = None,
    ) -> Optional[Portfolio]:
        """
        Register the main portfolio from config. Sub-portfolios and holdings are
        created lazily the first time set_holdings is called for each ticker.

        Returns:
            Main portfolio entity or None if registration failed
        """
        try:
            # Determine main portfolio parameters
            if portfolio_config:
                main_name = portfolio_config.get('name', name or 'Default_Portfolio')
                main_cash = portfolio_config.get('initial_cash', initial_cash or 100000.0)
                main_type = portfolio_config.get('portfolio_type', portfolio_type or 'BACKTEST')
                main_currency = portfolio_config.get('currency_code', 'USD')
                initial_cash_currency_code = portfolio_config.get('initial_cash_currency_code', main_currency)
            else:
                # Fallback to individual parameters
                main_name = name or 'Default_Portfolio'
                main_cash = initial_cash or 100000.0
                main_type = portfolio_type or 'BACKTEST'
                main_currency = 'USD'
                initial_cash_currency_code = main_currency

            # Convert initial_cash to portfolio currency when they differ.
            # CurrencyFactor for portfolio_currency stores: 1 portfolio_currency = X initial_cash_currency
            # so quantity_portfolio_currency = initial_cash / fx_rate.
            if initial_cash_currency_code != main_currency:
                fx_rate = self._get_currency_fx_rate(main_currency)
                if fx_rate:
                    original_cash = main_cash
                    main_cash = main_cash / fx_rate
                    if self.logger:
                        self.logger.info(
                            f"FX conversion: {original_cash} {initial_cash_currency_code} "
                            f"/ {fx_rate} = {main_cash:.4f} {main_currency}"
                        )
                else:
                    if self.logger:
                        self.logger.warning(
                            f"CurrencyFactor rate for {main_currency} not found; "
                            f"using initial_cash without conversion"
                        )
            
            # Create main portfolio
            main_portfolio = self.portfolio_repo._create_or_get(
                name=main_name,
                portfolio_type=main_type,
                initial_cash=main_cash,
                currency_code=main_currency
            )

            
            if not main_portfolio:
                if self.logger:
                    self.logger.error(f"❌ Failed to create main portfolio: {main_name}")
                return None
            
            self._current_portfolio_entity = main_portfolio
            # Create market_data_service on demand if it's None
            if self.market_data_service is None and self.entity_service:
                if self.logger:
                    self.logger.info("🔄 Creating MarketDataService on demand...")
                try:
                    from src.application.services.misbuffet.data.market_data_service import MarketDataService
                    self.market_data_service = MarketDataService(self.entity_service)
                    if self.logger:
                        self.logger.info("✅ MarketDataService created successfully on demand")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"❌ Failed to create MarketDataService on demand: {e}")
            
            if self.market_data_service is None:
                if self.logger:
                    self.logger.error("❌ Market data service is None - cannot create portfolio value factor")
                    self.logger.error("❌ This indicates UnifiedPortfolioManager was initialized without proper market_data_service")
            elif not hasattr(self.market_data_service, '_create_or_get'):
                if self.logger:
                    self.logger.error(f"❌ Market data service {type(self.market_data_service)} does not have _create_or_get method")
            else:
                try:
                    config = FACTOR_LIBRARY["portfolio_library"]["portfolio_value"]
                    if self.logger:
                        self.logger.info(f"🔄 Creating portfolio value factor with config: {config.get('factor_type', 'unknown')}")
                    portfolio_value_factor = self.market_data_service._create_or_get(config)
                    self.portfolio_value_factor = portfolio_value_factor
                    initial_portfolio_value = self.get_portfolio_value()
                    if self.logger and portfolio_value_factor:
                        self.logger.info(f"✅ Portfolio value factor created: {portfolio_value_factor.name}")
                    elif self.logger:
                        self.logger.warning("⚠️ Portfolio value factor creation returned None")
                        
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"❌ Error in get_or_create portfolio value factor portfolio_value: {e}")
                        import traceback
                        self.logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            
            if self.logger:
                self.logger.info(f"✅ Main portfolio created: {main_portfolio.name} (ID: {main_portfolio.id})")

            return main_portfolio
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Enhanced portfolio registration failed: {e}")
            return None

    # ---------------------------------------------------------------------------
    # Lazy asset pipeline — called from set_holdings on first trade for a ticker
    # ---------------------------------------------------------------------------

    def _ensure_asset_container(self, ticker: str, now: datetime) -> Optional[int]:
        """
        Idempotently set up the full sub-portfolio hierarchy for a CompanyShare ticker.

        Steps (all idempotent):
          1. Resolve the CompanyShareModel by symbol.
          2. Find or create a CompanySharePortfolio sub-portfolio.
          3. Link it to the main portfolio via CompanySharePortfolioPortfolioHolding.
          4. Create a CompanySharePortfolioHolding + Position for the ticker.
          5. Create a value factor for the sub-portfolio (if not already present).

        Returns the sub-portfolio id to use as portfolio_id in execute_trade,
        or None if the ticker is not a known CompanyShare.
        """
        from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel
        from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import (
            CompanySharePortfolioPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.holding.company_share_portfolio_holding import (
            CompanySharePortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.position import PositionModel

        session = self.portfolio_repo.session
        main_id = self._current_portfolio_entity.id

        # Step 1: resolve the share
        share = session.query(CompanyShareModel).filter(
            CompanyShareModel.symbol == ticker
        ).first()
        if not share:
            return None

        # Step 2 & 3: find or create the CompanySharePortfolio + its link to main portfolio
        link = (
            session.query(CompanySharePortfolioPortfolioHoldingModel)
            .filter_by(container_id=main_id)
            .first()
        )
        if link:
            sub_portfolio_id = link.asset_id
        else:
            sub_portfolio = self._create_company_share_sub_portfolio()
            if sub_portfolio is None:
                return None
            sub_portfolio_id = sub_portfolio.id

            # Position for the portfolio-portfolio link (quantity = 1, structural)
            pp_pos = PositionModel(
                portfolio_id=main_id,
                quantity=1,
                position_type='LONG',
            )
            session.add(pp_pos)
            session.flush()

            link = CompanySharePortfolioPortfolioHoldingModel(
                asset_id=sub_portfolio_id,
                portfolio_id=main_id,
                container_id=main_id,
                start_date=now,
                position_id=pp_pos.id,
            )
            session.add(link)
            session.commit()

            if self.logger:
                self.logger.info(
                    f"Created CompanySharePortfolio '{sub_portfolio.name}' "
                    f"(id={sub_portfolio_id}) linked to main portfolio {main_id}"
                )

        # Step 4: ensure per-ticker holding
        existing = (
            session.query(CompanySharePortfolioHoldingModel)
            .filter_by(company_share_portfolio_id=sub_portfolio_id, asset_id=share.id)
            .first()
        )
        if not existing:
            pos = PositionModel(
                portfolio_id=sub_portfolio_id,
                quantity=0,
                position_type='LONG',
            )
            session.add(pos)
            session.flush()

            holding = CompanySharePortfolioHoldingModel(
                asset_id=share.id,
                company_share_portfolio_id=sub_portfolio_id,
                container_id=sub_portfolio_id,
                start_date=now,
                position_id=pos.id,
            )
            session.add(holding)
            session.commit()

            if self.logger:
                self.logger.info(
                    f"Created CompanySharePortfolioHolding: {ticker} "
                    f"(asset_id={share.id}) → sub-portfolio {sub_portfolio_id}"
                )

        return sub_portfolio_id

    def _find_existing_container(self, ticker: str) -> Optional[int]:
        """
        Return the sub-portfolio id for a ticker that already has a holding.
        Used for liquidation orders where the structure was set up in a prior call.
        """
        from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel
        from src.infrastructure.models.finance.holding.company_share_portfolio_holding import (
            CompanySharePortfolioHoldingModel,
        )

        session = self.portfolio_repo.session
        share = session.query(CompanyShareModel).filter(
            CompanyShareModel.symbol == ticker
        ).first()
        if not share:
            return None
        holding = (
            session.query(CompanySharePortfolioHoldingModel)
            .filter_by(asset_id=share.id)
            .first()
        )
        return holding.company_share_portfolio_id if holding else None

    def _create_company_share_sub_portfolio(self):
        """Create (or retrieve) a CompanySharePortfolio sub-portfolio for this main portfolio."""
        try:
            from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
            repo = self.repository_factory.get_local_repository(CompanySharePortfolio)
            main = self._current_portfolio_entity
            sub_name = f"{main.name}_CS"
            return repo._create_or_get(
                name=sub_name,
                currency_code=getattr(main, 'currency_code', 'USD'),
                initial_cash=0.0,
                portfolio_type=getattr(main, 'portfolio_type', 'BACKTEST'),
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"_create_company_share_sub_portfolio failed: {e}")
            return None

    def get_current_portfolio(self) -> Optional[Portfolio]:
        """Get the current portfolio entity."""
        return self._current_portfolio_entity

    def register_order(self, order_ticket) -> Optional[Order]:
        """
        Register an order from QCAlgorithm order ticket.
        Uses enhanced _create_or_get method with cascading relationships:
        - Creates inactive holding for the order
        - If order is executed (FILLED), creates associated transaction
        
        Args:
            order_ticket: QCAlgorithm OrderTicket
            
        Returns:
            Domain Order entity or None if registration failed
        """
        if not self._current_portfolio_entity:
            if self.logger:
                self.logger.warning("Cannot register order - no portfolio registered")
            return None
            
        try:
            # Extract parameters for enhanced _create_or_get method
            order_params = self._extract_order_params(order_ticket)
            
            # Use enhanced repository method with cascading relationships
            persisted_order = self.order_repo._create_or_get(
                external_order_id=str(order_ticket.order_id),
                portfolio_id=self._current_portfolio_entity.id,
                **order_params
            )
            
            # Create order quantity and price factors using market data service
            if persisted_order and self.market_data_service and hasattr(self.market_data_service, '_create_or_get'):
                try:
                    symbol = order_params.get('symbol', 'UNKNOWN')
                    
                    # Create order quantity factor
                    # Configure entity_config for MarketDataService._create_or_get method
                    entity_config = {
                        'entity_class': Factor,
                        'entity_symbol': f"order_quantity_{symbol}_{persisted_order.id}",
                        'factor_type': "company_share_order_quantity_factor",
                        'group': "quantity",
                        'subgroup': "order",
                        'frequency': "1d",
                        'data_type': "numeric",
                        'source': "order",
                        'definition': f"Order quantity factor for {symbol}"
                    }
                    
                    order_quantity_factor = self.market_data_service._create_or_get(entity_config)
                    
                    # Create order price factor
                    # Configure entity_config for MarketDataService._create_or_get method
                    entity_config = {
                        'entity_class': Factor,
                        'entity_symbol': f"order_price_{symbol}_{persisted_order.id}",
                        'factor_type': "company_share_order_price_factor",
                        'group': "price",
                        'subgroup': "order",
                        'frequency': "1d",
                        'data_type': "numeric",
                        'source': "order",
                        'definition': f"Order price factor for {symbol}"
                    }
                    
                    order_price_factor = self.market_data_service._create_or_get(entity_config)
                    
                    if self.logger:
                        if order_quantity_factor:
                            self.logger.info(f"✅ Order quantity factor created: {order_quantity_factor.name}")
                        if order_price_factor:
                            self.logger.info(f"✅ Order price factor created: {order_price_factor.name}")
                            
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"⚠️ Failed to create order factors: {e}")
            
            if persisted_order:
                # Store mapping for future reference
                self._order_ticket_mapping[order_ticket.order_id] = persisted_order.id
                
                if self.logger:
                    self.logger.info(f"✅ Order registered with cascading relationships: {persisted_order.id}")
                
                return persisted_order
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Order registration failed: {e}")
            return None

    def record_transaction(self, order_event) -> Optional[Transaction]:
        """
        Record a transaction when an order is filled.
        Uses enhanced _create_or_get method with cascading relationships:
        - Updates holding status (activate/deactivate) based on transaction
        - Creates/gets account associated with transaction
        
        Args:
            order_event: QCAlgorithm OrderEvent
            
        Returns:
            Domain Transaction entity or None if recording failed
        """
        if not self._current_portfolio_entity:
            return None
            
        try:
            # Find corresponding order
            domain_order_id = self._order_ticket_mapping.get(order_event.order_id)
            if not domain_order_id:
                if self.logger:
                    self.logger.warning(f"No domain order found for QC order {order_event.order_id}")
                return None
            
            # Extract transaction parameters
            transaction_params = self._extract_transaction_params(order_event, domain_order_id)
            
            # Generate unique transaction ID
            import uuid
            transaction_id = f"TXN_{order_event.order_id}_{uuid.uuid4().hex[:8]}"
            
            # Use enhanced repository method with cascading relationships
            persisted_transaction = self.transaction_repo._create_or_get(
                transaction_id=transaction_id,
                order_id=int(domain_order_id),
                portfolio_id=self._current_portfolio_entity.id,
                **transaction_params
            )
            
            # Create transaction value factor using market data service
            if persisted_transaction and self.market_data_service and hasattr(self.market_data_service, '_create_or_get'):
                try:
                    symbol = transaction_params.get('symbol', 'UNKNOWN')
                    
                    # Create transaction value factor
                    # Configure entity_config for MarketDataService._create_or_get method
                    entity_config = {
                        'entity_class': Factor,
                        'entity_symbol': f"transaction_value_{symbol}_{persisted_transaction.id}",
                        'factor_type': "company_share_transaction_value_factor",
                        'group': "value",
                        'subgroup': "transaction",
                        'frequency': "1d",
                        'data_type': "numeric",
                        'source': "calculated",
                        'definition': f"Transaction value factor for {symbol}"
                    }
                    
                    transaction_value_factor = self.market_data_service._create_or_get(entity_config)
                    
                    if self.logger and transaction_value_factor:
                        self.logger.info(f"✅ Transaction value factor created: {transaction_value_factor.name}")
                        
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"⚠️ Failed to create transaction value factor: {e}")
            
            if self.logger and persisted_transaction:
                self.logger.info(f"✅ Transaction recorded with cascading relationships: {persisted_transaction.id}")
            
            return persisted_transaction
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Transaction recording failed: {e}")
            return None

    def get_portfolio_value(self,backtest_date=None) -> float:
        """
        Return current total portfolio value as a float and persist a pre-trade FactorValue snapshot.

        Flow (Option A — algorithm-first):
          1. Read total_portfolio_value from the QC algorithm (authoritative).
          2. Source active positions via get_active_positions() as factor dependencies.
          3. Compute portfolio_value_factor.calculate(dependencies) from those values.
          4. Persist via the FactorValue resolution service (once per algorithm bar).
          5. Return the authoritative float from step 1.
        """
        total: float = 0.0

        if self._algorithm is not None:
            try:
                total = float(self._algorithm.portfolio.total_portfolio_value)
            except Exception:
                pass

        # Persist pre-trade snapshot — at most once per algorithm bar, and use the
        # computed value as authoritative total when the QC portfolio reports 0.
        if self._current_portfolio_entity is not None:
            
            if self._algorithm and hasattr(self._algorithm, 'time') and isinstance(self._algorithm.time, datetime) and self._algorithm.time < datetime.strptime(self._algorithm.config["backtest_end"],"%Y-%m-%d %H:%M:%S"):
                current_time = self._algorithm.time
            elif backtest_date is not None:
                current_time = backtest_date
           
            elif self._algorithm and hasattr(self._algorithm, 'config') and "backtest_start" in self._algorithm.config:
                current_time = self._algorithm.config["backtest_start"]
            
            else:
                current_time = datetime.now()

            if self._last_pv_snapshot_time != current_time:
                try:
                    # Recursively value the full holding tree (main portfolio →
                    # sub-portfolios → leaf assets).  Prices come from DB
                    # FactorValues only — no market_data_service fallback here,
                    # because that path calls factor_value_resolution_service which
                    # would re-enter this call stack and cause infinite recursion.
                    # Prices are written to DB by the market-data pipeline before
                    # on_data fires, so DB-only lookup is sufficient.
                    from src.application.services.data.entities.factor.finance.portfolio_service import PortfolioService
                    portfolio_svc = PortfolioService(
                        self.portfolio_repo.session,
                        self.repository_factory,
                        market_data_service=None,
                    )
                    computed = float(portfolio_svc.calculate_value(
                        self._current_portfolio_entity.id,
                        as_of_date=current_time,
                    ))
                    # Use the computed tree-traversal value when the QC portfolio
                    # object reports zero (happens in custom backtests that don't
                    # populate the in-memory QC portfolio object).
                    if total == 0.0 and computed > 0.0:
                        total = computed
                    # calculate_value already persisted holding_value and
                    # portfolio_value FactorValue rows; no resolve_factor_value
                    # call needed (that path triggers _resolve_dynamic_dependencies
                    # which recurses unboundedly through related entities).
                    self._last_pv_snapshot_time = current_time
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"get_portfolio_value: FactorValue snapshot failed: {e}")

        if total == 0.0 and self._current_portfolio_entity is not None:
            try:
                total = float(getattr(self._current_portfolio_entity, 'initial_cash', 0) or 0)
            except Exception:
                pass

        return total

    def get_active_positions(self) -> List[Dict[str, Any]]:
        """
        Get all active positions using domain entities.
        
        Returns:
            List of position data dictionaries
        """
        if not self._current_portfolio_entity:
            return []
            
        try:
            holdings = self.holding_repo.get_by_portfolio_id(self._current_portfolio_entity.id)
            positions = []
            
            for holding in holdings:
                if holding.is_active() and holding.position.quantity != 0:
                    position_data = {
                        'holding_id': holding.id,
                        'asset_id': holding.asset.id,
                        'symbol': self._get_asset_symbol(holding.asset),
                        'quantity': holding.position.quantity,
                        'position_type': holding.position.position_type.value,
                        'market_value': float(self._calculate_holding_market_value(holding)),
                        'start_date': holding.start_date,
                        'is_active': holding.is_active()
                    }
                    positions.append(position_data)
            
            return positions
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Active positions retrieval failed: {e}")
            return []

    def get_orders_summary(self) -> Dict[str, Any]:
        """
        Get summary of orders for the current portfolio.
        
        Returns:
            Dictionary with order statistics
        """
        if not self._current_portfolio_entity:
            return {}
            
        try:
            # Get all orders for this portfolio
            orders = self.order_repo.get_by_portfolio_id(self._current_portfolio_entity.id)
            
            summary = {
                'total_orders': len(orders),
                'pending_orders': len([o for o in orders if o.status == OrderStatus.PENDING]),
                'filled_orders': len([o for o in orders if o.status == OrderStatus.FILLED]),
                'cancelled_orders': len([o for o in orders if o.status == OrderStatus.CANCELLED]),
                'buy_orders': len([o for o in orders if o.side == OrderSide.BUY]),
                'sell_orders': len([o for o in orders if o.side == OrderSide.SELL])
            }
            
            return summary
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Orders summary failed: {e}")
            return {}

    def get_transactions_summary(self) -> Dict[str, Any]:
        """
        Get summary of transactions for the current portfolio.
        
        Returns:
            Dictionary with transaction statistics
        """
        if not self._current_portfolio_entity:
            return {}
            
        try:
            # Get all transactions for this portfolio
            transactions = self.transaction_repo.get_by_portfolio_id(self._current_portfolio_entity.id)
            
            summary = {
                'total_transactions': len(transactions),
                'executed_transactions': len([t for t in transactions if t.status == TransactionStatus.EXECUTED]),
                'pending_transactions': len([t for t in transactions if t.status == TransactionStatus.PENDING]),
                'market_orders': len([t for t in transactions if t.transaction_type == TransactionType.MARKET_ORDER]),
                'limit_orders': len([t for t in transactions if t.transaction_type == TransactionType.LIMIT_ORDER])
            }
            
            return summary
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Transactions summary failed: {e}")
            return {}

    # Private helper methods

    def _extract_order_params(self, ticket) -> Dict[str, Any]:
        """Extract order parameters from QCAlgorithm OrderTicket for enhanced _create_or_get."""
        return {
            'order_type': self._map_order_type(getattr(ticket, 'order_type', 'MARKET')),
            'side': OrderSide.BUY if ticket.quantity > 0 else OrderSide.SELL,
            'quantity': abs(ticket.quantity),
            'created_at': getattr(ticket, 'time', datetime.now()),
            'status': self._map_order_status(getattr(ticket, 'status', 'PENDING')),
            'account_id': self._get_account_id(),
            'symbol': getattr(ticket, 'symbol', 'UNKNOWN'),
            'price': getattr(ticket, 'limit_price', None),
            'stop_price': getattr(ticket, 'stop_price', None),
            'filled_quantity': getattr(ticket, 'quantity_filled', 0.0),
            'average_fill_price': getattr(ticket, 'average_fill_price', None),
            'time_in_force': getattr(ticket, 'time_in_force', None)
        }

    def _extract_transaction_params(self, order_event, domain_order_id: str) -> Dict[str, Any]:
        """Extract transaction parameters from QCAlgorithm OrderEvent for enhanced _create_or_get."""
        event_time = getattr(order_event, 'time', datetime.now())
        
        return {
            'date': event_time,
            'transaction_type': TransactionType.MARKET_ORDER,  # Could be enhanced based on order type
            'account_id': self._get_account_id(),
            'trade_date': event_time.date(),
            'value_date': event_time.date(),
            'settlement_date': event_time.date(),
            'status': TransactionStatus.EXECUTED,
            'spread': 0.0,
            'currency_id': 1,  # USD
            'exchange_id': 1,  # Default exchange
            'external_transaction_id': getattr(order_event, 'transaction_id', None),
            'side': 'BUY' if getattr(order_event, 'quantity', 0) > 0 else 'SELL',
            'quantity': abs(getattr(order_event, 'quantity', 0)),
            'symbol': getattr(order_event, 'symbol', 'UNKNOWN')
        }

    def get_enhanced_holdings(self, include_inactive: bool = False) -> List[Holding]:
        """Get enhanced holdings with cascading relationships already established."""
        if not self._current_portfolio_entity:
            return []
            
        try:
            holdings = self.holding_repo.get_by_portfolio_id(self._current_portfolio_entity.id)
            
            if include_inactive:
                return holdings
            else:
                return [h for h in holdings if h.is_active()]
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Enhanced holdings retrieval failed: {e}")
            return []

    def _calculate_holding_market_value(self, holding: Holding) -> Decimal:
        """Calculate market value of a holding."""
        try:
            # Simplified calculation - would use real market prices
            quantity = holding.position.quantity
            # Would get current market price from market data service
            estimated_price = Decimal('100.0')  # Mock price
            
            return Decimal(str(quantity)) * estimated_price
            
        except Exception:
            return Decimal('0')

    def _has_budget_for_trade(self, order_qty: int, price: float, current_qty: int) -> bool:
        """
        Return True if the portfolio has sufficient resources to execute the trade.

        BUY  (order_qty > 0): available cash must cover the full order cost.
        SELL (order_qty < 0): current position must be >= the sell quantity
                              (no naked short selling in this implementation).
        """
        if order_qty > 0:
            required_cash = order_qty * price
            available_cash = float(self._get_cash_balance())
            if available_cash < required_cash:
                if self.logger:
                    self.logger.warning(
                        f"Budget check failed — need ${required_cash:,.2f}, "
                        f"available cash ${available_cash:,.2f}"
                    )
                return False
        elif order_qty < 0:
            sell_qty = abs(order_qty)
            if current_qty < sell_qty:
                if self.logger:
                    self.logger.warning(
                        f"Budget check failed — cannot sell {sell_qty} shares, "
                        f"only {current_qty} in position"
                    )
                return False
        return True

    def _get_cash_balance(self) -> Decimal:
        """
        Return the current available cash balance as a Decimal.

        Sources in priority order:
        1. QC algorithm's in-memory portfolio cash — fast and authoritative
           during backtesting/paper trading.
        2. Currency holding in the DB — the cash holding created at portfolio
           init (currency asset, position.quantity = initial_cash).
        3. Falls back to 0 so callers always receive a valid number.
        """
        # 1. Algorithm in-memory cash (most accurate during simulation)
        if self._algorithm is not None:
            try:
                cash = float(self._algorithm.portfolio.cash)
                if cash >= 0:
                    return Decimal(str(cash))
            except Exception:
                pass

        # 2. DB cash via CurrencyPortfolio sub-portfolio tree
        try:
            if self._current_portfolio_entity:
                from src.infrastructure.models.finance.holding.currency_portfolio_portfolio_holding import (
                    CurrencyPortfolioPortfolioHoldingModel,
                )
                from src.infrastructure.models.finance.holding.currency_portfolio_holding import (
                    CurrencyPortfolioHoldingModel,
                )
                from src.infrastructure.models.finance.position import PositionModel

                session = self.portfolio_repo.session
                main_id = self._current_portfolio_entity.id

                cp_link = session.query(CurrencyPortfolioPortfolioHoldingModel).filter_by(
                    container_id=main_id
                ).first()
                if cp_link:
                    cash_holding = session.query(CurrencyPortfolioHoldingModel).filter_by(
                        currency_portfolio_id=cp_link.asset_id
                    ).first()
                    if cash_holding and cash_holding.position_id:
                        pos = session.query(PositionModel).filter_by(
                            id=cash_holding.position_id
                        ).first()
                        if pos is not None and pos.quantity is not None:
                            return Decimal(str(pos.quantity))
        except Exception:
            pass

        return Decimal('0')

    def _get_asset_symbol(self, asset) -> str:
        """Return the ticker symbol for an asset, falling back to a DB lookup when the
        in-memory placeholder has symbol=None (as created by HoldingMapper)."""
        symbol = getattr(asset, 'symbol', None)
        if symbol:
            return symbol
        asset_id = getattr(asset, 'id', None)
        if asset_id:
            try:
                from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
                session = self.portfolio_repo.session
                fa = session.query(FinancialAssetModel).filter(
                    FinancialAssetModel.id == asset_id
                ).first()
                if fa and fa.symbol:
                    return fa.symbol
            except Exception:
                pass
        return 'UNKNOWN'

    def _get_or_create_holding_for_symbol(self, symbol) -> int:
        """Get or create holding for a symbol."""
        # Simplified implementation
        return 1

    def _get_next_order_id(self) -> int:
        """Get next available order ID."""
        return len(self._order_ticket_mapping) + 1

    def _get_next_transaction_id(self) -> int:
        """Get next available transaction ID."""
        # Simplified implementation
        return 1

    def _get_account_id(self) -> str:
        """Get account ID."""
        return "SPX_TRADING_ACCOUNT"

    def _map_order_type(self, order_type_str: str) -> OrderType:
        """Map QC order type to domain OrderType."""
        mapping = {
            'MARKET': OrderType.MARKET,
            'LIMIT': OrderType.LIMIT,
            'STOP': OrderType.STOP,
            'STOP_LIMIT': OrderType.STOP_LIMIT
        }
        return mapping.get(order_type_str.upper(), OrderType.MARKET)

    def _map_order_status(self, status_str: str) -> OrderStatus:
        """Map QC order status to domain OrderStatus."""
        mapping = {
            'PENDING': OrderStatus.PENDING,
            'SUBMITTED': OrderStatus.SUBMITTED,
            'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
            'FILLED': OrderStatus.FILLED,
            'CANCELLED': OrderStatus.CANCELLED,
            'REJECTED': OrderStatus.REJECTED
        }
        return mapping.get(status_str.upper(), OrderStatus.PENDING)
    
    def _get_currency_fx_rate(self, portfolio_currency_code: str) -> Optional[float]:
        """
        Return the latest CurrencyFactor price for *portfolio_currency_code*.

        CurrencyFactor stores the price as "1 portfolio_currency = X base_currency"
        (e.g. 1 USD = 1.3 CAD).  Dividing initial_cash (in the base/input currency)
        by this rate converts it to the portfolio currency.

        Returns None when no FactorValue is found so the caller can fall back
        gracefully without crashing portfolio creation.
        """
        try:
            from src.infrastructure.models.factor.factor import FactorModel
            from src.infrastructure.models.factor.factor_value import FactorValueModel

            session = self.repository_factory.session

            # Look up the CurrencyFactor row (discriminator entity_type='currency')
            currency_factor_model = session.query(FactorModel).filter(
                FactorModel.name == portfolio_currency_code,
                FactorModel.entity_type == 'currency',
            ).first()

            if not currency_factor_model:
                if self.logger:
                    self.logger.warning(
                        f"_get_currency_fx_rate: no CurrencyFactor found for '{portfolio_currency_code}'"
                    )
                return None

            # Resolve the Currency financial-asset entity to get its id
            currency_repo = self.repository_factory.currency_local_repo
            if not currency_repo:
                if self.logger:
                    self.logger.warning(
                        "_get_currency_fx_rate: currency_local_repo not available"
                    )
                return None

            currency_entity = currency_repo.get_or_create(iso_code=portfolio_currency_code)
            if not currency_entity:
                if self.logger:
                    self.logger.warning(
                        f"_get_currency_fx_rate: currency entity for '{portfolio_currency_code}' not found"
                    )
                return None

            currency_id = getattr(currency_entity, 'id', None) or getattr(currency_entity, 'asset_id', None)
            if not currency_id:
                if self.logger:
                    self.logger.warning(
                        f"_get_currency_fx_rate: currency '{portfolio_currency_code}' has no id"
                    )
                return None

            # Fetch the most recent FactorValue for this factor / entity pair
            latest_fv = (
                session.query(FactorValueModel)
                .filter(
                    FactorValueModel.factor_id == currency_factor_model.id,
                    FactorValueModel.entity_id == currency_id,
                )
                .order_by(FactorValueModel.date.desc())
                .first()
            )

            if not latest_fv or latest_fv.value is None:
                if self.logger:
                    self.logger.warning(
                        f"_get_currency_fx_rate: no FactorValue found for '{portfolio_currency_code}'"
                    )
                return None

            rate = float(latest_fv.value)
            if rate == 0:
                if self.logger:
                    self.logger.warning(
                        f"_get_currency_fx_rate: FactorValue for '{portfolio_currency_code}' is 0"
                    )
                return None

            return rate

        except Exception as e:
            if self.logger:
                self.logger.error(f"_get_currency_fx_rate failed for '{portfolio_currency_code}': {e}")
            return None

    def demonstrate_cascading_workflow(self, symbol: str, quantity: float) -> Dict[str, Any]:
        """
        Demonstrate the complete cascading workflow from order to position.
        This method shows how the enhanced repositories work together.
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            
        Returns:
            Dictionary showing the cascading creation process
        """
        if not self._current_portfolio_entity:
            return {'error': 'No portfolio registered'}
            
        workflow_log = []
        
        try:
            # Step 1: Create order (creates inactive holding)
            workflow_log.append("Step 1: Creating order with cascading relationships...")
            order = self.create_order_with_cascading_relationships(symbol, quantity)
            if not order:
                return {'error': 'Failed to create order', 'workflow_log': workflow_log}
            
            workflow_log.append(f"✅ Created order {order.id} for {symbol}")
            
            # Step 2: Simulate order execution by creating transaction
            workflow_log.append("Step 2: Creating transaction (simulating order fill)...")
            transaction = self.create_transaction_with_cascading_relationships(
                order_id=order.id,
                symbol=symbol,
                quantity=quantity,
                side='BUY' if quantity > 0 else 'SELL'
            )
            
            if transaction:
                workflow_log.append(f"✅ Created transaction {transaction.id} (holding updated)")
            
            # Step 3: Get the resulting holding with position
            workflow_log.append("Step 3: Retrieving enhanced holding with position...")
            holdings = self.get_enhanced_holdings(include_inactive=True)
            relevant_holding = next((h for h in holdings if hasattr(h, 'asset') and 
                                   self._get_asset_symbol(h.asset) == symbol), None)
            
            if relevant_holding:
                workflow_log.append(f"✅ Found holding {relevant_holding.id} with position")
            
            return {
                'success': True,
                'workflow_log': workflow_log,
                'created_objects': {
                    'order_id': order.id if order else None,
                    'transaction_id': transaction.id if transaction else None,
                    'holding_id': relevant_holding.id if relevant_holding else None
                },
                'cascading_effects': [
                    'Order created inactive holding',
                    'Transaction activated holding and updated quantities',
                    'Holding has associated position and asset dependencies'
                ]
            }
            
        except Exception as e:
            workflow_log.append(f"❌ Error in cascading workflow: {e}")
            return {'error': str(e), 'workflow_log': workflow_log}

    def set_algorithm(self, algorithm) -> None:
        """Inject the owning QCAlgorithm after construction (avoids circular init)."""
        self._algorithm = algorithm

    def set_holdings(
        self,
        target_weights: Dict[str, float],
        data=None,
        tag: str = "",
    ) -> Dict[str, bool]:
        """
        Rebalance the portfolio to the given target weights.

        SELLs are executed before BUYs so that proceeds from trimmed positions
        are available as cash for new or enlarged positions.  Any ticker
        currently held but absent from target_weights is treated as target
        weight = 0 (full liquidation).

        Args:
            target_weights: {ticker: target_weight (0.0 – 1.0)}
            data:           current Slice from on_data (for price resolution)
            tag:            optional order tag

        Returns:
            {ticker: True/False} for every ticker where an order was attempted.
        """
        results: Dict[str, bool] = {}
        
            
        if data.time:
            current_time = data.time
        elif hasattr(self._algorithm, "time"):
            current_time = self._algorithm.time
        else:
            current_time = datetime.now()
        if not self._current_portfolio_entity:
            if self.logger:
                self.logger.warning("set_holdings: no portfolio registered")
            return results

        if not self._algorithm:
            if self.logger:
                self.logger.warning("set_holdings: algorithm not injected, cannot submit orders")
            return results

        # Portfolio value snapshot (at most once per bar via get_portfolio_value guard)
        try:
            pv = self.get_portfolio_value(backtest_date=current_time)
            portfolio_value = float(getattr(pv, "value", pv))
        except Exception:
            portfolio_value = 0.0

        if portfolio_value <= 0:
            if self.logger:
                self.logger.warning(f"set_holdings: invalid portfolio value {portfolio_value}")
            return results

        

        # Evaluate all explicitly targeted tickers + all currently held tickers
        main_id = self._current_portfolio_entity.id

        # Lazy pipeline: ensure sub-portfolio + holding structures exist for each
        # new ticker before we start computing order quantities.
        ticker_container: Dict[str, int] = {}
        for ticker in target_weights:
            cid = self._ensure_asset_container(ticker, current_time)
            ticker_container[ticker] = cid if cid else main_id

        all_tickers = set(target_weights.keys()) | self._get_all_held_tickers()

        # For liquidation tickers (held but not targeted), look up their existing container.
        for ticker in all_tickers - set(target_weights.keys()):
            if ticker not in ticker_container:
                cid = self._find_existing_container(ticker)
                ticker_container[ticker] = cid if cid else main_id

        sells: List[tuple] = []  # (ticker, order_qty, price, current_qty)
        buys:  List[tuple] = []

        for ticker in all_tickers:
            target_pct = target_weights.get(ticker, 0.0)

            price = self._price_from_slice(ticker, data)
            if not price or price <= 0:
                if hasattr(self._algorithm, "_resolve_asset_price"):
                    price = self._algorithm._resolve_asset_price(ticker)

            if not price or price <= 0:
                if self.logger:
                    self.logger.warning(f"set_holdings: no price for {ticker}, skipping")
                results[ticker] = False
                continue

            current_qty = self._get_current_position_qty(ticker)
            target_qty  = int(portfolio_value * target_pct / price)
            order_qty   = target_qty - current_qty

            if order_qty == 0:
                continue

            entry = (ticker, order_qty, price, current_qty)
            if order_qty < 0:
                sells.append(entry)
            else:
                buys.append(entry)

        # Execute sells first to free up cash / reduce exposure
        for ticker, order_qty, price, current_qty in sells:
            if not self._has_budget_for_trade(order_qty, price, current_qty):
                if self.logger:
                    self.logger.warning(
                        f"set_holdings: sell check failed for {ticker} qty={order_qty:+d}"
                    )
                results[ticker] = False
                continue
            results[ticker] = self._trade_manager.execute_trade(
                ticker=ticker,
                order_qty=order_qty,
                price=price,
                portfolio_id=ticker_container.get(ticker, main_id),
                current_time=current_time,
                submit_order_fn=self._algorithm.market_order,
                tag=tag,
            )

        # Execute buys after sells have freed up liquidity
        for ticker, order_qty, price, current_qty in buys:
            if not self._has_budget_for_trade(order_qty, price, current_qty):
                if self.logger:
                    self.logger.warning(
                        f"set_holdings: buy check failed for {ticker} "
                        f"qty={order_qty:+d} @ {price:.2f}"
                    )
                results[ticker] = False
                continue
            results[ticker] = self._trade_manager.execute_trade(
                ticker=ticker,
                order_qty=order_qty,
                price=price,
                portfolio_id=ticker_container.get(ticker, main_id),
                current_time=current_time,
                submit_order_fn=self._algorithm.market_order,
                tag=tag,
            )

        return results

    def _get_all_held_tickers(self) -> set:
        """
        Return all non-currency tickers with non-zero positions across the full
        portfolio tree (direct holdings + sub-portfolios).
        """
        if not self._current_portfolio_entity:
            return set()
        return self._tickers_in_container(self._current_portfolio_entity.id)

    def _tickers_in_container(self, container_id: int) -> set:
        """
        Collect all tradeable (non-currency) tickers in a portfolio container,
        recursing into CompanySharePortfolio sub-portfolios.

        Portfolio tree structure:
          Portfolio (main)
            ├─ PortfolioHolding          → asset is a FinancialAsset (direct)
            └─ CompanySharePortfolioPortfolioHolding
                 └─ asset is a CompanySharePortfolio (sub-portfolio)
                      └─ its own PortfolioHoldings → FinancialAssets
        """
        try:
            from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
            from src.infrastructure.models.finance.holding.holding import HoldingModel
            from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import CompanySharePortfolioPortfolioHoldingModel
            from src.infrastructure.models.finance.position import PositionModel

            session = self.portfolio_repo.session
            tickers: set = set()

            # Direct financial-asset holdings with non-zero positions
            rows = (
                session.query(FinancialAssetModel.symbol)
                .join(HoldingModel, HoldingModel.asset_id == FinancialAssetModel.id)
                .join(PositionModel, PositionModel.id == HoldingModel.position_id)
                .filter(
                    HoldingModel.container_id == container_id,
                    PositionModel.quantity != 0,
                    FinancialAssetModel.asset_type != 'currency',
                )
                .all()
            )
            tickers.update(symbol for (symbol,) in rows if symbol)

            # Sub-portfolio holdings — recurse one level per sub-portfolio
            sub_holdings = session.query(CompanySharePortfolioPortfolioHoldingModel).filter(
                CompanySharePortfolioPortfolioHoldingModel.container_id == container_id
            ).all()
            for sh in sub_holdings:
                tickers.update(self._tickers_in_container(sh.asset_id))

            return tickers
        except Exception:
            return set()

    def _price_from_slice(self, ticker: str, data) -> Optional[float]:
        """
        Extract the close price for `ticker` from a Slice object.

        data.bars keys are Symbol objects whose `.value` attribute holds the
        ticker string (e.g. 'AAPL').  Returns None when data is absent or the
        ticker has no bar in this slice.
        """
        if data is None or not hasattr(data, "bars"):
            return None
        ticker_upper = ticker.upper()
        for symbol, bar in data.bars.items():
            sym_value = getattr(symbol, "value", str(symbol)).upper()
            if sym_value == ticker_upper:
                close = getattr(bar, "close", None)
                if close is not None:
                    return float(close)
        return None

    def _get_current_position_qty(self, ticker: str) -> int:
        """
        Return the summed quantity of `ticker` across the full portfolio tree.
        Delegates to _qty_in_container which recurses into sub-portfolios.
        """
        if not self._current_portfolio_entity:
            return 0
        return self._qty_in_container(ticker, self._current_portfolio_entity.id)

    def _qty_in_container(self, ticker: str, container_id: int) -> int:
        """
        Sum the quantity of `ticker` held in `container_id`, recursing into
        any CompanySharePortfolio sub-portfolios found there.

        Portfolio tree navigation:
          container_id
            ├─ HoldingModel(asset_id → FinancialAsset symbol=ticker) → Position.quantity
            └─ CompanySharePortfolioPortfolioHoldingModel(container_id)
                 asset_id = sub-portfolio id → recurse with that id as container_id
        """
        try:
            from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
            from src.infrastructure.models.finance.holding.holding import HoldingModel
            from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import CompanySharePortfolioPortfolioHoldingModel
            from src.infrastructure.models.finance.position import PositionModel

            session = self.portfolio_repo.session
            total = 0

            # Direct financial-asset holding in this container
            asset = session.query(FinancialAssetModel).filter(
                FinancialAssetModel.symbol == ticker
            ).first()
            if asset:
                holding = session.query(HoldingModel).filter(
                    HoldingModel.container_id == container_id,
                    HoldingModel.asset_id == asset.id,
                ).first()
                if holding and holding.position_id:
                    pos = session.query(PositionModel).filter(
                        PositionModel.id == holding.position_id
                    ).first()
                    if pos:
                        total += int(pos.quantity)

            # Recurse into sub-portfolio holdings
            sub_holdings = session.query(CompanySharePortfolioPortfolioHoldingModel).filter(
                CompanySharePortfolioPortfolioHoldingModel.container_id == container_id
            ).all()
            for sh in sub_holdings:
                total += self._qty_in_container(ticker, sh.asset_id)

            return total

        except Exception:
            return 0

    def update_holding_position(self, ticker: str, new_quantity: float, fill_price: float) -> bool:
        """
        Upsert the position for `ticker` to `new_quantity` shares at `fill_price`.

        Called after a simulated fill so the domain Position reflects the new quantity.
        Creates the position row if it doesn't exist yet.
        """
        if not self._current_portfolio_entity:
            return False
        try:
            portfolio_id = self._current_portfolio_entity.id
            existing = None
            try:
                existing = self.position_repo.get_by_portfolio_and_symbol(portfolio_id, ticker)
            except Exception:
                pass

            if existing and getattr(existing, 'id', None):
                self.position_repo.update_quantity(
                    existing.id, float(new_quantity), float(fill_price)
                )
            else:
                self.position_repo._create_or_get(
                    portfolio_id=portfolio_id,
                    symbol=ticker,
                    quantity=new_quantity,
                    average_cost=fill_price,
                    current_price=fill_price,
                )
            if self.logger:
                self.logger.info(
                    f"✅ Position for {ticker} updated to {new_quantity} shares @ ${fill_price:.2f}"
                )
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ update_holding_position failed for {ticker}: {e}")
            return False

    def get_unified_state(self) -> Dict[str, Any]:
        """
        Get complete unified portfolio state.
        
        Returns:
            Comprehensive state dictionary using domain entities
        """
        if not self._current_portfolio_entity:
            return {'error': 'No portfolio registered'}
            
        try:
            return {
                'portfolio': {
                    'id': self._current_portfolio_entity.id,
                    'name': self._current_portfolio_entity.name,
                    'start_date': self._current_portfolio_entity.start_date.isoformat(),
                    'end_date': self._current_portfolio_entity.end_date.isoformat() if self._current_portfolio_entity.end_date else None
                },
                'portfolio_value': float(self.get_portfolio_value()),
                'cash_balance': float(self._get_cash_balance()),
                'active_positions': self.get_active_positions(),
                'orders_summary': self.get_orders_summary(),
                'transactions_summary': self.get_transactions_summary(),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Unified state retrieval failed: {e}")
            return {'error': str(e)}