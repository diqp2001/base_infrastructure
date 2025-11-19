"""
Factor Calculation Service - handles computation and storage of factor values.
Provides a service layer for calculating and storing factor calculations from domain entities.
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal
import pandas as pd

from domain.entities.factor.factor import Factor
from domain.entities.factor.factor_value import FactorValue
from domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor
from domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor
from domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor
from domain.entities.factor.finance.financial_assets.share_factor.share_target_factor import ShareTargetFactor

from infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository


class FactorCalculationService:
    """Service for calculating factor values and storing them in the database."""
    
    def __init__(self, db_type: str = 'sqlite'):
        """Initialize the service with a database type."""
        self.repository = BaseFactorRepository(db_type)
    
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