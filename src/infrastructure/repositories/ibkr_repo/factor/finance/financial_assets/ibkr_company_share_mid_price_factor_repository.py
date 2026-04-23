"""
src/infrastructure/repositories/ibkr_repo/factor/finance/financial_assets/ibkr_company_share_mid_price_factor_repository.py

IBKR repository for CompanyShareMidPriceFactor operations.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import CompanyShareMidPriceFactor
from src.domain.ports.factor.company_share_mid_price_factor_port import CompanyShareMidPriceFactorPort


class IBKRCompanyShareMidPriceFactorRepository(CompanyShareMidPriceFactorPort):
    """IBKR repository for CompanyShareMidPriceFactor operations."""

    def __init__(self, ibkr_client, factory=None):
        self.ibkr_client = ibkr_client
        self.factory = factory
        self.local_repo = factory._local_repositories.get('company_share_mid_price_factor') if factory else None

    def _create_or_get(self, name: str, **kwargs) -> Optional[CompanyShareMidPriceFactor]:
        """Create new factor or get existing one with IBKR integration."""
        try:
            if self.local_repo:
                return self.local_repo._create_or_get(
                    name=name,
                    **kwargs
                )
            return None

        except Exception as e:
            print(f"IBKR CompanyShareMidPriceFactor error {name}: {e}")
            return None

    def calculate_mid_price_from_multiple_sources(
        self, 
        symbol: str, 
        timestamp: datetime = None
    ) -> Optional[Decimal]:
        """
        Calculate mid price from multiple IBKR data sources.
        
        This method gathers price data from different IBKR tick types
        and calculates the true mid price using the factor's algorithm.
        """
        try:
            # Gather prices from multiple IBKR sources
            source_prices = self._gather_ibkr_price_sources(symbol, timestamp)
            
            if not source_prices:
                return None
            
            # Create a factor instance for calculation
            factor = CompanyShareMidPriceFactor()
            
            # Calculate true mid price
            return factor.calculate(source_prices)
            
        except Exception as e:
            print(f"Error calculating mid price for {symbol}: {e}")
            return None

    def _gather_ibkr_price_sources(self, symbol: str, timestamp: datetime = None) -> List[Dict[str, Any]]:
        """Gather price data from different IBKR sources."""
        source_prices = []
        
        try:
            ib = self.ibkr_client
            
            # Get market data from different tick types
            # These represent different price sources within IBKR
            tick_types = {
                'bid': 1,  # Bid price
                'ask': 2,  # Ask price
                'last': 4,  # Last traded price
                'close': 9, # Previous close
            }
            
            for source_name, tick_type in tick_types.items():
                try:
                    # Get price data from IBKR
                    price_data = ib.get_market_data(symbol, tick_type)
                    
                    if price_data and 'price' in price_data:
                        # Calculate mid price for bid/ask
                        if source_name == 'bid' and 'ask_price' in price_data:
                            mid_price = (price_data['price'] + price_data['ask_price']) / 2
                        elif source_name == 'ask' and 'bid_price' in price_data:
                            mid_price = (price_data['price'] + price_data['bid_price']) / 2
                        else:
                            mid_price = price_data['price']
                        
                        source_prices.append({
                            'source': f"ibkr_{source_name}",
                            'price': Decimal(str(mid_price)),
                            'timestamp': timestamp or datetime.now(),
                            'group': 'price',
                            'subgroup': 'mid_price_true'
                        })
                        
                except Exception as e:
                    print(f"Error getting {source_name} price for {symbol}: {e}")
                    continue
            
            return source_prices
            
        except Exception as e:
            print(f"Error gathering IBKR price sources for {symbol}: {e}")
            return []

    # Standard repository interface methods delegate to local repository
    def get_by_id(self, id: int) -> Optional[CompanyShareMidPriceFactor]:
        """Get factor by ID."""
        return self.local_repo.get_by_id(id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[CompanyShareMidPriceFactor]:
        """Get factor by name."""
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_all(self) -> List[CompanyShareMidPriceFactor]:
        """Get all factors."""
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CompanyShareMidPriceFactor) -> Optional[CompanyShareMidPriceFactor]:
        """Add new factor."""
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CompanyShareMidPriceFactor) -> Optional[CompanyShareMidPriceFactor]:
        """Update existing factor."""
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, id: int) -> bool:
        """Delete factor by ID."""
        return self.local_repo.delete(id) if self.local_repo else False