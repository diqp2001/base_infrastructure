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

    def __init__(self, repository_factory, logger=None):
        """
        Initialize the unified portfolio manager.
        
        Args:
            repository_factory: Factory providing access to all repositories
            logger: Optional logger for debugging
        """
        self.repository_factory = repository_factory
        self.logger = logger
        self._current_portfolio_entity: Optional[Portfolio] = None
        self._order_ticket_mapping: Dict[str, str] = {}  # QC order_id -> domain order_id
        
        # Repository shortcuts
        self.portfolio_repo = repository_factory.portfolio_local_repo
        self.holding_repo = repository_factory.holding_local_repo
        self.position_repo = repository_factory.position_local_repo
        self.order_repo = repository_factory.order_local_repo
        self.transaction_repo = repository_factory.transaction_local_repo

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
                sub_portfolios_config = portfolio_config.get('sub_portfolios', [])
            else:
                # Fallback to individual parameters
                main_name = name or 'Default_Portfolio'
                main_cash = initial_cash or 100000.0
                main_type = portfolio_type or 'BACKTEST'
                main_currency = 'USD'
                sub_portfolios_config = []
            
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
                        #parent_portfolio_id=main_portfolio.id  # Link to main portfolio #link is made by holding
                    )
                    
                    if sub_portfolio:
                        created_sub_portfolios.append(sub_portfolio)
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
            
            if self.logger and persisted_transaction:
                self.logger.info(f"✅ Transaction recorded with cascading relationships: {persisted_transaction.id}")
            
            return persisted_transaction
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Transaction recording failed: {e}")
            return None

    def get_portfolio_value(self) -> Decimal:
        """
        Get current total portfolio value using domain entities.
        
        Returns:
            Total portfolio value including cash and holdings
        """
        if not self._current_portfolio_entity:
            return Decimal('0')
            
        try:
            # Get all active holdings for this portfolio
            holdings = self.holding_repo.get_by_portfolio_id(self._current_portfolio_entity.id)
            
            total_holdings_value = Decimal('0')
            for holding in holdings:
                if holding.is_active():
                    # Calculate holding value (simplified - would use market prices in reality)
                    holding_value = self._calculate_holding_market_value(holding)
                    total_holdings_value += holding_value
            
            # Get cash balance (would be tracked via separate cash holding or portfolio attribute)
            cash_balance = self._get_cash_balance()
            
            return total_holdings_value + cash_balance
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Portfolio value calculation failed: {e}")
            return Decimal('0')

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

    def _get_cash_balance(self) -> Decimal:
        """Get current cash balance for the portfolio."""
        # Simplified - would be tracked via cash holdings or portfolio cash attribute
        return Decimal('10000.0')

    def _get_asset_symbol(self, asset) -> str:
        """Get symbol string from asset entity."""
        # Simplified - would access asset properties
        return getattr(asset, 'symbol', 'UNKNOWN')

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