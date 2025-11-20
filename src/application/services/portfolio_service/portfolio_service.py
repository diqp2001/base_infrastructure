# src/application/services/portfolio_service.py
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import date, datetime
import pandas as pd
from application.services.database_service.database_service import DatabaseService


class PortfolioService:
    """Service class for managing portfolios, positions, and portfolio analytics."""
    
    def __init__(self, database_service=None, db_type: str = 'sqlite'):
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