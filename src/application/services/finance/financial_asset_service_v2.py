"""
Financial Asset Service V2 - Infrastructure-agnostic financial asset service.

This service follows the IBKR repository architecture pattern, depending only on ports
rather than concrete repository implementations. This ensures the service layer
remains clean and can work with any repository implementation (local, IBKR, etc.).
"""

from typing import Optional, List
from datetime import date
from decimal import Decimal

from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.currency import Currency
from src.domain.entities.finance.financial_assets.bond import Bond

from src.domain.ports.financial_assets.index_future_port import IndexFuturePort
from src.domain.ports.financial_assets.company_share_port import CompanySharePort
from src.domain.ports.financial_assets.currency_port import CurrencyPort
from src.domain.ports.financial_assets.bond_port import BondPort


class FinancialAssetServiceV2:
    """
    Infrastructure-agnostic financial asset service.
    
    This service depends ONLY on port interfaces, not concrete repository implementations.
    It does not know if data comes from IBKR, local database, or any other source.
    This is intentional and follows the Ports & Adapters pattern.
    """

    def __init__(
        self,
        index_future_port: IndexFuturePort,
        company_share_port: CompanySharePort,
        currency_port: CurrencyPort,
        bond_port: BondPort
    ):
        """
        Initialize service with port implementations.
        
        Args:
            index_future_port: Repository port for index futures
            company_share_port: Repository port for company shares
            currency_port: Repository port for currencies
            bond_port: Repository port for bonds
        """
        self.index_futures = index_future_port
        self.company_shares = company_share_port
        self.currencies = currency_port
        self.bonds = bond_port

    # Index Future operations
    def get_or_create_index_future(self, symbol: str) -> Optional[IndexFuture]:
        """
        Get or create an index future by symbol.
        
        Args:
            symbol: Future symbol (e.g., 'ESZ25', 'NQH25')
            
        Returns:
            IndexFuture entity or None if failed
        """
        return self.index_futures.get_or_create(symbol)

    def get_index_future_by_symbol(self, symbol: str) -> Optional[IndexFuture]:
        """Get index future by symbol."""
        return self.index_futures.get_by_symbol(symbol)

    def get_all_index_futures(self) -> List[IndexFuture]:
        """Get all index futures."""
        return self.index_futures.get_all()

    # Company Share operations
    def get_or_create_company_share(self, symbol: str) -> Optional[CompanyShare]:
        """
        Get or create a company share by symbol.
        
        Args:
            symbol: Share symbol (e.g., 'AAPL', 'TSLA')
            
        Returns:
            CompanyShare entity or None if failed
        """
        return self.company_shares.get_or_create(symbol)

    def get_company_share_by_ticker(self, ticker: str) -> Optional[CompanyShare]:
        """Get company share by ticker."""
        return self.company_shares.get_by_ticker(ticker)

    def get_all_company_shares(self) -> List[CompanyShare]:
        """Get all company shares."""
        return self.company_shares.get_all()

    # Currency operations
    def get_or_create_currency(self, symbol: str) -> Optional[Currency]:
        """
        Get or create a currency by symbol.
        
        Args:
            symbol: Currency symbol (e.g., 'USD', 'EUR')
            
        Returns:
            Currency entity or None if failed
        """
        return self.currencies.get_or_create(symbol)

    def get_currency_by_iso_code(self, iso_code: str) -> Optional[Currency]:
        """Get currency by ISO code."""
        return self.currencies.get_by_iso_code(iso_code)

    def get_all_currencies(self) -> List[Currency]:
        """Get all currencies."""
        return self.currencies.get_all()

    # Bond operations
    def get_or_create_bond(self, symbol: str) -> Optional[Bond]:
        """
        Get or create a bond by symbol.
        
        Args:
            symbol: Bond symbol/ISIN
            
        Returns:
            Bond entity or None if failed
        """
        return self.bonds.get_or_create(symbol)

    def get_bond_by_isin(self, isin: str) -> Optional[Bond]:
        """Get bond by ISIN."""
        return self.bonds.get_by_isin(isin)

    def get_bonds_by_maturity_range(self, start_date: date, end_date: date) -> List[Bond]:
        """Get bonds maturing within date range."""
        return self.bonds.get_by_maturity_range(start_date, end_date)

    def get_all_bonds(self) -> List[Bond]:
        """Get all bonds."""
        return self.bonds.get_all()

    # Portfolio operations (combining multiple asset types)
    def create_diversified_portfolio(
        self,
        equity_symbols: List[str],
        future_symbols: List[str],
        currency_symbols: List[str],
        bond_symbols: Optional[List[str]] = None
    ) -> dict:
        """
        Create a diversified portfolio with multiple asset types.
        
        This demonstrates how the service can orchestrate multiple repositories
        without knowing their implementation details.
        
        Returns:
            Dictionary with portfolio components or error information
        """
        portfolio = {
            'equities': [],
            'futures': [],
            'currencies': [],
            'bonds': [],
            'errors': []
        }

        # Get or create equity positions
        for symbol in equity_symbols:
            try:
                share = self.get_or_create_company_share(symbol)
                if share:
                    portfolio['equities'].append(share)
                else:
                    portfolio['errors'].append(f"Failed to create/get equity: {symbol}")
            except Exception as e:
                portfolio['errors'].append(f"Error with equity {symbol}: {str(e)}")

        # Get or create future positions
        for symbol in future_symbols:
            try:
                future = self.get_or_create_index_future(symbol)
                if future:
                    portfolio['futures'].append(future)
                else:
                    portfolio['errors'].append(f"Failed to create/get future: {symbol}")
            except Exception as e:
                portfolio['errors'].append(f"Error with future {symbol}: {str(e)}")

        # Get or create currency positions
        for symbol in currency_symbols:
            try:
                currency = self.get_or_create_currency(symbol)
                if currency:
                    portfolio['currencies'].append(currency)
                else:
                    portfolio['errors'].append(f"Failed to create/get currency: {symbol}")
            except Exception as e:
                portfolio['errors'].append(f"Error with currency {symbol}: {str(e)}")

        # Get or create bond positions (optional)
        if bond_symbols:
            for symbol in bond_symbols:
                try:
                    bond = self.get_or_create_bond(symbol)
                    if bond:
                        portfolio['bonds'].append(bond)
                    else:
                        portfolio['errors'].append(f"Failed to create/get bond: {symbol}")
                except Exception as e:
                    portfolio['errors'].append(f"Error with bond {symbol}: {str(e)}")

        return portfolio

    def get_portfolio_summary(self) -> dict:
        """
        Get a summary of all available financial assets.
        
        Returns:
            Dictionary with counts and samples of each asset type
        """
        try:
            return {
                'index_futures': {
                    'count': len(self.get_all_index_futures()),
                    'sample': self.get_all_index_futures()[:5]  # First 5 for preview
                },
                'company_shares': {
                    'count': len(self.get_all_company_shares()),
                    'sample': self.get_all_company_shares()[:5]
                },
                'currencies': {
                    'count': len(self.get_all_currencies()),
                    'sample': self.get_all_currencies()[:5]
                },
                'bonds': {
                    'count': len(self.get_all_bonds()),
                    'sample': self.get_all_bonds()[:5]
                }
            }
        except Exception as e:
            return {'error': f"Failed to get portfolio summary: {str(e)}"}

    def search_assets_by_criteria(
        self,
        asset_type: str,
        search_term: str
    ) -> List:
        """
        Search for assets by criteria.
        
        Args:
            asset_type: Type of asset ('futures', 'shares', 'currencies', 'bonds')
            search_term: Search term (symbol, name, etc.)
            
        Returns:
            List of matching assets
        """
        try:
            if asset_type.lower() == 'futures':
                # For futures, search by symbol
                result = self.get_index_future_by_symbol(search_term.upper())
                return [result] if result else []
            
            elif asset_type.lower() == 'shares':
                # For shares, search by ticker
                result = self.get_company_share_by_ticker(search_term.upper())
                return [result] if result else []
            
            elif asset_type.lower() == 'currencies':
                # For currencies, search by ISO code
                result = self.get_currency_by_iso_code(search_term.upper())
                return [result] if result else []
            
            elif asset_type.lower() == 'bonds':
                # For bonds, search by ISIN
                result = self.get_bond_by_isin(search_term.upper())
                return [result] if result else []
            
            else:
                return []
                
        except Exception as e:
            print(f"Error searching {asset_type} for {search_term}: {str(e)}")
            return []