"""
Mapper for CompanyShare domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
Enhanced with factor integration for historical price data.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict

from src.domain.entities.finance.financial_assets.company_share import CompanyShare as DomainCompanyShare
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShare as ORMCompanyShare
from src.domain.entities.finance.financial_assets.security import Symbol, SecurityType, MarketData
from src.domain.entities.finance.financial_assets.equity import FundamentalData
from infrastructure.models.factor.finance.financial_assets.share_factors import ShareFactor, ShareFactorValue
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository


class CompanyShareMapper:
    """Mapper for CompanyShare domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMCompanyShare) -> DomainCompanyShare:
        """Convert ORM model to domain entity."""
        # Create domain entity
        domain_entity = DomainCompanyShare(
            id=orm_obj.id,
            ticker=orm_obj.ticker,
            exchange_id=orm_obj.exchange_id,
            company_id=orm_obj.company_id,
            start_date=orm_obj.start_date,
            end_date=orm_obj.end_date
        )
        
        # Set market data if available
        if orm_obj.current_price:
            market_data = MarketData(
                timestamp=orm_obj.last_update or datetime.now(),
                price=Decimal(str(orm_obj.current_price)),
                volume=None
            )
            domain_entity.update_market_data(market_data)
        
        # Set fundamental data if available
        if orm_obj.market_cap or orm_obj.pe_ratio:
            fundamentals = FundamentalData(
                market_cap=Decimal(str(orm_obj.market_cap)) if orm_obj.market_cap else None,
                shares_outstanding=float(orm_obj.shares_outstanding) if orm_obj.shares_outstanding else None,
                pe_ratio=Decimal(str(orm_obj.pe_ratio)) if orm_obj.pe_ratio else None,
                dividend_yield=Decimal(str(orm_obj.dividend_yield)) if orm_obj.dividend_yield else None,
                book_value_per_share=Decimal(str(orm_obj.book_value_per_share)) if orm_obj.book_value_per_share else None,
                earnings_per_share=Decimal(str(orm_obj.earnings_per_share)) if orm_obj.earnings_per_share else None
            )
            domain_entity.update_fundamentals(fundamentals)
        
        # Set additional properties
        if orm_obj.sector:
            domain_entity.set_sector(orm_obj.sector)
        if orm_obj.industry:
            domain_entity.set_industry(orm_obj.industry)
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainCompanyShare, orm_obj: Optional[ORMCompanyShare] = None) -> ORMCompanyShare:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMCompanyShare()
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.ticker = domain_obj.ticker
        orm_obj.exchange_id = domain_obj.exchange_id
        orm_obj.company_id = domain_obj.company_id
        orm_obj.start_date = domain_obj.start_date
        orm_obj.end_date = domain_obj.end_date
        
        # Map market data
        orm_obj.current_price = domain_obj.price
        orm_obj.last_update = domain_obj.last_update
        orm_obj.is_tradeable = domain_obj.is_tradeable
        
        # Map fundamental data
        if domain_obj.fundamentals:
            orm_obj.market_cap = domain_obj.fundamentals.market_cap
            orm_obj.shares_outstanding = domain_obj.fundamentals.shares_outstanding
            orm_obj.pe_ratio = domain_obj.fundamentals.pe_ratio
            orm_obj.dividend_yield = domain_obj.fundamentals.dividend_yield
            orm_obj.book_value_per_share = domain_obj.fundamentals.book_value_per_share
            orm_obj.earnings_per_share = domain_obj.fundamentals.earnings_per_share
        
        # Map additional properties
        orm_obj.sector = domain_obj.sector
        orm_obj.industry = domain_obj.industry
        
        return orm_obj

    @staticmethod
    def populate_price_factors(domain_obj: DomainCompanyShare, share_id: int, 
                              price_data: List[Dict], factor_repository: ShareFactorRepository) -> List[ShareFactorValue]:
        """
        Populate share price factors from historical price data.
        
        :param domain_obj: Domain company share entity
        :param share_id: Database ID of the company share
        :param price_data: List of price data dictionaries with date, open, high, low, close, volume
        :param factor_repository: Repository for managing share factors
        :return: List of created factor value records
        """
        created_values = []
        
        if not price_data:
            return created_values
        
        # Define factor types to create
        factor_types = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
        price_factors = {}
        
        # Create or get factors for each price type
        for factor_type in factor_types:
            factor_name = f"{domain_obj.ticker}_{factor_type}"
            
            try:
                factor = factor_repository.get_by_name(factor_name)
            except:
                # Create new factor
                group = "price" if factor_type != "volume" else "volume"
                factor = factor_repository.add_factor(
                    name=factor_name,
                    group=group,
                    subgroup="historical",
                    data_type="numeric",
                    source="share_mapper",
                    definition=f"{factor_type.replace('_', ' ').title()} data for {domain_obj.ticker}"
                )
            
            price_factors[factor_type] = factor
        
        # Populate factor values from price data
        for price_record in price_data:
            record_date = price_record.get('date')
            if isinstance(record_date, str):
                record_date = datetime.strptime(record_date, '%Y-%m-%d').date()
            elif isinstance(record_date, datetime):
                record_date = record_date.date()
            
            # Create factor values for each price type
            for factor_type, factor in price_factors.items():
                value_key = factor_type
                if factor_type == 'adj_close':
                    value_key = 'adj_close'
                
                if value_key in price_record and price_record[value_key] is not None:
                    try:
                        factor_value = factor_repository.add_factor_value(
                            factor_id=factor.id,
                            entity_id=share_id,
                            date=record_date,
                            value=Decimal(str(price_record[value_key]))
                        )
                        created_values.append(factor_value)
                    except Exception as e:
                        print(f"Warning: Failed to create factor value for {factor.name} on {record_date}: {str(e)}")
                        continue
        
        return created_values

    @staticmethod
    def populate_current_price_factor(domain_obj: DomainCompanyShare, share_id: int, 
                                    factor_repository: ShareFactorRepository) -> Optional[ShareFactorValue]:
        """
        Populate current price as a factor value.
        
        :param domain_obj: Domain company share entity with current price
        :param share_id: Database ID of the company share
        :param factor_repository: Repository for managing share factors
        :return: Created factor value record or None
        """
        if not domain_obj.price:
            return None
        
        # Create or get current price factor
        factor_name = f"{domain_obj.ticker}_current_price"
        
        try:
            factor = factor_repository.get_by_name(factor_name)
        except:
            # Create new factor
            factor = factor_repository.add_factor(
                name=factor_name,
                group="price",
                subgroup="current",
                data_type="numeric",
                source="share_mapper",
                definition=f"Current price for {domain_obj.ticker}"
            )
        
        # Create factor value for current price
        current_date = domain_obj.last_update.date() if domain_obj.last_update else date.today()
        
        try:
            factor_value = factor_repository.add_factor_value(
                factor_id=factor.id,
                entity_id=share_id,
                date=current_date,
                value=domain_obj.price
            )
            return factor_value
        except Exception as e:
            print(f"Warning: Failed to create current price factor value for {factor_name}: {str(e)}")
            return None

    @staticmethod
    def load_price_history_from_factors(orm_obj: ORMCompanyShare, factor_repository: ShareFactorRepository) -> DomainCompanyShare:
        """
        Load company share domain entity with price history from factor data.
        
        :param orm_obj: ORM CompanyShare model
        :param factor_repository: Repository for accessing share factors
        :return: Domain company share entity with historical price data
        """
        # Convert ORM to domain first
        domain_entity = CompanyShareMapper.to_domain(orm_obj)
        
        # Load price history from factors
        price_history = []
        
        try:
            # Get all factor values for this share
            factor_values = factor_repository.get_factor_values_by_entity(orm_obj.id)
            
            # Group by date
            price_by_date = {}
            
            for fv in factor_values:
                if fv.date not in price_by_date:
                    price_by_date[fv.date] = {}
                
                # Extract factor type from name
                factor_name = fv.factor.name
                if domain_entity.ticker in factor_name:
                    factor_type = factor_name.replace(f"{domain_entity.ticker}_", "")
                    price_by_date[fv.date][factor_type] = float(fv.value)
            
            # Convert to market data records
            for price_date, prices in sorted(price_by_date.items()):
                if 'close' in prices:  # At minimum, we need a close price
                    market_data = MarketData(
                        timestamp=datetime.combine(price_date, datetime.min.time()),
                        price=Decimal(str(prices.get('close', 0))),
                        volume=int(prices.get('volume', 0)) if prices.get('volume') else None
                    )
                    
                    # Add additional price data as attributes
                    if 'open' in prices:
                        market_data.open_price = Decimal(str(prices['open']))
                    if 'high' in prices:
                        market_data.high_price = Decimal(str(prices['high']))
                    if 'low' in prices:
                        market_data.low_price = Decimal(str(prices['low']))
                    if 'adj_close' in prices:
                        market_data.adjusted_price = Decimal(str(prices['adj_close']))
                    
                    price_history.append(market_data)
            
            # Set price history in domain entity (if it has such a method)
            if hasattr(domain_entity, 'set_price_history'):
                domain_entity.set_price_history(price_history)
                
        except Exception as e:
            print(f"Warning: Failed to load price history for share {domain_entity.ticker}: {str(e)}")
        
        return domain_entity

    @staticmethod
    def get_factor_summary(orm_obj: ORMCompanyShare, factor_repository: ShareFactorRepository) -> Dict[str, any]:
        """
        Get a summary of available factors for a company share.
        
        :param orm_obj: ORM CompanyShare model
        :param factor_repository: Repository for accessing share factors
        :return: Dictionary with factor summary information
        """
        try:
            # Get all factors related to this share
            factor_values = factor_repository.get_factor_values_by_entity(orm_obj.id)
            
            # Group by factor type
            factor_summary = {}
            factor_names = set()
            
            for fv in factor_values:
                factor_name = fv.factor.name
                factor_names.add(factor_name)
                
                if factor_name not in factor_summary:
                    factor_summary[factor_name] = {
                        'count': 0,
                        'first_date': fv.date,
                        'last_date': fv.date,
                        'min_value': float(fv.value),
                        'max_value': float(fv.value)
                    }
                else:
                    summary = factor_summary[factor_name]
                    summary['count'] += 1
                    summary['first_date'] = min(summary['first_date'], fv.date)
                    summary['last_date'] = max(summary['last_date'], fv.date)
                    summary['min_value'] = min(summary['min_value'], float(fv.value))
                    summary['max_value'] = max(summary['max_value'], float(fv.value))
            
            return {
                'ticker': orm_obj.ticker,
                'total_factors': len(factor_names),
                'total_data_points': len(factor_values),
                'factors': factor_summary
            }
            
        except Exception as e:
            print(f"Warning: Failed to get factor summary for share {orm_obj.ticker}: {str(e)}")
            return {'ticker': orm_obj.ticker, 'error': str(e)}


