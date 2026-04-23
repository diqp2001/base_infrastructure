# src/application/services/portfolio_service.py
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import date, datetime
import pandas as pd
from src.application.services.database_service.database_service import DatabaseService


class PortfolioService:
    """Service class for managing portfolios, positions, and portfolio analytics."""
    
    def __init__(self, database_service: Optional[DatabaseService] = None, db_type: str = 'sqlite'):
        """
        Initialize the PortfolioService with a database service.
        :param database_service: Optional existing DatabaseService instance
        :param db_type: The database type for the DatabaseService (ignored if database_service provided).
        """
        if database_service is not None:
            self.database_service = database_service
        else:
            self.database_service = DatabaseService(db_type)
    
    def create_portfolio(self, name: str, description: str = None, initial_cash: Decimal = None, 
                        currency: str = 'USD', benchmark: str = None) -> Dict[str, Any]:
        """
        Create a new portfolio.
        :param name: Portfolio name.
        :param description: Optional portfolio description.
        :param initial_cash: Initial cash amount.
        :param currency: Portfolio currency.
        :param benchmark: Optional benchmark symbol.
        :return: Portfolio information dictionary.
        """
        portfolio_data = {
            'name': name,
            'description': description,
            'initial_cash': float(initial_cash) if initial_cash else 0.0,
            'current_cash': float(initial_cash) if initial_cash else 0.0,
            'currency': currency,
            'benchmark': benchmark,
            'created_at': datetime.now(),
            'status': 'active'
        }
        
        try:
            # Insert portfolio into database
            query = """
            INSERT INTO portfolios (name, description, initial_cash, current_cash, currency, benchmark, created_at, status)
            VALUES (:name, :description, :initial_cash, :current_cash, :currency, :benchmark, :created_at, :status)
            """
            self.database_service.session.execute(query, portfolio_data)
            self.database_service.session.commit()
            
            # Get the created portfolio ID
            result = self.database_service.session.execute("SELECT last_insert_rowid()").fetchone()
            portfolio_data['id'] = result[0]
            
            print(f"Portfolio '{name}' created successfully with ID {portfolio_data['id']}")
            return portfolio_data
            
        except Exception as e:
            self.database_service.session.rollback()
            print(f"Error creating portfolio: {e}")
            return None
    
    def add_position(self, portfolio_id: int, symbol: str, quantity: int, entry_price: Decimal,
                    entry_date: date = None, position_type: str = 'long') -> Dict[str, Any]:
        """
        Add a position to a portfolio.
        :param portfolio_id: Portfolio ID.
        :param symbol: Asset symbol.
        :param quantity: Quantity of shares/units.
        :param entry_price: Entry price per unit.
        :param entry_date: Entry date (defaults to today).
        :param position_type: Position type ('long' or 'short').
        :return: Position information dictionary.
        """
        position_data = {
            'portfolio_id': portfolio_id,
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': float(entry_price),
            'entry_date': entry_date or date.today(),
            'position_type': position_type,
            'current_price': float(entry_price),  # Initially same as entry price
            'market_value': float(entry_price * quantity),
            'unrealized_pnl': 0.0,
            'status': 'open'
        }
        
        try:
            query = """
            INSERT INTO positions (portfolio_id, symbol, quantity, entry_price, entry_date, 
                                 position_type, current_price, market_value, unrealized_pnl, status)
            VALUES (:portfolio_id, :symbol, :quantity, :entry_price, :entry_date, 
                   :position_type, :current_price, :market_value, :unrealized_pnl, :status)
            """
            self.database_service.session.execute(query, position_data)
            self.database_service.session.commit()
            
            # Get the created position ID
            result = self.database_service.session.execute("SELECT last_insert_rowid()").fetchone()
            position_data['id'] = result[0]
            
            # Update portfolio cash
            total_cost = float(entry_price * quantity)
            self._update_portfolio_cash(portfolio_id, -total_cost)
            
            print(f"Position for {symbol} added successfully to portfolio {portfolio_id}")
            return position_data
            
        except Exception as e:
            self.database_service.session.rollback()
            print(f"Error adding position: {e}")
            return None
    
    def update_position_price(self, position_id: int, current_price: Decimal) -> bool:
        """
        Update the current price of a position.
        :param position_id: Position ID.
        :param current_price: Current market price.
        :return: True if successful, False otherwise.
        """
        try:
            # Get position details
            position = self.get_position(position_id)
            if not position:
                return False
            
            # Calculate new market value and unrealized P&L
            quantity = position['quantity']
            entry_price = position['entry_price']
            new_market_value = float(current_price * quantity)
            unrealized_pnl = float((current_price - entry_price) * quantity)
            
            # Update position
            query = """
            UPDATE positions 
            SET current_price = :current_price, market_value = :market_value, unrealized_pnl = :unrealized_pnl
            WHERE id = :position_id
            """
            self.database_service.session.execute(query, {
                'current_price': float(current_price),
                'market_value': new_market_value,
                'unrealized_pnl': unrealized_pnl,
                'position_id': position_id
            })
            self.database_service.session.commit()
            
            return True
            
        except Exception as e:
            self.database_service.session.rollback()
            print(f"Error updating position price: {e}")
            return False
    
    def close_position(self, position_id: int, exit_price: Decimal, exit_date: date = None) -> bool:
        """
        Close a position.
        :param position_id: Position ID.
        :param exit_price: Exit price per unit.
        :param exit_date: Exit date (defaults to today).
        :return: True if successful, False otherwise.
        """
        try:
            # Get position details
            position = self.get_position(position_id)
            if not position:
                return False
            
            # Calculate realized P&L
            quantity = position['quantity']
            entry_price = position['entry_price']
            realized_pnl = float((exit_price - entry_price) * quantity)
            
            # Update position
            query = """
            UPDATE positions 
            SET exit_price = :exit_price, exit_date = :exit_date, realized_pnl = :realized_pnl, status = 'closed'
            WHERE id = :position_id
            """
            self.database_service.session.execute(query, {
                'exit_price': float(exit_price),
                'exit_date': exit_date or date.today(),
                'realized_pnl': realized_pnl,
                'position_id': position_id
            })
            
            # Update portfolio cash (add proceeds from sale)
            total_proceeds = float(exit_price * quantity)
            self._update_portfolio_cash(position['portfolio_id'], total_proceeds)
            
            self.database_service.session.commit()
            
            print(f"Position {position_id} closed successfully with realized P&L: {realized_pnl}")
            return True
            
        except Exception as e:
            self.database_service.session.rollback()
            print(f"Error closing position: {e}")
            return False
    
    def get_portfolio(self, portfolio_id: int) -> Optional[Dict[str, Any]]:
        """
        Get portfolio information.
        :param portfolio_id: Portfolio ID.
        :return: Portfolio information dictionary or None.
        """
        try:
            query = "SELECT * FROM portfolios WHERE id = :portfolio_id"
            result = self.database_service.session.execute(query, {'portfolio_id': portfolio_id}).fetchone()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            print(f"Error getting portfolio: {e}")
            return None
    
    def get_position(self, position_id: int) -> Optional[Dict[str, Any]]:
        """
        Get position information.
        :param position_id: Position ID.
        :return: Position information dictionary or None.
        """
        try:
            query = "SELECT * FROM positions WHERE id = :position_id"
            result = self.database_service.session.execute(query, {'position_id': position_id}).fetchone()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            print(f"Error getting position: {e}")
            return None
    
    def get_portfolio_positions(self, portfolio_id: int, status: str = None) -> List[Dict[str, Any]]:
        """
        Get all positions for a portfolio.
        :param portfolio_id: Portfolio ID.
        :param status: Optional position status filter ('open', 'closed').
        :return: List of position dictionaries.
        """
        try:
            if status:
                query = "SELECT * FROM positions WHERE portfolio_id = :portfolio_id AND status = :status"
                params = {'portfolio_id': portfolio_id, 'status': status}
            else:
                query = "SELECT * FROM positions WHERE portfolio_id = :portfolio_id"
                params = {'portfolio_id': portfolio_id}
            
            result = self.database_service.session.execute(query, params).fetchall()
            return [dict(row) for row in result]
            
        except Exception as e:
            print(f"Error getting portfolio positions: {e}")
            return []
    
    def calculate_portfolio_value(self, portfolio_id: int) -> Dict[str, float]:
        """
        Calculate portfolio total value and metrics.
        :param portfolio_id: Portfolio ID.
        :return: Dictionary with portfolio valuation metrics.
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                return {}
            
            positions = self.get_portfolio_positions(portfolio_id, status='open')
            
            total_market_value = sum([pos['market_value'] for pos in positions])
            total_unrealized_pnl = sum([pos['unrealized_pnl'] for pos in positions])
            current_cash = portfolio['current_cash']
            
            # Calculate closed positions P&L
            closed_positions = self.get_portfolio_positions(portfolio_id, status='closed')
            total_realized_pnl = sum([pos.get('realized_pnl', 0) for pos in closed_positions])
            
            total_portfolio_value = total_market_value + current_cash
            initial_value = portfolio['initial_cash']
            total_return = total_portfolio_value - initial_value
            
            return {
                'portfolio_id': portfolio_id,
                'total_market_value': total_market_value,
                'current_cash': current_cash,
                'total_portfolio_value': total_portfolio_value,
                'initial_value': initial_value,
                'total_return': total_return,
                'total_return_pct': (total_return / initial_value * 100) if initial_value > 0 else 0,
                'unrealized_pnl': total_unrealized_pnl,
                'realized_pnl': total_realized_pnl,
                'total_pnl': total_unrealized_pnl + total_realized_pnl,
                'position_count': len(positions)
            }
            
        except Exception as e:
            print(f"Error calculating portfolio value: {e}")
            return {}
    
    def generate_portfolio_report(self, portfolio_id: int) -> Dict[str, Any]:
        """
        Generate a comprehensive portfolio report.
        :param portfolio_id: Portfolio ID.
        :return: Dictionary containing portfolio report.
        """
        portfolio = self.get_portfolio(portfolio_id)
        if not portfolio:
            return {}
        
        valuation = self.calculate_portfolio_value(portfolio_id)
        positions = self.get_portfolio_positions(portfolio_id)
        open_positions = [pos for pos in positions if pos['status'] == 'open']
        closed_positions = [pos for pos in positions if pos['status'] == 'closed']
        
        # Calculate performance metrics
        winning_trades = [pos for pos in closed_positions if pos.get('realized_pnl', 0) > 0]
        losing_trades = [pos for pos in closed_positions if pos.get('realized_pnl', 0) < 0]
        
        win_rate = (len(winning_trades) / len(closed_positions) * 100) if closed_positions else 0
        avg_win = sum([pos.get('realized_pnl', 0) for pos in winning_trades]) / len(winning_trades) if winning_trades else 0
        avg_loss = sum([pos.get('realized_pnl', 0) for pos in losing_trades]) / len(losing_trades) if losing_trades else 0
        
        report = {
            'portfolio_info': portfolio,
            'valuation': valuation,
            'positions_summary': {
                'total_positions': len(positions),
                'open_positions': len(open_positions),
                'closed_positions': len(closed_positions)
            },
            'performance_metrics': {
                'win_rate': win_rate,
                'average_win': avg_win,
                'average_loss': avg_loss,
                'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
            },
            'open_positions': open_positions,
            'closed_positions': closed_positions,
            'report_date': datetime.now().isoformat()
        }
        
        return report
    
    def get_portfolio_history(self, portfolio_id: int, start_date: date = None, 
                             end_date: date = None) -> pd.DataFrame:
        """
        Get portfolio value history over time.
        :param portfolio_id: Portfolio ID.
        :param start_date: Start date for history.
        :param end_date: End date for history.
        :return: DataFrame with portfolio history.
        """
        try:
            # This is a simplified version - in a real implementation,
            # you'd want to track portfolio values over time in a separate table
            query = """
            SELECT entry_date as date, SUM(market_value) as total_value
            FROM positions 
            WHERE portfolio_id = :portfolio_id
            GROUP BY entry_date
            ORDER BY entry_date
            """
            
            params = {'portfolio_id': portfolio_id}
            if start_date:
                query += " AND entry_date >= :start_date"
                params['start_date'] = start_date
            if end_date:
                query += " AND entry_date <= :end_date"
                params['end_date'] = end_date
            
            result = self.database_service.session.execute(query, params).fetchall()
            return pd.DataFrame(result, columns=['date', 'total_value'])
            
        except Exception as e:
            print(f"Error getting portfolio history: {e}")
            return pd.DataFrame()
    
    def _update_portfolio_cash(self, portfolio_id: int, cash_change: float):
        """
        Update portfolio cash balance.
        :param portfolio_id: Portfolio ID.
        :param cash_change: Change in cash (positive for inflow, negative for outflow).
        """
        try:
            query = """
            UPDATE portfolios 
            SET current_cash = current_cash + :cash_change
            WHERE id = :portfolio_id
            """
            self.database_service.session.execute(query, {
                'cash_change': cash_change,
                'portfolio_id': portfolio_id
            })
            
        except Exception as e:
            print(f"Error updating portfolio cash: {e}")
    
    def list_portfolios(self, status: str = None) -> List[Dict[str, Any]]:
        """
        List all portfolios.
        :param status: Optional status filter.
        :return: List of portfolio dictionaries.
        """
        try:
            if status:
                query = "SELECT * FROM portfolios WHERE status = :status"
                params = {'status': status}
            else:
                query = "SELECT * FROM portfolios"
                params = {}
            
            result = self.database_service.session.execute(query, params).fetchall()
            return [dict(row) for row in result]
            
        except Exception as e:
            print(f"Error listing portfolios: {e}")
            return []
    
    def delete_portfolio(self, portfolio_id: int) -> bool:
        """
        Delete a portfolio and all its positions.
        :param portfolio_id: Portfolio ID.
        :return: True if successful, False otherwise.
        """
        try:
            # Delete positions first
            self.database_service.session.execute(
                "DELETE FROM positions WHERE portfolio_id = :portfolio_id",
                {'portfolio_id': portfolio_id}
            )
            
            # Delete portfolio
            self.database_service.session.execute(
                "DELETE FROM portfolios WHERE id = :portfolio_id",
                {'portfolio_id': portfolio_id}
            )
            
            self.database_service.session.commit()
            print(f"Portfolio {portfolio_id} deleted successfully")
            return True
            
        except Exception as e:
            self.database_service.session.rollback()
            print(f"Error deleting portfolio: {e}")
            return False

    def calculate_holding_total_value(self) -> Dict[str, Any]:
        """
        Calculate total value for all holdings using quantity × mid_price approach.
        
        This function gets quantities from holdings/positions and multiplies by current mid prices
        from financial assets to get true market value.
        
        :return: Dictionary containing holding value breakdown
        """
        try:
            result = {
                'holdings': {'count': 0, 'total_market_value': 0.0, 'details': []},
                'positions': {'count': 0, 'total_market_value': 0.0, 'details': []},
                'total_holdings_value': 0.0,
                'calculation_timestamp': datetime.now().isoformat()
            }
            
            # Calculate holdings values using holdings table with asset relationships
            try:
                holdings_query = """
                SELECT h.id, h.asset_id, h.container_id,
                       pch.quantity, pch.start_date, pch.end_date,
                       cs.symbol, cs.name
                FROM holdings h
                LEFT JOIN portfolio_company_share_holdings pch ON h.id = pch.id
                LEFT JOIN company_shares cs ON pch.asset_id = cs.id
                WHERE pch.end_date IS NULL OR pch.end_date > CURRENT_TIMESTAMP
                """
                holdings_results = self.database_service.session.execute(holdings_query).fetchall()
                
                for holding in holdings_results:
                    if holding[3]:  # quantity exists
                        # Get mid price for this financial asset
                        mid_price = self._get_asset_mid_price(holding[1])  # asset_id
                        if mid_price:
                            market_value = float(holding[3]) * float(mid_price)  # quantity × mid_price
                            result['holdings']['total_market_value'] += market_value
                            result['holdings']['details'].append({
                                'holding_id': holding[0],
                                'asset_id': holding[1],
                                'symbol': holding[6],
                                'quantity': float(holding[3]),
                                'mid_price': float(mid_price),
                                'market_value': market_value
                            })
                
                result['holdings']['count'] = len(holdings_results)
                
            except Exception as e:
                print(f"Warning: Error calculating holdings values: {e}")
                result['holdings'] = {'count': 0, 'total_market_value': 0.0, 'details': []}
            
            # Calculate positions values using positions table (alternative approach)
            try:
                positions_query = """
                SELECT p.id, p.portfolio_id, p.quantity, p.position_type
                FROM positions p
                """
                positions_results = self.database_service.session.execute(positions_query).fetchall()
                
                for position in positions_results:
                    if position[2]:  # quantity exists
                        # Note: positions table doesn't have direct asset_id link
                        # This would need enhancement to link positions to specific financial assets
                        # For now, treating as placeholder quantity without price calculation
                        result['positions']['details'].append({
                            'position_id': position[0],
                            'portfolio_id': position[1],
                            'quantity': float(position[2]),
                            'position_type': str(position[3]),
                            'market_value': 0.0  # Cannot calculate without asset_id
                        })
                
                result['positions']['count'] = len(positions_results)
                
            except Exception as e:
                print(f"Warning: Error calculating positions values: {e}")
                result['positions'] = {'count': 0, 'total_market_value': 0.0, 'details': []}
            
            # Total holdings value (primarily from holdings table)
            result['total_holdings_value'] = result['holdings']['total_market_value']
            
            return result
            
        except Exception as e:
            print(f"Error calculating holding total value: {e}")
            return {
                'error': str(e),
                'total_holdings_value': 0.0,
                'calculation_timestamp': datetime.now().isoformat()
            }
    
    def _get_asset_mid_price(self, asset_id: int) -> Optional[float]:
        """
        Get current mid price for a financial asset.
        
        This is a simplified implementation. In production, this would:
        1. Query the factor tables for latest mid price
        2. Use CompanyShareMidPriceFactor repository
        3. Handle different asset types (stocks, options, etc.)
        
        :param asset_id: ID of the financial asset
        :return: Current mid price or None
        """
        try:
            # Simplified approach: get latest price from company_shares table
            price_query = """
            SELECT current_price 
            FROM company_shares 
            WHERE id = :asset_id
            AND current_price IS NOT NULL
            """
            price_result = self.database_service.session.execute(price_query, {'asset_id': asset_id}).fetchone()
            
            if price_result and price_result[0]:
                return float(price_result[0])
            
            # Fallback: return a default price for testing
            return 100.0  # Default mid price for demo purposes
            
        except Exception as e:
            print(f"Warning: Error getting mid price for asset {asset_id}: {e}")
            return 100.0  # Default mid price for demo purposes

    def calculate_total_value(self) -> Dict[str, Any]:
        """
        Calculate total value across all portfolios, holdings, orders, transactions, and accounts.
        
        This function uses quantity-based calculations with dependencies:
        1. Holdings calculation (base dependency) - quantity × mid_price
        2. Portfolio calculation depends on holdings
        3. Total value aggregates all factors
        
        :return: Dictionary containing total value breakdown and summary
        """
        try:
            result = {
                'total_value': 0.0,
                'portfolios': {'count': 0, 'total_value': 0.0, 'cash': 0.0, 'market_value': 0.0},
                'holdings': {'count': 0, 'total_market_value': 0.0, 'details': []},
                'positions': {'count': 0, 'total_market_value': 0.0, 'details': []},
                'orders': {'count': 0, 'total_pending_value': 0.0},
                'transactions': {'count': 0, 'total_executed_value': 0.0},
                'accounts': {'count': 0, 'total_cash_balance': 0.0},
                'calculation_timestamp': datetime.now().isoformat()
            }
            
            # Step 1: Calculate holdings total value (base dependency)
            holdings_data = self.calculate_holding_total_value()
            result['holdings'] = holdings_data.get('holdings', {'count': 0, 'total_market_value': 0.0, 'details': []})
            result['positions'] = holdings_data.get('positions', {'count': 0, 'total_market_value': 0.0, 'details': []})
            holdings_market_value = holdings_data.get('total_holdings_value', 0.0)
            
            # Step 2: Calculate portfolio values (depends on holdings)
            portfolios = self.list_portfolios()
            for portfolio in portfolios:
                portfolio_value = self.calculate_portfolio_value(portfolio['id'])
                if portfolio_value:
                    result['portfolios']['cash'] += portfolio_value.get('current_cash', 0.0)
                    # Use holdings market value instead of portfolio's calculated market value
                    # This ensures consistency with quantity × mid_price calculations
            
            result['portfolios']['count'] = len(portfolios)
            result['portfolios']['market_value'] = holdings_market_value
            result['portfolios']['total_value'] = result['portfolios']['cash'] + result['portfolios']['market_value']
            
            # Step 3: Calculate orders values using quantity × price approach
            try:
                orders_query = """
                SELECT COUNT(*) as count, 
                       SUM(COALESCE(quantity, 0) * COALESCE(price, 0)) as total_pending_value
                FROM orders 
                WHERE status IN ('PENDING', 'SUBMITTED', 'PARTIALLY_FILLED')
                """
                orders_result = self.database_service.session.execute(orders_query).fetchone()
                if orders_result:
                    result['orders']['count'] = orders_result[0] or 0
                    result['orders']['total_pending_value'] = float(orders_result[1] or 0)
            except Exception:
                result['orders']['count'] = 0
                result['orders']['total_pending_value'] = 0.0
            
            # Step 4: Calculate transactions values using executed amounts
            try:
                transactions_query = """
                SELECT COUNT(*) as count, 
                       SUM(COALESCE(quantity, 0) * COALESCE(execution_price, 0)) as total_executed_value
                FROM transactions 
                WHERE status = 'EXECUTED'
                """
                transactions_result = self.database_service.session.execute(transactions_query).fetchone()
                if transactions_result:
                    result['transactions']['count'] = transactions_result[0] or 0
                    result['transactions']['total_executed_value'] = float(transactions_result[1] or 0)
            except Exception:
                result['transactions']['count'] = 0
                result['transactions']['total_executed_value'] = 0.0
            
            # Step 5: Calculate accounts values
            try:
                accounts_query = """
                SELECT COUNT(*) as count, SUM(COALESCE(current_cash, 0)) as total_cash_balance
                FROM accounts 
                WHERE status = 'ACTIVE'
                """
                accounts_result = self.database_service.session.execute(accounts_query).fetchone()
                if accounts_result:
                    result['accounts']['count'] = accounts_result[0] or 0
                    result['accounts']['total_cash_balance'] = float(accounts_result[1] or 0)
            except Exception:
                result['accounts']['count'] = 0
                result['accounts']['total_cash_balance'] = result['portfolios']['cash']
            
            # Step 6: Calculate total value factor (aggregation of all components)
            result['total_value'] = (
                result['portfolios']['total_value'] +
                result['orders']['total_pending_value'] +
                result['accounts']['total_cash_balance']
                # Note: Not adding transactions as they're historical, not current value
            )
            
            return result
            
        except Exception as e:
            print(f"Error calculating total value: {e}")
            return {
                'error': str(e),
                'total_value': 0.0,
                'calculation_timestamp': datetime.now().isoformat()
            }