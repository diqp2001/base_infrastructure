"""
Factor Calculation Service - handles computation and storage of factor values.
Provides a service layer for calculating and storing factor calculations from domain entities.
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal
import pandas as pd

from src.domain.entities.factor.factor import Factor
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
from src.application.services.database_service import DatabaseService


class FactorCalculationService:
    """Service for calculating factor values and storing them in the database."""
    
    def __init__(self, db_type: str = 'sqlite'):
        """Initialize the service with a database type."""
        self.database_service = DatabaseService(db_type)
        self.repository = BaseFactorRepository(self.database_service.session)
    
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
    
    # Existing calculation methods...
    def calculate_and_store_momentum(
        self, 
        factor: ShareMomentumFactor, 
        entity_id: int, 
        entity_type: str,
        prices: List[float], 
        dates: List[date],
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate momentum factor values and store them in the database.
        
        Args:
            factor: ShareMomentumFactor domain entity
            entity_id: ID of the entity (e.g., share ID)
            entity_type: Type of entity ('share', 'equity', etc.)
            prices: List of price values
            dates: List of corresponding dates
            overwrite: Whether to overwrite existing values
            
        Returns:
            Dict with calculation results and storage stats
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
        
        # Calculate momentum for each date
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
            if isinstance(data, dict) and 'prices' in data and 'dates' in data:
                return self.calculate_and_store_momentum(
                    factor, entity_id, entity_type, data['prices'], data['dates'], overwrite
                )
            else:
                raise ValueError("ShareMomentumFactor requires data with 'prices' and 'dates' keys")
        
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