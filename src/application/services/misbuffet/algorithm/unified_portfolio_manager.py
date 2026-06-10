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

    def register_portfolio(
        self, 
        name: str, 
        initial_cash: float = 100000.0, 
        portfolio_type: str = "BACKTEST"
    ) -> Optional[Portfolio]:
        """
        Register or retrieve a portfolio entity (legacy method).
        
        Args:
            name: Portfolio name
            initial_cash: Initial cash amount
            portfolio_type: Type of portfolio
            
        Returns:
            Portfolio entity or None if registration failed
        """
        try:
            # Use standardized repository method to get or create portfolio
            portfolio = self.portfolio_repo._create_or_get(
                name=name,
                portfolio_type=portfolio_type,
                initial_cash=initial_cash,
                currency_code="USD"
            )
            
            self._current_portfolio_entity = portfolio
            
            # Create portfolio value factor using market data service
            if self.market_data_service and hasattr(self.market_data_service, '_create_or_get'):
                try:
                    # Configure entity_config for MarketDataService._create_or_get method
                    entity_config = {
                        'entity_class': PortfolioValueFactor,
                        'entity_symbol': f"portfolio_value_{portfolio.name}",
                        'factor_type': "portfolio_value_factor",
                        'group': "value",
                        'subgroup': "portfolio",
                        'frequency': "1d",
                        'data_type': "numeric",
                        'source': "calculated",
                        'definition': f"Portfolio value factor for {portfolio.name}"
                    }
                    
                    portfolio_value_factor = self.market_data_service._create_or_get(entity_config
                    )
                    
                    if self.logger and portfolio_value_factor:
                        self.logger.info(f"✅ Portfolio value factor created: {portfolio_value_factor.name}")
                        
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"⚠️ Failed to create portfolio value factor: {e}")
            
            if self.logger:
                self.logger.info(f"✅ Portfolio registered: {portfolio.name} (ID: {portfolio.id})")
            
            return portfolio
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Portfolio registration failed: {e}")
            return None

    def register_portfolio_with_config(
        self, 
        portfolio_config: Optional[Dict[str, Any]] = None,
        name: str = None,
        initial_cash: float = None,
        portfolio_type: str = None
    ) -> Optional[Portfolio]:
        """
        Enhanced portfolio registration that creates main portfolio + sub-portfolios from config.
        
        Args:
            portfolio_config: Full portfolio configuration dict with sub-portfolios
            name: Portfolio name (fallback)
            initial_cash: Initial cash (fallback)
            portfolio_type: Portfolio type (fallback)
            
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
                sub_portfolios_config = portfolio_config.get('sub_portfolios', [])
            else:
                # Fallback to individual parameters
                main_name = name or 'Default_Portfolio'
                main_cash = initial_cash or 100000.0
                main_type = portfolio_type or 'BACKTEST'
                main_currency = 'USD'
                initial_cash_currency_code = main_currency
                sub_portfolios_config = []

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
            
            # Create sub-portfolios
            created_sub_portfolios = []
            for sub_config in sub_portfolios_config:
                try:
                    sub_name = sub_config.get('name', f"{main_name}_Sub")
                    sub_cash = sub_config.get('initial_cash', main_cash)
                    sub_type = sub_config.get('portfolio_type', main_type)
                    sub_currency = sub_config.get('currency_code', main_currency)
                    sub_portfolio_type = sub_config.get('type', 'general')  # company_share, derivative, etc.
                    repo = self.repository_factory.get_local_repository(sub_config['class'])
                    # Create sub-portfolio
                    sub_portfolio = repo._create_or_get(
                        name=sub_name,
                        currency_code=sub_currency,
                        initial_cash=sub_cash,
                        portfolio_type=sub_type,
                    )
                    
                    if sub_portfolio:
                        created_sub_portfolios.append(sub_portfolio)
                        
                        # Create sub-portfolio specific value factors
                        if self.market_data_service and hasattr(self.market_data_service, '_create_or_get'):
                            try:
                                # Determine factor type based on sub-portfolio type
                                if sub_portfolio_type == 'company_share':
                                    factor_type = "company_share_portfolio_value_factor"
                                else:
                                    factor_type = "portfolio_value_factor"
                                
                                # Configure entity_config for MarketDataService._create_or_get method
                                entity_config = {
                                    'entity_class': Factor,  # Factor entity class
                                    'entity_symbol': f"{sub_portfolio_type}_portfolio_value_{sub_portfolio.name}",
                                    'factor_type': factor_type,
                                    'group': "value",
                                    'subgroup': "portfolio",
                                    'frequency': "1d",
                                    'data_type': "numeric",
                                    'source': "calculated",
                                    'definition': f"{sub_portfolio_type.title()} portfolio value factor for {sub_portfolio.name}"
                                }
                                
                                sub_portfolio_value_factor = self.market_data_service._create_or_get(entity_config)
                                
                                if self.logger and sub_portfolio_value_factor:
                                    self.logger.info(f"✅ Sub-portfolio value factor created: {sub_portfolio_value_factor.name}")
                                    
                            except Exception as factor_e:
                                if self.logger:
                                    self.logger.warning(f"⚠️ Failed to create sub-portfolio value factor: {factor_e}")
                        
                        if self.logger:
                            self.logger.info(f"✅ Sub-portfolio created: {sub_portfolio.name} (Type: {sub_portfolio_type})")
                    else:
                        if self.logger:
                            self.logger.warning(f"⚠️ Failed to create sub-portfolio: {sub_name}")
                            
                except Exception as sub_e:
                    if self.logger:
                        self.logger.error(f"❌ Error creating sub-portfolio {sub_config.get('name', 'unknown')}: {sub_e}")
                    continue
            
            if self.logger:
                self.logger.info(f"✅ Portfolio registration complete: {main_portfolio.name} + {len(created_sub_portfolios)} sub-portfolios")
            
            return main_portfolio
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Enhanced portfolio registration failed: {e}")
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

    def get_portfolio_value(self) -> float:
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

        if total == 0.0 and self._current_portfolio_entity is not None:
            try:
                total = float(getattr(self._current_portfolio_entity, 'initial_cash', 0) or 0)
            except Exception:
                pass

        # Persist pre-trade snapshot — at most once per algorithm bar
        if (
            self.portfolio_value_factor is not None
            and self._current_portfolio_entity is not None
            and getattr(self.portfolio_value_factor, 'id', None)
            and getattr(self._current_portfolio_entity, 'id', None)
        ):
            current_time = (
                self._algorithm.time
                if self._algorithm and hasattr(self._algorithm, 'time')
                else datetime.now()
            )
            if self._last_pv_snapshot_time != current_time:
                try:
                    # Source active positions as factor dependencies
                    positions = self.get_active_positions()
                    dependencies = {
                        f"holding_{p['holding_id']}": Decimal(str(p['market_value']))
                        for p in positions
                    }

                    # Compute via the factor entity's calculate function
                    self.portfolio_value_factor.calculate(dependencies)

                    # Persist (create-or-get) via the resolution service
                    fv_repo = self.repository_factory.factor_value_local_repo
                    if fv_repo and hasattr(fv_repo, 'resolution_service'):
                        fv_repo.resolution_service.resolve_factor_value(
                            factor_entity=self.portfolio_value_factor,
                            entity=self._current_portfolio_entity,
                            time_date=current_time,
                        )
                    self._last_pv_snapshot_time = current_time
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"get_portfolio_value: FactorValue snapshot failed: {e}")

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

        # 2. DB currency holding
        try:
            if self._current_portfolio_entity:
                currency_repo = getattr(self.repository_factory, 'currency_local_repo', None)
                holdings = self.holding_repo.get_by_portfolio_id(
                    self._current_portfolio_entity.id
                )
                for holding in holdings:
                    asset_id = getattr(getattr(holding, 'asset', None), 'id', None)
                    if asset_id and currency_repo and hasattr(currency_repo, 'get_by_id'):
                        if currency_repo.get_by_id(asset_id) is not None:
                            qty = getattr(getattr(holding, 'position', None), 'quantity', None)
                            if qty is not None:
                                return Decimal(str(qty))
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

    def set_holdings(self, ticker: str, percentage: float, data=None, tag: str = "") -> bool:
        """
        Orchestrate a portfolio-weight trade for `ticker`.

        This is the single entry-point called from the algorithm layer.
        UPM resolves the inputs (price, quantities) and delegates the
        actual persistence pipeline to TradeManager.

        Args:
            ticker:     asset symbol string (e.g. 'AAPL')
            percentage: target portfolio weight (0.0 – 1.0)
            data:       current Slice object from on_data – prices are read from
                        data.bars[symbol].close when present
            tag:        optional order tag
        """
        if not self._current_portfolio_entity:
            if self.logger:
                self.logger.warning("set_holdings: no portfolio registered")
            return False

        # Portfolio value
        try:
            pv = self.get_portfolio_value()
            portfolio_value = float(getattr(pv, "value", pv))
        except Exception:
            portfolio_value = 0.0

        if portfolio_value <= 0:
            if self.logger:
                self.logger.warning(f"set_holdings: invalid portfolio value {portfolio_value}")
            return False

        # Price resolution: Slice bars first, then algorithm's resolver as fallback
        price = self._price_from_slice(ticker, data)
        if not price or price <= 0:
            if self._algorithm and hasattr(self._algorithm, "_resolve_asset_price"):
                price = self._algorithm._resolve_asset_price(ticker)

        if not price or price <= 0:
            if self.logger:
                self.logger.warning(f"set_holdings: no price available for {ticker}")
            return False

        target_qty = int(portfolio_value * percentage / price)
        current_qty = self._get_current_position_qty(ticker)
        order_qty = target_qty - current_qty

        if order_qty == 0:
            return True

        if not self._has_budget_for_trade(order_qty, price, current_qty):
            if self.logger:
                self.logger.warning(
                    f"set_holdings: insufficient budget for {ticker} "
                    f"qty={order_qty:+d} @ {price:.2f}"
                )
            return False

        current_time = (
            self._algorithm.time
            if self._algorithm and hasattr(self._algorithm, "time")
            else datetime.now()
        )

        if not self._algorithm:
            if self.logger:
                self.logger.warning("set_holdings: algorithm not injected, cannot submit order")
            return False

        return self._trade_manager.execute_trade(
            ticker=ticker,
            order_qty=order_qty,
            price=price,
            portfolio_id=self._current_portfolio_entity.id,
            current_time=current_time,
            submit_order_fn=self._algorithm.market_order,
            tag=tag,
        )

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
        Return the current Position quantity for ticker.

        PositionModel has no symbol column — navigate via:
          FinancialAsset (symbol) → Holding (container+asset) → Position (position_id)
        """
        try:
            from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
            from src.infrastructure.models.finance.holding.holding import HoldingModel
            from src.infrastructure.models.finance.position import PositionModel

            session = self.portfolio_repo.session

            asset = session.query(FinancialAssetModel).filter(
                FinancialAssetModel.symbol == ticker
            ).first()
            if not asset:
                return 0

            holding = session.query(HoldingModel).filter(
                HoldingModel.container_id == self._current_portfolio_entity.id,
                HoldingModel.asset_id == asset.id,
            ).first()
            if not holding or not holding.position_id:
                return 0

            pos = session.query(PositionModel).filter(
                PositionModel.id == holding.position_id
            ).first()
            return int(pos.quantity) if pos else 0

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