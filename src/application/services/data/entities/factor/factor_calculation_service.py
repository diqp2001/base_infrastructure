"""
Factor Calculation Service - handles computation and storage of factor values.
Provides a service layer for calculating and storing factor calculations from domain entities.
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal
import pandas as pd

from src.domain.entities.factor.factor import Factor
from domain.entities.factor.factor_serie import FactorSerie
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

from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from application.services.database_service.database_service import DatabaseService


class FactorCalculationService:
    """Service for calculating factor values and storing them in the database."""
    
    def __init__(self, database_service: Optional[DatabaseService] = None, db_type: str = 'sqlite'):
        """
        Initialize the service with a database service or create one if not provided.
        
        Args:
            database_service: Optional existing DatabaseService instance
            db_type: Database type to use when creating new DatabaseService (ignored if database_service provided)
        """
        if database_service is not None:
            self.database_service = database_service
        else:
            self.database_service = DatabaseService(db_type)
        self.repository = BaseFactorRepository(self.database_service.session)
        self.share_factor_repository = ShareFactorRepository(db_type)
        self.company_share_repository = CompanyShareRepositoryLocal(self.database_service.session)
    
    # Entity Creation Functions
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
    
    def create_share_factor(
        self,
        name: str,
        group: str = "share",
        subgroup: str = "general",
        definition: str = None,
        equity_specific: str = None
    ) -> ShareFactor:
        """Create a ShareFactor entity."""
        return ShareFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"Share-specific factor: {name}",
            equity_specific=equity_specific
        )
    
    def create_country_factor(
        self,
        name: str,
        group: str = "geographic",
        subgroup: str = "country",
        definition: str = None
    ) -> CountryFactor:
        """Create a CountryFactor entity."""
        return CountryFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="external",
            definition=definition or f"Country-level factor: {name}"
        )
    
    def create_continent_factor(
        self,
        name: str,
        group: str = "geographic",
        subgroup: str = "continent",
        definition: str = None
    ) -> ContinentFactor:
        """Create a ContinentFactor entity."""
        return ContinentFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="external",
            definition=definition or f"Continent-level factor: {name}"
        )
    
    def create_security_factor(
        self,
        name: str,
        group: str = "security",
        subgroup: str = "general",
        definition: str = None
    ) -> SecurityFactor:
        """Create a SecurityFactor entity."""
        return SecurityFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"Security-level factor: {name}"
        )
    
    def create_equity_factor(
        self,
        name: str,
        group: str = "equity",
        subgroup: str = "general",
        definition: str = None
    ) -> EquityFactor:
        """Create an EquityFactor entity."""
        return EquityFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"Equity-level factor: {name}"
        )
    
    def create_financial_asset_factor(
        self,
        name: str,
        group: str = "financial_asset",
        subgroup: str = "general",
        definition: str = None
    ) -> FinancialAssetFactor:
        """Create a FinancialAssetFactor entity."""
        return FinancialAssetFactor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type="float",
            source="calculated",
            definition=definition or f"Financial asset factor: {name}"
        )
    
    def create_base_factor(
        self,
        name: str,
        group: str,
        subgroup: str = None,
        data_type: str = "float",
        source: str = "calculated",
        definition: str = None
    ) -> Factor:
        """Create a base Factor entity."""
        return Factor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition or f"Base factor: {name}"
        )
    
    def _extract_price_data_from_database(self, entity_id: int, ticker: str = None) -> Optional[FactorSerie]:
        """
        Extract price data from database and create PriceData domain object.
        
        Args:
            entity_id: ID of the entity (e.g., share ID)
            ticker: Optional ticker symbol for context
            
        Returns:
            PriceData domain object or None if no data found
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
            
            # Create PriceData domain object
            return FactorSerie(
                values=df["value"].tolist(),
                dates=df["date"].tolist(),
                ticker=ticker or f"entity_{entity_id}",
                entity_id=entity_id
            )
            
        except Exception as e:
            print(f"    ❌ Error extracting price data for entity_id {entity_id}: {str(e)}")
            return None

    # Existing calculation methods...
    def calculate_and_store_momentum(
        self, 
        factor: ShareMomentumFactor, 
        entity_id: int, 
        entity_type: str,
        ticker: str = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate momentum factor values and store them in the database.
        
        Price data is extracted from the database using the standardized PriceData domain object.
        This follows the pattern established in BaseFactorRepository._create_or_get_factor().
        
        Args:
            factor: ShareMomentumFactor domain entity
            entity_id: ID of the entity (e.g., share ID)
            entity_type: Type of entity ('share', 'equity', etc.)
            ticker: Optional ticker symbol for context and logging
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
        """
        # Extract price data from database
        price_data = self._extract_price_data_from_database(entity_id, ticker)
        if not price_data:
            return {
                'factor_name': factor.name,
                'factor_id': factor.id,
                'entity_id': entity_id,
                'entity_type': entity_type,
                'calculations': [],
                'stored_values': 0,
                'skipped_values': 0,
                'errors': ['No price data available in database']
            }
        
        results = {
            'factor_name': factor.name,
            'factor_id': factor.id,
            'entity_id': entity_id,
            'entity_type': entity_type,
            'calculations': [],
            'stored_values': 0,
            'skipped_values': 0,
            'errors': []
        }
        
        # Calculate momentum for each date using the PriceData domain object
        for i, (price_date, current_price) in enumerate(zip(price_data.dates, price_data.values)):
            try:
                # Get historical prices up to current date for momentum calculation
                historical_prices = price_data.get_historical_values(i + 1)
                
                # Calculate momentum using domain logic
                momentum_value = factor.calculate_momentum(historical_prices)
                
                if momentum_value is not None:
                    # Check if value already exists
                    if not overwrite and self.repository.factor_value_exists(
                        factor.id, entity_id, price_date
                    ):
                        results['skipped_values'] += 1
                        continue
                    
                    # Store the calculated value
                    factor_value = self.repository.add_factor_value(
                        factor_id=factor.id,
                        entity_id=entity_id,
                        date=price_date,
                        value=Decimal(str(momentum_value))
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
    
    def _calculate_momentum_legacy(
        self, 
        factor: ShareMomentumFactor, 
        entity_id: int, 
        entity_type: str,
        prices: List[float], 
        dates: List[date],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility.
        
        This method maintains the old interface while the new interface extracts 
        price data from the database using the PriceData domain object.
        """
        if len(prices) != len(dates):
            raise ValueError("Prices and dates lists must have the same length")
        
        results = {
            'factor_name': factor.name,
            'factor_id': factor.id,
            'entity_id': entity_id,
            'entity_type': entity_type,
            'calculations': [],
            'stored_values': 0,
            'skipped_values': 0,
            'errors': []
        }
        
        # Calculate momentum for each date (legacy approach)
        for i, (price_date, current_price) in enumerate(zip(dates, prices)):
            try:
                # Get historical prices up to current date for momentum calculation
                historical_prices = prices[:i+1]
                
                # Calculate momentum using domain logic
                momentum_value = factor.calculate_momentum(historical_prices)
                
                if momentum_value is not None:
                    # Check if value already exists
                    if not overwrite and self.repository.factor_value_exists(
                        factor.id, entity_id, price_date
                    ):
                        results['skipped_values'] += 1
                        continue
                    
                    # Store the calculated value
                    factor_value = self.repository.add_factor_value(
                        factor_id=factor.id,
                        entity_id=entity_id,
                        date=price_date,
                        value=Decimal(str(momentum_value))
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
    
    def calculate_and_store_technical(
        self,
        factor: ShareTechnicalFactor,
        entity_id: int,
        entity_type: str,
        data: pd.DataFrame,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate technical indicator values and store them in the database.
        
        Args:
            factor: ShareTechnicalFactor domain entity
            entity_id: ID of the entity
            entity_type: Type of entity
            data: DataFrame with OHLCV data (columns: open, high, low, close, volume)
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
        """
        results = {
            'factor_name': factor.name,
            'factor_id': factor.id,
            'entity_id': entity_id,
            'entity_type': entity_type,
            'calculations': [],
            'stored_values': 0,
            'skipped_values': 0,
            'errors': []
        }
        
        try:
            # Calculate technical indicators using domain logic
            if factor.indicator_type.upper() == 'SMA':
                values = factor.calculate_sma(data['close'].tolist())
            elif factor.indicator_type.upper() == 'EMA':
                values = factor.calculate_ema(data['close'].tolist())
            elif factor.indicator_type.upper() == 'RSI':
                values = factor.calculate_rsi(data['close'].tolist())
            else:
                results['errors'].append(f"Unknown indicator type: {factor.indicator_type}")
                return results
            
            # Store calculated values
            for i, (date_idx, value) in enumerate(zip(data.index, values)):
                try:
                    trade_date = date_idx.date() if hasattr(date_idx, 'date') else date_idx
                    
                    if value is not None:
                        # Check if value already exists
                        if not overwrite and self.repository.factor_value_exists(
                            factor.id, entity_id, trade_date
                        ):
                            results['skipped_values'] += 1
                            continue
                        
                        # Store the calculated value
                        factor_value = self.repository.add_factor_value(
                            factor_id=factor.id,
                            entity_id=entity_id,
                            date=trade_date,
                            value=Decimal(str(value))
                        )
                        
                        if factor_value:
                            results['stored_values'] += 1
                            results['calculations'].append({
                                'date': trade_date,
                                'value': value,
                                'stored': True
                            })
                        else:
                            results['errors'].append(f"Failed to store value for {trade_date}")
                    else:
                        results['calculations'].append({
                            'date': trade_date,
                            'value': None,
                            'stored': False,
                            'reason': 'Insufficient data for technical calculation'
                        })
                
                except Exception as e:
                    results['errors'].append(f"Error processing {trade_date}: {str(e)}")
            
        except Exception as e:
            results['errors'].append(f"Error calculating technical indicator: {str(e)}")
        
        return results
    
    def calculate_and_store_volatility(
        self,
        factor: ShareVolatilityFactor,
        entity_id: int,
        entity_type: str,
        returns: List[float],
        dates: List[date],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate volatility factor values and store them in the database.
        
        Args:
            factor: ShareVolatilityFactor domain entity
            entity_id: ID of the entity
            entity_type: Type of entity
            returns: List of return values
            dates: List of corresponding dates
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
        """
        if len(returns) != len(dates):
            raise ValueError("Returns and dates lists must have the same length")
        
        results = {
            'factor_name': factor.name,
            'factor_id': factor.id,
            'entity_id': entity_id,
            'entity_type': entity_type,
            'calculations': [],
            'stored_values': 0,
            'skipped_values': 0,
            'errors': []
        }
        
        # Calculate volatility for each date
        for i, (vol_date, current_return) in enumerate(zip(dates, returns)):
            try:
                # Get historical returns up to current date for volatility calculation
                historical_returns = returns[:i+1]
                
                # Calculate volatility using domain logic
                if factor.volatility_type == 'historical':
                    volatility_value = factor.calculate_historical_volatility(historical_returns)
                else:
                    volatility_value = factor.calculate_realized_volatility(historical_returns)
                
                if volatility_value is not None:
                    # Check if value already exists
                    if not overwrite and self.repository.factor_value_exists(
                        factor.id, entity_id, vol_date
                    ):
                        results['skipped_values'] += 1
                        continue
                    
                    # Store the calculated value
                    factor_value = self.repository.add_factor_value(
                        factor_id=factor.id,
                        entity_id=entity_id,
                        date=vol_date,
                        value=Decimal(str(volatility_value))
                    )
                    
                    if factor_value:
                        results['stored_values'] += 1
                        results['calculations'].append({
                            'date': vol_date,
                            'value': volatility_value,
                            'stored': True
                        })
                    else:
                        results['errors'].append(f"Failed to store value for {vol_date}")
                else:
                    results['calculations'].append({
                        'date': vol_date,
                        'value': None,
                        'stored': False,
                        'reason': 'Insufficient data for volatility calculation'
                    })
            
            except Exception as e:
                results['errors'].append(f"Error calculating volatility for {vol_date}: {str(e)}")
        
        return results
    
    def calculate_and_store_factor(
        self,
        factor: Factor,
        entity_id: int,
        entity_type: str,
        data: Any,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Generic method to calculate and store factor values based on factor type.
        
        Args:
            factor: Factor domain entity
            entity_id: ID of the entity
            entity_type: Type of entity
            data: Input data (format depends on factor type)
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
        """
        if isinstance(factor, ShareMomentumFactor):
            # Support both old and new calling patterns
            if isinstance(data, dict) and 'ticker' in data:
                # New pattern: extract from database using ticker
                return self.calculate_and_store_momentum(
                    factor, entity_id, entity_type, ticker=data['ticker'], overwrite=overwrite
                )
            elif isinstance(data, dict) and 'prices' in data and 'dates' in data:
                # Legacy pattern: prices provided directly (deprecated)
                print("⚠️  Warning: Direct price/dates input is deprecated. Use database extraction with ticker instead.")
                # Create backward-compatible call by temporarily modifying the method
                # This ensures existing code still works while encouraging migration to new pattern
                legacy_results = self._calculate_momentum_legacy(
                    factor, entity_id, entity_type, data['prices'], data['dates'], overwrite
                )
                return legacy_results
            elif data is None:
                # New pattern: extract from database without ticker context
                return self.calculate_and_store_momentum(
                    factor, entity_id, entity_type, ticker=None, overwrite=overwrite
                )
            else:
                raise ValueError("ShareMomentumFactor requires either {'ticker': str} for database extraction or legacy {'prices': List[float], 'dates': List[date]} format")
        
        elif isinstance(factor, ShareTechnicalFactor):
            if isinstance(data, pd.DataFrame):
                return self.calculate_and_store_technical(
                    factor, entity_id, entity_type, data, overwrite
                )
            else:
                raise ValueError("ShareTechnicalFactor requires pandas DataFrame with OHLCV data")
        
        elif isinstance(factor, ShareVolatilityFactor):
            if isinstance(data, dict) and 'returns' in data and 'dates' in data:
                return self.calculate_and_store_volatility(
                    factor, entity_id, entity_type, data['returns'], data['dates'], overwrite
                )
            else:
                raise ValueError("ShareVolatilityFactor requires data with 'returns' and 'dates' keys")
        
        else:
            return {
                'error': f"Unsupported factor type: {type(factor).__name__}",
                'factor_name': factor.name if hasattr(factor, 'name') else 'Unknown',
                'stored_values': 0,
                'errors': [f"No calculation method available for {type(factor).__name__}"]
            }
    
    def bulk_calculate_and_store(
        self,
        calculations: List[Dict[str, Any]],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Bulk calculate and store multiple factor values.
        
        Args:
            calculations: List of calculation dictionaries with keys:
                - 'factor': Factor domain entity
                - 'entity_id': Entity ID
                - 'entity_type': Entity type
                - 'data': Input data
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with aggregated results
        """
        results = {
            'total_calculations': len(calculations),
            'successful_calculations': 0,
            'failed_calculations': 0,
            'total_stored_values': 0,
            'total_skipped_values': 0,
            'calculation_details': [],
            'errors': []
        }
        
        for calc in calculations:
            try:
                calc_result = self.calculate_and_store_factor(
                    factor=calc['factor'],
                    entity_id=calc['entity_id'],
                    entity_type=calc['entity_type'],
                    data=calc['data'],
                    overwrite=overwrite
                )
                
                results['successful_calculations'] += 1
                results['total_stored_values'] += calc_result.get('stored_values', 0)
                results['total_skipped_values'] += calc_result.get('skipped_values', 0)
                results['calculation_details'].append(calc_result)
                
                if calc_result.get('errors'):
                    results['errors'].extend(calc_result['errors'])
            
            except Exception as e:
                results['failed_calculations'] += 1
                error_msg = f"Failed to calculate {calc.get('factor', {}).get('name', 'Unknown')}: {str(e)}"
                results['errors'].append(error_msg)
        
        return results
    
    # Cross-Factor Calculation Methods
    
    def calculate_factor_from_factors(
        self,
        source_factors: List[Dict[str, Any]],
        target_factor: Factor,
        entity_id: int,
        entity_type: str,
        calculation_function,
        dates: List[date],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate a new factor using values from existing factors.
        
        Args:
            source_factors: List of factor dictionaries with 'factor' and 'values' keys
            target_factor: Target factor domain entity to store results
            entity_id: ID of the entity
            entity_type: Type of entity
            calculation_function: Function that takes source factor values and returns calculated value
            dates: List of dates to calculate for
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
        """
        results = {
            'target_factor_name': target_factor.name,
            'target_factor_id': target_factor.id,
            'source_factors': [sf['factor'].name for sf in source_factors],
            'entity_id': entity_id,
            'entity_type': entity_type,
            'calculations': [],
            'stored_values': 0,
            'skipped_values': 0,
            'errors': []
        }
        
        # Calculate for each date
        for calc_date in dates:
            try:
                # Get source factor values for this date
                source_values = {}
                all_values_available = True
                
                for source_factor_info in source_factors:
                    factor = source_factor_info['factor']
                    value = self.repository.get_factor_value(
                        factor.id, entity_id, calc_date
                    )
                    
                    if value is None:
                        all_values_available = False
                        break
                    
                    source_values[factor.name] = float(value)
                
                if not all_values_available:
                    results['calculations'].append({
                        'date': calc_date,
                        'value': None,
                        'stored': False,
                        'reason': 'Missing source factor values'
                    })
                    continue
                
                # Apply calculation function
                calculated_value = calculation_function(source_values, calc_date)
                
                if calculated_value is not None:
                    # Check if value already exists
                    if not overwrite and self.repository.factor_value_exists(
                        target_factor.id, entity_id, calc_date
                    ):
                        results['skipped_values'] += 1
                        continue
                    
                    # Store the calculated value
                    factor_value = self.repository.add_factor_value(
                        factor_id=target_factor.id,
                        entity_id=entity_id,
                        date=calc_date,
                        value=Decimal(str(calculated_value))
                    )
                    
                    if factor_value:
                        results['stored_values'] += 1
                        results['calculations'].append({
                            'date': calc_date,
                            'value': calculated_value,
                            'stored': True,
                            'source_values': source_values
                        })
                    else:
                        results['errors'].append(f"Failed to store value for {calc_date}")
                else:
                    results['calculations'].append({
                        'date': calc_date,
                        'value': None,
                        'stored': False,
                        'reason': 'Calculation function returned None'
                    })
                    
            except Exception as e:
                results['errors'].append(f"Error processing {calc_date}: {str(e)}")
        
        return results
    
    def calculate_momentum_relative_strength(
        self,
        momentum_factor: ShareMomentumFactor,
        benchmark_momentum_factor: ShareMomentumFactor,
        target_factor: Factor,
        entity_id: int,
        entity_type: str,
        dates: List[date],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate relative strength by comparing momentum factor to benchmark momentum.
        
        Example of calculating new factors from existing factors.
        """
        def relative_strength_calc(source_values, calc_date):
            momentum_value = source_values.get(momentum_factor.name)
            benchmark_momentum = source_values.get(benchmark_momentum_factor.name)
            
            if momentum_value is not None and benchmark_momentum is not None and benchmark_momentum != 0:
                return momentum_value / benchmark_momentum - 1.0  # Relative performance
            return None
        
        source_factors = [
            {'factor': momentum_factor},
            {'factor': benchmark_momentum_factor}
        ]
        
        return self.calculate_factor_from_factors(
            source_factors=source_factors,
            target_factor=target_factor,
            entity_id=entity_id,
            entity_type=entity_type,
            calculation_function=relative_strength_calc,
            dates=dates,
            overwrite=overwrite
        )
    
    def calculate_volatility_adjusted_momentum(
        self,
        momentum_factor: ShareMomentumFactor,
        volatility_factor: ShareVolatilityFactor,
        target_factor: Factor,
        entity_id: int,
        entity_type: str,
        dates: List[date],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate volatility-adjusted momentum (momentum / volatility).
        
        Another example of calculating new factors from existing factors.
        """
        def vol_adjusted_momentum_calc(source_values, calc_date):
            momentum_value = source_values.get(momentum_factor.name)
            volatility_value = source_values.get(volatility_factor.name)
            
            if momentum_value is not None and volatility_value is not None and volatility_value > 0:
                return momentum_value / volatility_value  # Risk-adjusted momentum
            return None
        
        source_factors = [
            {'factor': momentum_factor},
            {'factor': volatility_factor}
        ]
        
        return self.calculate_factor_from_factors(
            source_factors=source_factors,
            target_factor=target_factor,
            entity_id=entity_id,
            entity_type=entity_type,
            calculation_function=vol_adjusted_momentum_calc,
            dates=dates,
            overwrite=overwrite
        )
    
    def calculate_composite_factor(
        self,
        factor_weights: Dict[Factor, float],
        target_factor: Factor,
        entity_id: int,
        entity_type: str,
        dates: List[date],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate a composite factor as weighted sum of multiple factors.
        
        Args:
            factor_weights: Dictionary mapping factors to their weights
            target_factor: Target composite factor
            entity_id: ID of the entity
            entity_type: Type of entity
            dates: List of dates to calculate for
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
        """
        def composite_calc(source_values, calc_date):
            weighted_sum = 0.0
            total_weight = 0.0
            
            for factor, weight in factor_weights.items():
                factor_value = source_values.get(factor.name)
                if factor_value is not None:
                    weighted_sum += factor_value * weight
                    total_weight += abs(weight)
            
            # Return weighted average if we have any valid values
            if total_weight > 0:
                return weighted_sum / total_weight
            return None
        
        source_factors = [{'factor': factor} for factor in factor_weights.keys()]
        
        return self.calculate_factor_from_factors(
            source_factors=source_factors,
            target_factor=target_factor,
            entity_id=entity_id,
            entity_type=entity_type,
            calculation_function=composite_calc,
            dates=dates,
            overwrite=overwrite
        )