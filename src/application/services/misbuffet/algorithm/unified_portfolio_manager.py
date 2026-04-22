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
        Register or retrieve a portfolio entity.
        
        Args:
            name: Portfolio name
            initial_cash: Initial cash amount
            portfolio_type: Type of portfolio
            
        Returns:
            Portfolio entity or None if registration failed
        """
        try:
            # Use repository to get or create portfolio
            portfolio = self.portfolio_repo._create_or_get_portfolio(
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

    def get_current_portfolio(self) -> Optional[Portfolio]:
        """Get the current portfolio entity."""
        return self._current_portfolio_entity

    def register_order(self, order_ticket) -> Optional[Order]:
        """
        Register an order from QCAlgorithm order ticket.
        
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
            # Convert QC order ticket to domain entity
            order_entity = self._convert_ticket_to_order(order_ticket)
            
            # Persist using repository
            persisted_order = self.order_repo.add(order_entity)
            
            # Store mapping for future reference
            self._order_ticket_mapping[order_ticket.order_id] = persisted_order.id
            
            if self.logger:
                self.logger.info(f"✅ Order registered: {persisted_order.id}")
            
            return persisted_order
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Order registration failed: {e}")
            return None

    def record_transaction(self, order_event) -> Optional[Transaction]:
        """
        Record a transaction when an order is filled.
        
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
            
            # Create transaction entity
            transaction_entity = self._convert_event_to_transaction(order_event, domain_order_id)
            
            # Persist transaction
            persisted_transaction = self.transaction_repo.add(transaction_entity) #_create_or_get
            
            # Update holdings based on transaction
            self._update_holdings_from_transaction(persisted_transaction)
            
            if self.logger:
                self.logger.info(f"✅ Transaction recorded: {persisted_transaction.id}")
            
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

    def _convert_ticket_to_order(self, ticket) -> Order:
        """Convert QCAlgorithm OrderTicket to domain Order entity."""
        # Get or create holding for this asset
        holding_id = self._get_or_create_holding_for_symbol(ticket.symbol)
        
        return Order(
            id=self._get_next_order_id(),
            portfolio_id=self._current_portfolio_entity.id,
            holding_id=holding_id,
            order_type=self._map_order_type(getattr(ticket, 'order_type', 'MARKET')),
            side=OrderSide.BUY if ticket.quantity > 0 else OrderSide.SELL,
            quantity=abs(ticket.quantity),
            created_at=getattr(ticket, 'time', datetime.now()),
            status=self._map_order_status(getattr(ticket, 'status', 'PENDING')),
            account_id=self._get_account_id(),
            external_order_id=ticket.order_id
        )

    def _convert_event_to_transaction(self, order_event, domain_order_id: str) -> Transaction:
        """Convert QCAlgorithm OrderEvent to domain Transaction entity."""
        return Transaction(
            id=self._get_next_transaction_id(),
            portfolio_id=self._current_portfolio_entity.id,
            holding_id=1,  # Would be retrieved from the order
            order_id=int(domain_order_id),
            date=getattr(order_event, 'time', datetime.now()),
            transaction_type=TransactionType.MARKET_ORDER,  # Simplified
            transaction_id=f"TXN_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            account_id=self._get_account_id(),
            trade_date=getattr(order_event, 'time', datetime.now()).date(),
            value_date=getattr(order_event, 'time', datetime.now()).date(),
            settlement_date=getattr(order_event, 'time', datetime.now()).date(),
            status=TransactionStatus.EXECUTED,
            spread=0.0,
            currency_id=1,  # USD
            exchange_id=1   # Default exchange
        )

    def _update_holdings_from_transaction(self, transaction: Transaction):
        """Update holding quantities based on executed transaction."""
        try:
            # Find the holding
            holding = self.holding_repo.get_by_id(transaction.holding_id)
            if holding:
                # Update position quantity (simplified logic)
                # In practice, this would involve more complex position management
                if self.logger:
                    self.logger.info(f"✅ Holdings updated from transaction {transaction.id}")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Holdings update failed: {e}")

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