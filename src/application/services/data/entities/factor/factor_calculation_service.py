"""
Factor Calculation Service - handles computation and storage of factor values.
Provides a service layer for calculating and storing factor calculations from domain entities.
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
import pandas as pd

from application.services.database_service.database_service import DatabaseService
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

from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal



class FactorCalculationService:
    """Service for calculating factor values and storing them in the database."""
    
    @staticmethod
    def _get_entity_type_from_factor(factor) -> str:
        """
        Determine entity_type from factor type.
        Since entity_type moved to FactorModel, derive it from factor class type.
        """
        factor_class_name = factor.__class__.__name__
        
        # Map factor types to entity types
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
        self.share_factor_repository = ShareFactorRepository(self.database_service.session)
        self.company_share_repository = CompanyShareRepositoryLocal(self.database_service.session)
    
    # NOTE: Factor creation methods have been moved to FactorCreationService
    # This service is now focused on factor value calculation and storage only
    
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
            ticker: Optional ticker symbol for context and logging
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
        """
        # Determine entity_type from factor type
        entity_type = self._get_entity_type_from_factor(factor)
        
        # Extract price data from database
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
        
        # Calculate momentum for each date using the PriceData domain object with date awareness
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
                    if not overwrite and self.repository.factor_value_exists(
                        factor.factor_id, entity_id, price_date
                    ):
                        results['skipped_values'] += 1
                        continue
                    
                    # Store the calculated value
                    factor_value = self.repository.add_factor_value(
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
    
    def _calculate_momentum_legacy(
        self, 
        factor: ShareMomentumFactor, 
        entity_id: int, 
        prices: List[float], 
        dates: List[date],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility.
        
        This method maintains the old interface while the new interface extracts 
        price data from the database using the PriceData domain object.
        """
        # Determine entity_type from factor type
        entity_type = self._get_entity_type_from_factor(factor)
        
        if len(prices) != len(dates):
            raise ValueError("Prices and dates lists must have the same length")
        
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
                        factor.factor_id, entity_id, price_date
                    ):
                        results['skipped_values'] += 1
                        continue
                    
                    # Store the calculated value
                    factor_value = self.repository.add_factor_value(
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
    
    def calculate_and_store_technical(
        self,
        factor: ShareTechnicalFactor,
        entity_id: int,
        ticker: str = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate technical indicator values and store them in the database.
        
        Price data is extracted from the database using the FactorSerie domain entity.
        This follows the same pattern as calculate_and_store_momentum.
        
        Args:
            factor: ShareTechnicalFactor domain entity
            entity_id: ID of the entity (e.g., share ID)
            ticker: Optional ticker symbol for context and logging
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
        """
        # Determine entity_type from factor type
        entity_type = self._get_entity_type_from_factor(factor)
        # Extract price data from database using FactorSerie
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
        
        # Calculate technical indicators for each date using the FactorSerie domain object
        for i, (price_date, current_price) in enumerate(zip(price_data.dates, price_data.values)):
            try:
                # Get historical prices up to current date for technical calculation
                historical_prices = price_data.get_historical_values(i + 1)
                
                # Calculate technical indicator using domain logic
                technical_value = None
                if factor.indicator_type.upper() == 'SMA':
                    technical_value = factor.calculate_sma(historical_prices)
                elif factor.indicator_type.upper() == 'EMA':
                    # For EMA, we need the previous EMA value - simplified for now
                    technical_value = factor.calculate_ema(historical_prices)
                elif factor.indicator_type.upper() == 'RSI':
                    technical_value = factor.calculate_rsi(historical_prices)
                else:
                    results['errors'].append(f"Unknown indicator type: {factor.indicator_type}")
                    continue
                
                if technical_value is not None:
                    # Check if value already exists
                    if not overwrite and self.repository.factor_value_exists(
                        factor.factor_id, entity_id, price_date
                    ):
                        results['skipped_values'] += 1
                        continue
                    
                    # Store the calculated value
                    factor_value = self.repository.add_factor_value(
                        factor_id=factor.factor_id,
                        entity_id=entity_id,
                        date=price_date,
                        value=str(technical_value)
                    )
                    
                    if factor_value:
                        results['stored_values'] += 1
                        results['calculations'].append({
                            'date': price_date,
                            'value': technical_value,
                            'stored': True
                        })
                    else:
                        results['errors'].append(f"Failed to store value for {price_date}")
                else:
                    results['calculations'].append({
                        'date': price_date,
                        'value': None,
                        'stored': False,
                        'reason': 'Insufficient data for technical calculation'
                    })
            
            except Exception as e:
                results['errors'].append(f"Error calculating technical indicator for {price_date}: {str(e)}")
        
        return results
    
    def _calculate_technical_legacy(
        self,
        factor: ShareTechnicalFactor,
        entity_id: int,
        data: pd.DataFrame,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility with DataFrame input.
        
        This method maintains the old interface while encouraging migration to 
        the new FactorSerie-based approach.
        """
        # Determine entity_type from factor type
        entity_type = self._get_entity_type_from_factor(factor)
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
        
        try:
            # Calculate technical indicators using domain logic on DataFrame data
            prices = data['close'].tolist()
            dates = [idx.date() if hasattr(idx, 'date') else idx for idx in data.index]
            
            # Calculate for each date
            for i, (trade_date, current_price) in enumerate(zip(dates, prices)):
                try:
                    # Get historical prices up to current date
                    historical_prices = prices[:i+1]
                    
                    # Calculate technical indicator using domain logic
                    technical_value = None
                    if factor.indicator_type.upper() == 'SMA':
                        technical_value = factor.calculate_sma(historical_prices)
                    elif factor.indicator_type.upper() == 'EMA':
                        technical_value = factor.calculate_ema(historical_prices)
                    elif factor.indicator_type.upper() == 'RSI':
                        technical_value = factor.calculate_rsi(historical_prices)
                    else:
                        results['errors'].append(f"Unknown indicator type: {factor.indicator_type}")
                        continue
                    
                    if technical_value is not None:
                        # Check if value already exists
                        if not overwrite and self.repository.factor_value_exists(
                            factor.factor_id, entity_id, trade_date
                        ):
                            results['skipped_values'] += 1
                            continue
                        
                        # Store the calculated value
                        factor_value = self.repository.add_factor_value(
                            factor_id=factor.factor_id,
                            entity_id=entity_id,
                            date=trade_date,
                            value=str(technical_value)
                        )
                        
                        if factor_value:
                            results['stored_values'] += 1
                            results['calculations'].append({
                                'date': trade_date,
                                'value': technical_value,
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
        ticker: str = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate volatility factor values and store them in the database.
        
        Price data is extracted from the database using the FactorSerie domain entity.
        This follows the same pattern as calculate_and_store_momentum and calculate_and_store_technical.
        
        Args:
            factor: ShareVolatilityFactor domain entity
            entity_id: ID of the entity (e.g., share ID)
            ticker: Optional ticker symbol for context and logging
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
        """
        # Determine entity_type from factor type
        entity_type = self._get_entity_type_from_factor(factor)
        # Extract price data from database using FactorSerie
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
        
        # Calculate volatility for each date using the FactorSerie domain object
        for i, (price_date, current_price) in enumerate(zip(price_data.dates, price_data.values)):
            try:
                # Get historical prices up to current date for volatility calculation
                historical_prices = price_data.get_historical_values(i + 1)
                
                # Calculate volatility using domain logic
                volatility_value = None
                if factor.volatility_type == 'historical':
                    volatility_value = factor.calculate_historical_volatility(historical_prices)
                elif factor.volatility_type == 'realized':
                    # For realized volatility, we need returns, not prices
                    # Convert prices to returns first
                    if len(historical_prices) >= 2:
                        returns = []
                        for j in range(1, len(historical_prices)):
                            if historical_prices[j-1] > 0:
                                returns.append((historical_prices[j] / historical_prices[j-1]) - 1)
                        volatility_value = factor.calculate_realized_volatility(returns)
                else:
                    results['errors'].append(f"Unknown volatility type: {factor.volatility_type}")
                    continue
                
                if volatility_value is not None:
                    # Check if value already exists
                    if not overwrite and self.repository.factor_value_exists(
                        factor.factor_id, entity_id, price_date
                    ):
                        results['skipped_values'] += 1
                        continue
                    
                    # Store the calculated value
                    factor_value = self.repository.add_factor_value(
                        factor_id=factor.factor_id,
                        entity_id=entity_id,
                        date=price_date,
                        value=str(volatility_value)
                    )
                    
                    if factor_value:
                        results['stored_values'] += 1
                        results['calculations'].append({
                            'date': price_date,
                            'value': volatility_value,
                            'stored': True
                        })
                    else:
                        results['errors'].append(f"Failed to store value for {price_date}")
                else:
                    results['calculations'].append({
                        'date': price_date,
                        'value': None,
                        'stored': False,
                        'reason': 'Insufficient data for volatility calculation'
                    })
            
            except Exception as e:
                results['errors'].append(f"Error calculating volatility for {price_date}: {str(e)}")
        
        return results
    
    def _calculate_volatility_legacy(
        self,
        factor: ShareVolatilityFactor,
        entity_id: int,
        returns: List[float],
        dates: List[date],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility with direct returns/dates input.
        
        This method maintains the old interface while encouraging migration to 
        the new FactorSerie-based approach.
        """
        # Determine entity_type from factor type
        entity_type = self._get_entity_type_from_factor(factor)
        
        if len(returns) != len(dates):
            raise ValueError("Returns and dates lists must have the same length")
        
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
        
        # Calculate volatility for each date (legacy approach)
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
                        factor.factor_id, entity_id, vol_date
                    ):
                        results['skipped_values'] += 1
                        continue
                    
                    # Store the calculated value
                    factor_value = self.repository.add_factor_value(
                        factor_id=factor.factor_id,
                        entity_id=entity_id,
                        date=vol_date,
                        value=str(volatility_value)
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
        data: Any,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Generic method to calculate and store factor values based on factor type.
        
        Args:
            factor: Factor domain entity
            entity_id: ID of the entity
            data: Input data (format depends on factor type)
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
        """
        # Determine entity_type from factor type
        entity_type = self._get_entity_type_from_factor(factor)
        if isinstance(factor, ShareMomentumFactor):
            # Support both old and new calling patterns
            if isinstance(data, dict) and 'ticker' in data:
                # New pattern: extract from database using ticker
                return self.calculate_and_store_momentum(
                    factor, entity_id, ticker=data['ticker'], overwrite=overwrite
                )
            elif isinstance(data, dict) and 'prices' in data and 'dates' in data:
                # Legacy pattern: prices provided directly (deprecated)
                print("⚠️  Warning: Direct price/dates input is deprecated. Use database extraction with ticker instead.")
                # Create backward-compatible call by temporarily modifying the method
                # This ensures existing code still works while encouraging migration to new pattern
                legacy_results = self._calculate_momentum_legacy(
                    factor, entity_id, data['prices'], data['dates'], overwrite
                )
                return legacy_results
            elif data is None:
                # New pattern: extract from database without ticker context
                return self.calculate_and_store_momentum(
                    factor, entity_id, ticker=None, overwrite=overwrite
                )
            else:
                raise ValueError("ShareMomentumFactor requires either {'ticker': str} for database extraction or legacy {'prices': List[float], 'dates': List[date]} format")
        
        elif isinstance(factor, ShareTechnicalFactor):
            # Support both new and legacy calling patterns
            if isinstance(data, dict) and 'ticker' in data:
                # New pattern: extract from database using ticker
                return self.calculate_and_store_technical(
                    factor, entity_id, ticker=data['ticker'], overwrite=overwrite
                )
            elif isinstance(data, pd.DataFrame):
                # Legacy pattern: DataFrame provided directly (deprecated)
                print("⚠️  Warning: Direct DataFrame input is deprecated. Use database extraction with ticker instead.")
                return self._calculate_technical_legacy(
                    factor, entity_id, data, overwrite
                )
            elif data is None:
                # New pattern: extract from database without ticker context
                return self.calculate_and_store_technical(
                    factor, entity_id, ticker=None, overwrite=overwrite
                )
            else:
                raise ValueError("ShareTechnicalFactor requires either {'ticker': str} for database extraction or legacy pandas DataFrame format")
        
        elif isinstance(factor, ShareVolatilityFactor):
            # Support both new and legacy calling patterns
            if isinstance(data, dict) and 'ticker' in data:
                # New pattern: extract from database using ticker
                return self.calculate_and_store_volatility(
                    factor, entity_id, ticker=data['ticker'], overwrite=overwrite
                )
            elif isinstance(data, dict) and 'returns' in data and 'dates' in data:
                # Legacy pattern: returns/dates provided directly (deprecated)
                print("⚠️  Warning: Direct returns/dates input is deprecated. Use database extraction with ticker instead.")
                return self._calculate_volatility_legacy(
                    factor, entity_id, data['returns'], data['dates'], overwrite
                )
            elif data is None:
                # New pattern: extract from database without ticker context
                return self.calculate_and_store_volatility(
                    factor, entity_id, ticker=None, overwrite=overwrite
                )
            else:
                raise ValueError("ShareVolatilityFactor requires either {'ticker': str} for database extraction or legacy {'returns': List[float], 'dates': List[date]} format")
        
        elif isinstance(factor, ShareTargetFactor):
            # Target factor calculation - supports different calling patterns
            if isinstance(data, dict) and 'prices' in data:
                # Direct prices provided
                return self.calculate_and_store_target(
                    factor, entity_id, prices=data['prices'], dates=data.get('dates'), overwrite=overwrite
                )
            elif isinstance(data, dict) and 'ticker' in data:
                # Extract from database using ticker
                return self.calculate_and_store_target(
                    factor, entity_id, ticker=data['ticker'], overwrite=overwrite
                )
            elif data is None:
                # Extract from database without ticker context
                return self.calculate_and_store_target(
                    factor, entity_id, ticker=None, overwrite=overwrite
                )
            else:
                raise ValueError("ShareTargetFactor requires either {'prices': List[float], 'dates': List[date]} or {'ticker': str} format")
        
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
            'target_factor_id': target_factor.factor_id,
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
                        factor.factor_id, entity_id, calc_date
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
                        target_factor.factor_id, entity_id, calc_date
                    ):
                        results['skipped_values'] += 1
                        continue
                    
                    # Store the calculated value
                    factor_value = self.repository.add_factor_value(
                        factor_id=target_factor.factor_id,
                        entity_id=entity_id,
                        date=calc_date,
                        value=str(calculated_value)
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
    
    def calculate_and_store_target(
        self,
        factor: ShareTargetFactor,
        entity_id: int,
        prices: Optional[List[float]] = None,
        dates: Optional[List] = None,
        ticker: Optional[str] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate and store target factor values (returns or price directions).
        
        Args:
            factor: ShareTargetFactor domain entity
            entity_id: ID of the entity
            prices: List of price values (if provided directly)
            dates: List of corresponding dates (if provided directly)
            ticker: Ticker symbol to extract price data from database
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
        """
        try:
            # Extract price data if not provided
            if prices is None:
                if ticker:
                    # Extract from database using ticker - implement extraction logic
                    print(f"⚠️  Database extraction for target factors not implemented for ticker: {ticker}")
                    return {
                        'error': f"Database extraction not implemented for target factors",
                        'factor_name': factor.name,
                        'stored_values': 0,
                        'errors': ['Database extraction for target factors not yet implemented']
                    }
                else:
                    return {
                        'error': f"No price data provided for target factor calculation",
                        'factor_name': factor.name,
                        'stored_values': 0,
                        'errors': ['No prices or ticker provided for target calculation']
                    }
            
            # Calculate target values using the provided calculation logic
            target_values = self.calculate_target_values(
                factor=factor,
                prices=prices,
                forecast_horizon=factor.forecast_horizon,
                is_scaled=factor.is_scaled
            )
            
            if not target_values:
                return {
                    'factor_name': factor.name,
                    'stored_values': 0,
                    'errors': ['No target values could be calculated'],
                    'calculation_dates': []
                }
            
            # Store target values using factor service
            entity_type = self._get_entity_type_from_factor(factor)
            
            # Adjust dates to match target values length (remove forecast horizon)
            adjusted_dates = dates[:-factor.forecast_horizon] if dates and len(dates) >= factor.forecast_horizon else []
            
            stored_values = self._store_factor_values(
                factor=factor,
                entity_id=entity_id,
                entity_type=entity_type,
                values=target_values,
                dates=adjusted_dates,
                overwrite=overwrite
            )
            
            return {
                'factor_name': factor.name,
                'stored_values': stored_values,
                'calculation_dates': adjusted_dates,
                'errors': [],
                'forecast_horizon': factor.forecast_horizon,
                'target_type': factor.target_type
            }
            
        except Exception as e:
            return {
                'error': f"Error calculating target factor {factor.name}: {str(e)}",
                'factor_name': factor.name,
                'stored_values': 0,
                'errors': [str(e)]
            }
    
    def calculate_target_values(
        self, 
        factor: ShareTargetFactor,
        prices: List[float], 
        forecast_horizon: int = None, 
        is_scaled: bool = None
    ) -> List:
        """
        Calculate target values based on price data.
        
        Args:
            factor: ShareTargetFactor domain entity with configuration
            prices: List of price values
            forecast_horizon: Number of periods ahead to predict (uses factor default if None)
            is_scaled: Whether to return scaled values (uses factor default if None)
            
        Returns:
            List of target values (returns or price directions)
        """
        if not prices or len(prices) < 2:
            return []

        horizon = forecast_horizon if forecast_horizon is not None else factor.forecast_horizon
        scaled = is_scaled if is_scaled is not None else factor.is_scaled

        target_values = []

        # Calculate target values based on target_type
        if factor.target_type.lower() == "return":
            # Calculate future returns
            for i in range(len(prices) - horizon):
                current_price = prices[i]
                future_price = prices[i + horizon]

                if current_price > 0 and future_price > 0:
                    return_value = (future_price / current_price) - 1
                    target_values.append(return_value)
                else:
                    target_values.append(0.0)  # Default to 0 for invalid prices

        elif "direction" in factor.target_type.lower() or "binary" in factor.target_type.lower():
            # Calculate price direction (1 for up, 0 for down)
            for i in range(len(prices) - horizon):
                current_price = prices[i]
                future_price = prices[i + horizon]

                if current_price > 0 and future_price > 0:
                    direction = 1 if future_price > current_price else 0
                    target_values.append(direction)
                else:
                    target_values.append(0)  # Default to 0 for invalid prices
        else:
            # Default to return calculation
            for i in range(len(prices) - horizon):
                current_price = prices[i]
                future_price = prices[i + horizon]

                if current_price > 0 and future_price > 0:
                    return_value = (future_price / current_price) - 1
                    target_values.append(return_value)
                else:
                    target_values.append(0.0)

        # Apply scaling if requested
        if scaled and target_values and factor.scaling_method:
            target_values = self._apply_scaling(target_values, factor.scaling_method)

        return target_values

    def _apply_scaling(self, values: List, scaling_method: str) -> List:
        """Apply scaling to target values based on scaling_method."""
        if not values or scaling_method is None:
            return values

        import numpy as np
        from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler

        values_array = np.array(values).reshape(-1, 1)

        if scaling_method.lower() == 'z_score' or scaling_method.lower() == 'standard':
            scaler = StandardScaler()
        elif scaling_method.lower() == 'min_max' or scaling_method.lower() == 'minmax':
            scaler = MinMaxScaler()
        elif scaling_method.lower() == 'robust':
            scaler = RobustScaler()
        else:
            # Default to standard scaling
            scaler = StandardScaler()

        try:
            scaled_values = scaler.fit_transform(values_array)
            return scaled_values.flatten().tolist()
        except Exception:
            # Return original values if scaling fails
            return values