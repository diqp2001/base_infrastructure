"""
src/infrastructure/repositories/ibkr_repo/factor/finance/financial_assets/ibkr_company_share_option_mid_price_factor_repository.py

IBKR repository for CompanyShareOptionMidPriceFactor operations.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, date

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor import CompanyShareOptionMidPriceFactor
from src.domain.ports.factor.company_share_option_mid_price_factor_port import CompanyShareOptionMidPriceFactorPort


class IBKRCompanyShareOptionMidPriceFactorRepository(CompanyShareOptionMidPriceFactorPort):
    """IBKR repository for CompanyShareOptionMidPriceFactor operations."""

    def __init__(self, ibkr_client, factory=None):
        self.ibkr_client = ibkr_client
        self.factory = factory
        self.local_repo = factory._local_repositories.get('company_share_option_mid_price_factor') if factory else None

    def _create_or_get(self, name: str, **kwargs) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Create new factor or get existing one with IBKR integration."""
        try:
            if self.local_repo:
                return self.local_repo._create_or_get(
                    name=name,
                    **kwargs
                )
            return None

        except Exception as e:
            print(f"IBKR CompanyShareOptionMidPriceFactor error {name}: {e}")
            return None

    def calculate_option_mid_price_from_multiple_sources(
        self, 
        symbol: str, 
        strike: Decimal,
        expiry: date,
        option_type: str = 'C',  # 'C' for Call, 'P' for Put
        timestamp: datetime = None
    ) -> Optional[Decimal]:
        """
        Calculate option mid price from multiple IBKR data sources.
        
        This method gathers option price data from different IBKR sources
        and calculates the true mid price using the factor's algorithm.
        """
        try:
            # Gather option prices from multiple IBKR sources
            source_prices = self._gather_ibkr_option_price_sources(
                symbol, strike, expiry, option_type, timestamp
            )
            
            if not source_prices:
                return None
            
            # Create a factor instance for calculation
            factor = CompanyShareOptionMidPriceFactor()
            
            # Calculate true mid price
            return factor.calculate(source_prices)
            
        except Exception as e:
            print(f"Error calculating option mid price for {symbol}: {e}")
            return None

    def _gather_ibkr_option_price_sources(
        self, 
        symbol: str, 
        strike: Decimal,
        expiry: date,
        option_type: str,
        timestamp: datetime = None
    ) -> List[Dict[str, Any]]:
        """Gather option price data from different IBKR sources."""
        source_prices = []
        
        try:
            ib = self.ibkr_client
            
            # Create option contract
            option_contract = ib.create_option_contract(
                symbol=symbol,
                expiry=expiry,
                strike=float(strike),
                right=option_type
            )
            
            # Get option prices from different sources
            tick_types = {
                'bid': 1,  # Bid price
                'ask': 2,  # Ask price
                'last': 4,  # Last traded price
                'model': 13, # Model price (if available)
            }
            
            for source_name, tick_type in tick_types.items():
                try:
                    # Get option price data from IBKR
                    price_data = ib.get_option_market_data(option_contract, tick_type)
                    
                    if price_data and 'price' in price_data:
                        # Calculate mid price for bid/ask
                        if source_name == 'bid' and 'ask_price' in price_data:
                            mid_price = (price_data['price'] + price_data['ask_price']) / 2
                        elif source_name == 'ask' and 'bid_price' in price_data:
                            mid_price = (price_data['price'] + price_data['bid_price']) / 2
                        else:
                            mid_price = price_data['price']
                        
                        source_prices.append({
                            'source': f"ibkr_option_{source_name}",
                            'price': Decimal(str(mid_price)),
                            'timestamp': timestamp or datetime.now(),
                            'group': 'price',
                            'subgroup': 'mid_price_true',
                            'strike': strike,
                            'expiry': expiry
                        })
                        
                except Exception as e:
                    print(f"Error getting {source_name} option price for {symbol}: {e}")
                    continue
            
            return source_prices
            
        except Exception as e:
            print(f"Error gathering IBKR option price sources for {symbol}: {e}")
            return []

    # Standard repository interface methods delegate to local repository
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Get factor by ID."""
        return self.local_repo.get_by_id(id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Get factor by name."""
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_all(self) -> List[CompanyShareOptionMidPriceFactor]:
        """Get all factors."""
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CompanyShareOptionMidPriceFactor) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Add new factor."""
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CompanyShareOptionMidPriceFactor) -> Optional[CompanyShareOptionMidPriceFactor]:
        """Update existing factor."""
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, id: int) -> bool:
        """Delete factor by ID."""
        return self.local_repo.delete(id) if self.local_repo else False