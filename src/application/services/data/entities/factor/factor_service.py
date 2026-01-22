"""
Consolidated Factor Service - unified service layer for all factor operations.

This service consolidates functionality from:
- FactorCalculationService: Factor value calculation and storage
- FactorCreationService: Factor entity creation and management  
- FactorDataService: Factor data retrieval and storage operations

The service inherits from EntityService to maintain consistent repository initialization patterns.
It also includes functions from IBKR factor repositories in ibkr_repo\factor\finance directory.
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
import pandas as pd

# Domain entities
from src.application.services.data.entities.entity_service import EntityService
from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.factor_serie import FactorSerie
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_target_factor import ShareTargetFactor
from src.domain.entities.factor.country_factor import CountryFactor
from src.domain.entities.factor.continent_factor import ContinentFactor
from src.domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor
from src.domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor
from src.domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare

# Infrastructure repositories
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal

# IBKR repositories and types
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickType, IBKRTickFactorMapper

# Base service

from src.application.services.database_service.database_service import DatabaseService


class FactorService(EntityService):
    """
    Consolidated service for all factor operations.
    
    Inherits from EntityService for consistent repository initialization and management.
    Provides unified access to factor calculation, creation, and data operations.
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None, db_type: str = 'sqlite'):
        """
        Initialize the consolidated factor service.
        
        Args:
            database_service: Optional existing DatabaseService instance
            db_type: Database type to use when creating new DatabaseService
        """
        super().__init__(database_service, db_type)
        
        # # Initialize additional factor-specific repositories
        # self.base_factor_repository = self.local_repositories['base_factor']
        # self.share_factor_repository = self.local_repositories['share_factor']
        # self.company_share_repository = self.local_repositories['company_share']
        
        # Initialize tick mapper for IBKR operations
        # self.tick_mapper = IBKRTickFactorMapper()

    # ========================================
    # FACTOR CREATION METHODS (from FactorCreationService)
    # ========================================
    
    def create_share_momentum_factor(
        self,
        name: str,
        group: str = "momentum",
        subgroup: str = "price",
        definition: str = None,
        momentum_type: str = "price_momentum",
        period: int = 20
    ) -> ShareMomentumFactor:
        """Create a ShareMomentumFactor entity."""
        return ShareMomentumFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"{period}-period {momentum_type} momentum factor",
            momentum_type=momentum_type,
            period=period
        )
    
    def create_share_technical_factor(
        self,
        name: str,
        indicator_type: str = "SMA",
        period: int = 20,
        group: str = "technical",
        subgroup: str = "trend",
        definition: str = None
    ) -> ShareTechnicalFactor:
        """Create a ShareTechnicalFactor entity."""
        return ShareTechnicalFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"{period}-period {indicator_type} technical indicator",
            indicator_type=indicator_type,
            period=period
        )
    
    def create_share_volatility_factor(
        self,
        name: str,
        volatility_type: str = "historical",
        period: int = 30,
        annualization_factor: float = 252.0,
        group: str = "volatility",
        subgroup: str = "risk",
        definition: str = None
    ) -> ShareVolatilityFactor:
        """Create a ShareVolatilityFactor entity."""
        return ShareVolatilityFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"{period}-period {volatility_type} volatility factor",
            volatility_type=volatility_type,
            period=period,
            annualization_factor=annualization_factor
        )
    
    def create_share_target_factor(
        self,
        name: str,
        target_type: str = "returns",
        forecast_horizon: int = 1,
        is_scaled: bool = False,
        group: str = "target",
        subgroup: str = "prediction",
        definition: str = None
    ) -> ShareTargetFactor:
        """Create a ShareTargetFactor entity."""
        return ShareTargetFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"{forecast_horizon}-period {target_type} target factor",
            target_type=target_type,
            forecast_horizon=forecast_horizon,
            is_scaled=is_scaled
        )
    
    def create_factor_from_config(self, config: Dict[str, Any]) -> Factor:
        """
        Create a factor entity from a configuration dictionary.
        
        Args:
            config: Dictionary with factor configuration
                Required keys: 'factor_type', 'name'
                Optional keys: varies by factor type
                
        Returns:
            Factor entity instance
        """
        factor_type = config.get('factor_type', '').lower()
        
        if factor_type == 'share_momentum':
            return self.create_share_momentum_factor(
                name=config['name'],
                group=config.get('group', 'momentum'),
                subgroup=config.get('subgroup', 'price'),
                definition=config.get('definition'),
                momentum_type=config.get('momentum_type', 'price_momentum'),
                period=config.get('period', 20)
            )
        elif factor_type == 'share_technical':
            return self.create_share_technical_factor(
                name=config['name'],
                indicator_type=config.get('indicator_type', 'SMA'),
                period=config.get('period', 20),
                group=config.get('group', 'technical'),
                subgroup=config.get('subgroup', 'trend'),
                definition=config.get('definition')
            )
        elif factor_type == 'share_volatility':
            return self.create_share_volatility_factor(
                name=config['name'],
                volatility_type=config.get('volatility_type', 'historical'),
                period=config.get('period', 30),
                annualization_factor=config.get('annualization_factor', 252.0),
                group=config.get('group', 'volatility'),
                subgroup=config.get('subgroup', 'risk'),
                definition=config.get('definition')
            )
        elif factor_type == 'share_target':
            return self.create_share_target_factor(
                name=config['name'],
                target_type=config.get('target_type', 'returns'),
                forecast_horizon=config.get('forecast_horizon', 1),
                is_scaled=config.get('is_scaled', False),
                group=config.get('group', 'target'),
                subgroup=config.get('subgroup', 'prediction'),
                definition=config.get('definition')
            )
        else:
            # Create base factor
            return Factor(
                name=config['name'],
                group=config.get('group', 'general'),
                subgroup=config.get('subgroup'),
                data_type=config.get('data_type', 'float'),
                source=config.get('source', 'calculated'),
                definition=config.get('definition') or f"Base factor: {config['name']}"
            )
    
    def persist_factor(self, factor: Factor) -> Optional[Factor]:
        """
        Persist a factor entity to the database.
        
        Args:
            factor: Factor entity to persist
            
        Returns:
            Persisted factor entity or None if failed
        """
        try:
            return self.base_factor_repository.add_factor(factor)
        except Exception as e:
            print(f"Error persisting factor {factor.name}: {str(e)}")
            return None
    
    def get_or_create_factor(self, config: Dict[str, Any]) -> Optional[Factor]:
        """
        Get existing factor by name or create new one if not found.
        
        Args:
            config: Factor configuration dictionary (must include 'name')
            
        Returns:
            Existing or newly created factor entity
        """
        factor_name = config.get('name')
        if not factor_name:
            return None
        
        # Try to get existing factor first
        existing_factor = self.get_factor_by_name(factor_name)
        if existing_factor:
            return existing_factor
        
        # Create new factor if not found
        factor = self.create_factor_from_config(config)
        return self.persist_factor(factor)

    # ========================================
    # FACTOR DATA METHODS (from FactorDataService)
    # ========================================
    
    def get_company_share_by_ticker(self, ticker: str) -> Optional[CompanyShare]:
        """Get company share entity by ticker."""
        try:
            shares = self.company_share_repository.get_by_ticker(ticker)
            return shares[0] if shares else None
        except Exception as e:
            print(f"Error getting company share by ticker {ticker}: {str(e)}")
            return None
    
    def create_or_get_factor_db(self, name: str, group: str, subgroup: str, 
                            data_type: str, source: str, definition: str) -> Optional[Factor]:
        """Create or get factor using the standardized repository pattern."""
        try:
            return self.base_factor_repository._create_or_get(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type=data_type,
                source=source,
                definition=definition
            )
        except Exception as e:
            print(f"Error creating/getting factor {name}: {str(e)}")
            return None
    
    def get_factor_by_name(self, name: str) -> Optional[Factor]:
        """Get factor entity by name."""
        try:
            return self.share_factor_repository.get_by_name(name)
        except Exception as e:
            print(f"Error getting factor by name {name}: {str(e)}")
            return None
    
    def get_factors_by_groups(self, groups: List[str]) -> List[Factor]:
        """Get factors by groups."""
        try:
            return self.share_factor_repository.get_factors_by_groups(groups)
        except Exception as e:
            print(f"Error getting factors by groups {groups}: {str(e)}")
            return []
    
    def store_factor_values(self, factor: Factor, entity: object, 
                           data: pd.DataFrame, column: str, overwrite: bool = False) -> int:
        """Store factor values """
        
        try:
            self.repository = self.local_repositories.get(object)
            return self.repository._store_factor_values(
                factor, entity, data, column, overwrite
            )
        except Exception as e:
            print(f"Error storing factor values for {factor.name}: {str(e)}")
            return 0
    
    def get_factor_values_df(self, factor_id: int, entity_id: int) -> pd.DataFrame:
        """Get factor values as DataFrame for a specific factor and entity."""
        try:
            return self.share_factor_repository.get_factor_values_df(
                factor_id=factor_id, 
                entity_id=entity_id
            )
        except Exception as e:
            print(f"Error getting factor values DataFrame for factor {factor_id}: {str(e)}")
            return pd.DataFrame()

    # ========================================
    # FACTOR CALCULATION METHODS (from FactorCalculationService)
    # ========================================
    
    @staticmethod
    def _get_entity_type_from_factor(factor) -> str:
        """
        Determine entity_type from factor type.
        """
        factor_class_name = factor.__class__.__name__
        
        if any(share_type in factor_class_name for share_type in ['Share', 'share']):
            return 'share'
        elif any(equity_type in factor_class_name for equity_type in ['Equity', 'equity']):
            return 'equity'
        elif any(country_type in factor_class_name for country_type in ['Country', 'country']):
            return 'country'
        elif any(continent_type in factor_class_name for continent_type in ['Continent', 'continent']):
            return 'continent'
        else:
            return 'share'  # Default fallback
    
    def _extract_price_data_from_database(self, entity_id: int, ticker: str = None) -> Optional[FactorSerie]:
        """
        Extract price data from database and create FactorSerie domain object.
        
        Args:
            entity_id: ID of the entity (e.g., share ID)
            ticker: Optional ticker symbol for context
            
        Returns:
            FactorSerie domain object or None if no data found
        """
        try:
            # Get the 'Close' price factor from database
            close_factor = self.share_factor_repository.get_by_name('Close')
            if not close_factor:
                print(f"    ⚠️  'Close' price factor not found in database")
                return None
            
            # Get factor values as DataFrame
            df = self.share_factor_repository.get_factor_values_df(
                factor_id=int(close_factor.id), 
                entity_id=entity_id
            )
            
            if df.empty:
                print(f"    ⚠️  No price data found for entity_id: {entity_id}")
                return None
            
            # Convert and clean data
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["value"] = df["value"].astype(float)
            df = df.sort_values("date")
            
            # Create FactorSerie domain object
            return FactorSerie(
                values=df["value"].tolist(),
                dates=df["date"].tolist(),
                ticker=ticker or f"entity_{entity_id}",
                entity_id=entity_id
            )
            
        except Exception as e:
            print(f"    ❌ Error extracting price data for entity_id {entity_id}: {str(e)}")
            return None

    def calculate_and_store_momentum(
        self, 
        factor: ShareMomentumFactor, 
        entity_id: int, 
        ticker: str = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """Calculate momentum factor values and store them in the database."""
        entity_type = self._get_entity_type_from_factor(factor)
        
        price_data = self._extract_price_data_from_database(entity_id, ticker)
        if not price_data:
            return {
                'factor_name': factor.name,
                'factor_id': factor.factor_id,
                'entity_id': entity_id,
                'entity_type': entity_type,
                'calculations': [],
                'stored_values': 0,
                'skipped_values': 0,
                'errors': ['No price data available in database']
            }
        
        results = {
            'factor_name': factor.name,
            'factor_id': factor.factor_id,
            'entity_id': entity_id,
            'entity_type': entity_type,
            'calculations': [],
            'stored_values': 0,
            'skipped_values': 0,
            'errors': []
        }
        
        # Calculate momentum for each date
        for i, (price_date, current_price) in enumerate(zip(price_data.dates, price_data.values)):
            try:
                # Get historical dates and values within the factor's period delta
                historical_dates, historical_prices = price_data.get_historical_dates_and_values(
                    current_date=price_date, 
                    period_delta=factor.period
                )
                
                # Calculate momentum using date-aware domain logic
                momentum_value = factor.calculate_momentum_with_dates(
                    historical_prices, 
                    historical_dates, 
                    price_date
                )
                
                if momentum_value is not None:
                    # Check if value already exists
                    if not overwrite and self.base_factor_repository.factor_value_exists(
                        factor.factor_id, entity_id, price_date
                    ):
                        results['skipped_values'] += 1
                        continue
                    
                    # Store the calculated value
                    factor_value = self.base_factor_repository.add_factor_value(
                        factor_id=factor.factor_id,
                        entity_id=entity_id,
                        date=price_date,
                        value=str(momentum_value)
                    )
                    
                    if factor_value:
                        results['stored_values'] += 1
                        results['calculations'].append({
                            'date': price_date,
                            'value': momentum_value,
                            'stored': True
                        })
                    else:
                        results['errors'].append(f"Failed to store value for {price_date}")
                else:
                    results['calculations'].append({
                        'date': price_date,
                        'value': None,
                        'stored': False,
                        'reason': 'Insufficient data for momentum calculation'
                    })
            
            except Exception as e:
                results['errors'].append(f"Error calculating momentum for {price_date}: {str(e)}")
        
        return results

    # ========================================
    # IBKR FACTOR REPOSITORY METHODS
    # ========================================
    
    def get_or_create_factor_from_tick_type(self, tick_type: IBKRTickType, contract_data: Optional[Dict[str, Any]] = None) -> Optional[Factor]:
        """
        Get or create a factor from IBKR tick type.
        
        This method creates factors based on IBKR tick types (e.g., Volume, Last Price)
        using the IBKR tick mapping system.
        
        Args:
            tick_type: IBKR tick type enum (e.g., IBKRTickType.VOLUME)
            contract_data: Optional contract details from IBKR API
            
        Returns:
            Factor entity from database or newly created
        """
        try:
            # Get factor mapping configuration from IBKR tick type
            factor_mapping = self.tick_mapper.get_factor_mapping(tick_type)
            if not factor_mapping:
                print(f"No factor mapping found for tick type {tick_type}")
                return None
            
            # Check if factor already exists by name
            existing_factor = self.get_factor_by_name(factor_mapping.factor_name)
            if existing_factor:
                return existing_factor
            
            # Create new factor from IBKR tick mapping
            new_factor = Factor(
                name=factor_mapping.factor_name,
                group=factor_mapping.factor_group,
                subgroup=factor_mapping.factor_subgroup,
                data_type=factor_mapping.data_type,
                source="IBKR",
                definition=f"{factor_mapping.description} (IBKR Tick Type {tick_type.value})"
            )
            
            # Add additional metadata from contract data if available
            if contract_data:
                if 'symbol' in contract_data:
                    new_factor.definition += f" - Symbol: {contract_data['symbol']}"
                if 'exchange' in contract_data:
                    new_factor.definition += f" - Exchange: {contract_data['exchange']}"
            
            # Persist to local database
            created_factor = self.persist_factor(new_factor)
            if created_factor:
                print(f"Created new factor: {created_factor.name} (ID: {created_factor.id})")
                return created_factor
            else:
                print(f"Failed to create factor: {factor_mapping.factor_name}")
                return None
                
        except Exception as e:
            print(f"Error in get_or_create_factor_from_tick_type for tick type {tick_type}: {e}")
            return None
    
    def create_factor_from_volume_data(self, symbol: str, volume_value: int) -> Optional[Factor]:
        """
        Convenience method to create Volume factor from IBKR volume data.
        
        Args:
            symbol: Stock symbol
            volume_value: Volume value from IBKR
            
        Returns:
            Volume Factor entity
        """
        contract_data = {'symbol': symbol, 'volume': volume_value}
        return self.get_or_create_factor_from_tick_type(IBKRTickType.VOLUME, contract_data)
    
    def create_factor_from_price_data(self, symbol: str, price_type: str = "LAST") -> Optional[Factor]:
        """
        Convenience method to create Price factors from IBKR price data.
        
        Args:
            symbol: Stock symbol
            price_type: Type of price (LAST, BID, ASK, CLOSE, etc.)
            
        Returns:
            Price Factor entity
        """
        tick_type_map = {
            "LAST": IBKRTickType.LAST_PRICE,
            "BID": IBKRTickType.BID_PRICE,
            "ASK": IBKRTickType.ASK_PRICE,
            "CLOSE": IBKRTickType.CLOSE_PRICE,
            "HIGH": IBKRTickType.HIGH,
            "LOW": IBKRTickType.LOW,
            "OPEN": IBKRTickType.OPEN_TICK
        }
        
        tick_type = tick_type_map.get(price_type.upper())
        if not tick_type:
            print(f"Unsupported price type: {price_type}")
            return None
            
        contract_data = {'symbol': symbol, 'price_type': price_type}
        return self.get_or_create_factor_from_tick_type(tick_type, contract_data)

    # ========================================
    # IBKR FACTOR VALUE REPOSITORY METHODS
    # ========================================
    
    def get_or_create_factor_value_with_ticks(
        self, 
        symbol_or_name: str, 
        factor_id: int, 
        time: str,
        tick_data: Optional[Dict[int, Any]] = None
    ) -> Optional[FactorValue]:
        """
        Get or create a factor value for a financial asset by symbol using IBKR API with instrument flow.
        
        This method follows the new architecture:
        1. Create IBKR Contract → Instrument
        2. Extract tick data → Factor Values 
        3. Map Instrument Factor Values → Financial Asset Factor Values
        
        Args:
            symbol_or_name: Stock symbol or asset name
            factor_id: The factor ID (integer)
            time: Date string in 'YYYY-MM-DD' format
            tick_data: Optional IBKR tick data dictionary (tick_type_id -> value)
            
        Returns:
            FactorValue entity or None if creation/retrieval failed
        """
        try:
            if not self._validate_factor_value_data(factor_id, 1, time):
                return None

            # For now, use IBKR repositories from EntityService
            if not hasattr(self, 'ibkr_repositories') or not self.ibkr_repositories:
                self.create_ibkr_repositories()
                
            factor_value_repo = self.ibkr_repositories.get('factor_value')
            if not factor_value_repo:
                print("IBKR factor value repository not available")
                return None
            
            # Delegate to IBKR repository
            return factor_value_repo.get_or_create_factor_value_with_ticks(
                symbol_or_name, factor_id, time, tick_data
            )
            
        except Exception as e:
            print(f"Error in get_or_create_factor_value_with_ticks for {symbol_or_name}: {e}")
            return None
            
    def _validate_factor_value_data(self, factor_id: int, entity_id: int, time: str) -> bool:
        """
        Validate factor value creation parameters.
        
        Args:
            factor_id: The factor ID
            entity_id: The entity ID
            time: Date string in 'YYYY-MM-DD' format
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(factor_id, int) or factor_id <= 0:
                print(f"Invalid factor_id: {factor_id}")
                return False
                
            if not isinstance(entity_id, int) or entity_id <= 0:
                print(f"Invalid entity_id: {entity_id}")
                return False
                
            # Validate date format
            datetime.strptime(time, '%Y-%m-%d')
            return True
            
        except ValueError:
            print(f"Invalid date format: {time}")
            return False
        except Exception as e:
            print(f"Validation error: {e}")
            return False

    # ========================================
    # CONVENIENCE METHODS
    # ========================================
    
    def get_close_price_factor(self) -> Optional[Factor]:
        """Get the Close price factor."""
        return self.get_factor_by_name('Close')
    
    def get_price_factors(self) -> List[Factor]:
        """Get all price-related factors."""
        price_factor_names = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        factors = []
        for name in price_factor_names:
            factor = self.get_factor_by_name(name)
            if factor:
                factors.append(factor)
        return factors
    
    def validate_ticker_and_factor_existence(self, ticker: str, factor_name: str) -> bool:
        """
        Validate that both ticker and factor exist in the database.
        
        Args:
            ticker: Stock ticker to validate
            factor_name: Factor name to validate
            
        Returns:
            True if both exist, False otherwise
        """
        share = self.get_company_share_by_ticker(ticker)
        factor = self.get_factor_by_name(factor_name)
        return share is not None and factor is not None