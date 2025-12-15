"""
Risk Calculator for Market Making Project

Implements risk management calculations including:
- Value at Risk (VaR)
- Greeks exposure
- Position limits validation
- Portfolio risk metrics
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import math
from scipy import stats


class RiskCalculator:
    """
    Comprehensive risk calculator for market making operations.
    """
    
    def __init__(self, confidence_level: float = 0.95):
        """
        Initialize the risk calculator.
        
        Args:
            confidence_level: Confidence level for VaR calculations (default 95%)
        """
        self.logger = logging.getLogger(__name__)
        self.confidence_level = confidence_level
        
        # Risk parameters
        self.var_lookback_days = 252  # 1 year for historical VaR
        self.stress_scenarios = self._initialize_stress_scenarios()
        
        self.logger.info(f"RiskCalculator initialized with {confidence_level*100}% confidence level")
    
    def calculate_position_var(self, symbol: str, position: Decimal, 
                              market_data: Dict[str, Any], 
                              historical_prices: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Calculate Value at Risk for a single position.
        
        Args:
            symbol: Instrument symbol
            position: Current position size
            market_data: Current market data
            historical_prices: Historical price data for VaR calculation
            
        Returns:
            Position VaR metrics
        """
        try:
            current_price = market_data.get('price', Decimal('100'))
            volatility = market_data.get('volatility', Decimal('0.20'))
            
            # Calculate parametric VaR (using normal distribution)
            parametric_var = self._calculate_parametric_var(position, current_price, volatility)
            
            # Calculate historical VaR if historical data is available
            historical_var = None
            if historical_prices is not None and not historical_prices.empty:
                historical_var = self._calculate_historical_var(position, historical_prices)
            
            # Calculate Monte Carlo VaR
            monte_carlo_var = self._calculate_monte_carlo_var(position, current_price, volatility)
            
            # Use the maximum of the three methods for conservative estimate
            var_estimates = [parametric_var]
            if historical_var is not None:
                var_estimates.append(historical_var)
            var_estimates.append(monte_carlo_var)
            
            final_var = max(var_estimates)
            
            return {
                'symbol': symbol,
                'position': float(position),
                'current_price': float(current_price),
                'volatility': float(volatility),
                'parametric_var': parametric_var,
                'historical_var': historical_var,
                'monte_carlo_var': monte_carlo_var,
                'final_var': final_var,
                'var_as_percent_of_position': (final_var / abs(float(position * current_price))) * 100 if position != 0 else 0,
                'confidence_level': self.confidence_level,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating position VaR for {symbol}: {str(e)}")
            return {'error': str(e), 'symbol': symbol}
    
    def calculate_portfolio_var(self, positions: Dict[str, Decimal],
                               market_data: Dict[str, Dict[str, Any]],
                               correlation_matrix: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Calculate portfolio Value at Risk considering correlations.
        
        Args:
            positions: Dictionary of positions {symbol: quantity}
            market_data: Market data for all positions
            correlation_matrix: Correlation matrix between instruments
            
        Returns:
            Portfolio VaR metrics
        """
        try:
            individual_vars = {}
            position_values = {}
            
            # Calculate individual VaRs
            for symbol, position in positions.items():
                if symbol in market_data:
                    var_result = self.calculate_position_var(symbol, position, market_data[symbol])
                    if 'final_var' in var_result:
                        individual_vars[symbol] = var_result['final_var']
                        position_values[symbol] = float(position * market_data[symbol]['price'])
            
            if not individual_vars:
                return {'error': 'No valid VaR calculations available'}
            
            # Simple portfolio VaR (sum of individual VaRs) - conservative approach
            simple_portfolio_var = sum(individual_vars.values())
            
            # Diversified portfolio VaR using correlation matrix
            diversified_var = simple_portfolio_var
            if correlation_matrix is not None:
                diversified_var = self._calculate_diversified_var(individual_vars, correlation_matrix)
            
            # Calculate portfolio metrics
            total_portfolio_value = sum(abs(value) for value in position_values.values())
            portfolio_var_percent = (diversified_var / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
            
            # Diversification benefit
            diversification_benefit = simple_portfolio_var - diversified_var
            diversification_ratio = diversification_benefit / simple_portfolio_var if simple_portfolio_var > 0 else 0
            
            return {
                'individual_vars': individual_vars,
                'position_values': position_values,
                'simple_portfolio_var': simple_portfolio_var,
                'diversified_portfolio_var': diversified_var,
                'total_portfolio_value': total_portfolio_value,
                'portfolio_var_percent': portfolio_var_percent,
                'diversification_benefit': diversification_benefit,
                'diversification_ratio': diversification_ratio,
                'confidence_level': self.confidence_level,
                'number_of_positions': len(positions),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio VaR: {str(e)}")
            return {'error': str(e)}
    
    def calculate_greeks_exposure(self, options_positions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate total Greeks exposure for options positions.
        
        Args:
            options_positions: Dict with position info and Greeks
            
        Returns:
            Total Greeks exposure
        """
        try:
            total_greeks = {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0
            }
            
            position_details = []
            
            for symbol, position_data in options_positions.items():
                position_size = position_data.get('quantity', 0)
                greeks = position_data.get('greeks', {})
                
                # Scale Greeks by position size
                position_greeks = {}
                for greek_name in total_greeks.keys():
                    greek_value = float(greeks.get(greek_name, 0))
                    position_greek = greek_value * position_size
                    position_greeks[greek_name] = position_greek
                    total_greeks[greek_name] += position_greek
                
                position_details.append({
                    'symbol': symbol,
                    'position_size': position_size,
                    'unit_greeks': {k: float(v) for k, v in greeks.items()},
                    'position_greeks': position_greeks
                })
            
            # Calculate Greek-based risk metrics
            delta_risk = abs(total_greeks['delta']) * 100  # Risk from 1% underlying move
            gamma_risk = abs(total_greeks['gamma']) * 100  # Convexity risk
            theta_risk = abs(total_greeks['theta'])  # Daily time decay
            vega_risk = abs(total_greeks['vega'])  # Risk from 1% vol move
            
            return {
                'total_greeks': total_greeks,
                'position_details': position_details,
                'greek_risks': {
                    'delta_risk_1pct_move': delta_risk,
                    'gamma_risk_convexity': gamma_risk,
                    'theta_risk_daily': theta_risk,
                    'vega_risk_1pct_vol': vega_risk
                },
                'net_delta_exposure': total_greeks['delta'],
                'total_gamma_exposure': total_greeks['gamma'],
                'total_theta_decay': total_greeks['theta'],
                'total_vega_exposure': total_greeks['vega'],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating Greeks exposure: {str(e)}")
            return {'error': str(e)}
    
    def validate_position_limits(self, positions: Dict[str, Decimal],
                                market_data: Dict[str, Dict[str, Any]],
                                limits: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate positions against risk limits.
        
        Args:
            positions: Current positions
            market_data: Market data for positions
            limits: Risk limit configuration
            
        Returns:
            Limit validation results
        """
        try:
            violations = []
            warnings = []
            position_utilization = {}
            
            # Extract limits
            max_position_size = limits.get('max_position_size', Decimal('1000000'))
            max_portfolio_var = limits.get('max_portfolio_var', Decimal('0.05'))
            max_sector_concentration = limits.get('max_sector_concentration', Decimal('0.30'))
            
            # Check individual position limits
            for symbol, position in positions.items():
                if symbol in market_data:
                    position_value = abs(position * market_data[symbol]['price'])
                    
                    if position_value > max_position_size:
                        violations.append({
                            'type': 'position_size',
                            'symbol': symbol,
                            'current_value': float(position_value),
                            'limit': float(max_position_size),
                            'excess': float(position_value - max_position_size)
                        })
                    
                    # Calculate utilization
                    utilization = float(position_value / max_position_size)
                    position_utilization[symbol] = utilization
                    
                    if utilization > 0.8:  # 80% warning threshold
                        warnings.append({
                            'type': 'position_size_warning',
                            'symbol': symbol,
                            'utilization': utilization,
                            'threshold': 0.8
                        })
            
            # Check portfolio VaR limit
            portfolio_var_result = self.calculate_portfolio_var(positions, market_data)
            if 'diversified_portfolio_var' in portfolio_var_result:
                portfolio_var_percent = portfolio_var_result['portfolio_var_percent'] / 100
                
                if portfolio_var_percent > float(max_portfolio_var):
                    violations.append({
                        'type': 'portfolio_var',
                        'current_var': portfolio_var_percent,
                        'limit': float(max_portfolio_var),
                        'excess': portfolio_var_percent - float(max_portfolio_var)
                    })
            
            # Check sector concentration (simplified - assumes all equity positions are same sector)
            total_portfolio_value = sum(
                abs(pos * market_data[sym]['price']) 
                for sym, pos in positions.items() 
                if sym in market_data
            )
            
            if total_portfolio_value > 0:
                equity_exposure = sum(
                    abs(pos * market_data[sym]['price'])
                    for sym, pos in positions.items()
                    if sym in market_data and market_data[sym].get('asset_class') == 'equity'
                )
                
                sector_concentration = equity_exposure / total_portfolio_value
                
                if sector_concentration > float(max_sector_concentration):
                    violations.append({
                        'type': 'sector_concentration',
                        'current_concentration': sector_concentration,
                        'limit': float(max_sector_concentration),
                        'excess': sector_concentration - float(max_sector_concentration)
                    })
            
            return {
                'violations': violations,
                'warnings': warnings,
                'position_utilization': position_utilization,
                'limits_used': {
                    'max_position_size': float(max_position_size),
                    'max_portfolio_var': float(max_portfolio_var),
                    'max_sector_concentration': float(max_sector_concentration)
                },
                'overall_status': 'VIOLATION' if violations else ('WARNING' if warnings else 'OK'),
                'total_positions': len(positions),
                'total_violations': len(violations),
                'total_warnings': len(warnings),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error validating position limits: {str(e)}")
            return {'error': str(e)}
    
    def run_stress_tests(self, positions: Dict[str, Decimal],
                        market_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run stress tests on current portfolio.
        
        Args:
            positions: Current positions
            market_data: Market data for positions
            
        Returns:
            Stress test results
        """
        try:
            stress_results = {}
            
            for scenario_name, scenario in self.stress_scenarios.items():
                scenario_pnl = 0
                position_impacts = {}
                
                for symbol, position in positions.items():
                    if symbol in market_data:
                        current_price = market_data[symbol]['price']
                        asset_class = market_data[symbol].get('asset_class', 'equity')
                        
                        # Apply scenario shock based on asset class
                        if asset_class in scenario:
                            price_shock = scenario[asset_class]['price_shock']
                            vol_shock = scenario[asset_class].get('volatility_shock', 0)
                            
                            # Calculate position PnL impact
                            new_price = current_price * (1 + price_shock)
                            position_pnl = float(position * (new_price - current_price))
                            
                            position_impacts[symbol] = {
                                'current_price': float(current_price),
                                'stressed_price': float(new_price),
                                'price_shock': price_shock,
                                'position_pnl': position_pnl,
                                'volatility_shock': vol_shock
                            }
                            
                            scenario_pnl += position_pnl
                
                stress_results[scenario_name] = {
                    'total_pnl_impact': scenario_pnl,
                    'position_impacts': position_impacts,
                    'scenario_parameters': scenario
                }
            
            # Find worst-case scenario
            worst_scenario = min(stress_results.items(), key=lambda x: x[1]['total_pnl_impact'])
            
            return {
                'stress_scenarios': stress_results,
                'worst_case_scenario': {
                    'name': worst_scenario[0],
                    'pnl_impact': worst_scenario[1]['total_pnl_impact']
                },
                'total_scenarios_tested': len(self.stress_scenarios),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error running stress tests: {str(e)}")
            return {'error': str(e)}
    
    # Private helper methods
    
    def _calculate_parametric_var(self, position: Decimal, price: Decimal, volatility: Decimal) -> float:
        """Calculate parametric VaR using normal distribution."""
        position_value = float(position * price)
        daily_volatility = float(volatility) / math.sqrt(252)  # Convert annual to daily
        z_score = stats.norm.ppf(1 - self.confidence_level)  # For 95% confidence, z ≈ -1.645
        
        var = abs(position_value * daily_volatility * z_score)
        return var
    
    def _calculate_historical_var(self, position: Decimal, historical_prices: pd.DataFrame) -> float:
        """Calculate historical VaR using historical price movements."""
        if len(historical_prices) < 2:
            return None
        
        # Calculate historical returns
        returns = historical_prices['close'].pct_change().dropna()
        
        if len(returns) < 10:  # Need minimum data
            return None
        
        # Calculate position value changes
        current_price = historical_prices['close'].iloc[-1]
        position_value = float(position * current_price)
        
        position_changes = returns * position_value
        
        # Calculate VaR at specified confidence level
        var_percentile = (1 - self.confidence_level) * 100
        var = abs(np.percentile(position_changes, var_percentile))
        
        return var
    
    def _calculate_monte_carlo_var(self, position: Decimal, price: Decimal, 
                                 volatility: Decimal, num_simulations: int = 10000) -> float:
        """Calculate Monte Carlo VaR."""
        position_value = float(position * price)
        daily_volatility = float(volatility) / math.sqrt(252)
        
        # Generate random returns
        random_returns = np.random.normal(0, daily_volatility, num_simulations)
        
        # Calculate position value changes
        position_changes = random_returns * position_value
        
        # Calculate VaR
        var_percentile = (1 - self.confidence_level) * 100
        var = abs(np.percentile(position_changes, var_percentile))
        
        return var
    
    def _calculate_diversified_var(self, individual_vars: Dict[str, float],
                                 correlation_matrix: pd.DataFrame) -> float:
        """Calculate diversified portfolio VaR using correlation matrix."""
        try:
            symbols = list(individual_vars.keys())
            vars_vector = np.array([individual_vars[symbol] for symbol in symbols])
            
            # Ensure correlation matrix matches our symbols
            common_symbols = [s for s in symbols if s in correlation_matrix.index]
            
            if len(common_symbols) < 2:
                return sum(individual_vars.values())  # Fall back to simple sum
            
            # Extract relevant correlation submatrix
            corr_sub = correlation_matrix.loc[common_symbols, common_symbols]
            vars_sub = np.array([individual_vars[s] for s in common_symbols])
            
            # Calculate covariance matrix (VaR * correlation * VaR)
            cov_matrix = np.outer(vars_sub, vars_sub) * corr_sub.values
            
            # Portfolio VaR = sqrt(w' * Cov * w) where w is vector of 1s for VaR
            weights = np.ones(len(common_symbols))
            portfolio_var = math.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            
            return portfolio_var
            
        except Exception as e:
            self.logger.warning(f"Error calculating diversified VaR: {e}, falling back to simple sum")
            return sum(individual_vars.values())
    
    def _initialize_stress_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Initialize predefined stress test scenarios."""
        return {
            'market_crash': {
                'equity': {'price_shock': -0.20, 'volatility_shock': 0.50},
                'fixed_income': {'price_shock': 0.05, 'volatility_shock': 0.20},
                'commodity': {'price_shock': -0.15, 'volatility_shock': 0.30}
            },
            'interest_rate_spike': {
                'equity': {'price_shock': -0.10, 'volatility_shock': 0.25},
                'fixed_income': {'price_shock': -0.15, 'volatility_shock': 0.40},
                'commodity': {'price_shock': 0.05, 'volatility_shock': 0.15}
            },
            'volatility_spike': {
                'equity': {'price_shock': -0.05, 'volatility_shock': 1.00},
                'fixed_income': {'price_shock': -0.02, 'volatility_shock': 0.50},
                'commodity': {'price_shock': -0.08, 'volatility_shock': 0.75}
            },
            'liquidity_crisis': {
                'equity': {'price_shock': -0.15, 'volatility_shock': 0.60},
                'fixed_income': {'price_shock': -0.08, 'volatility_shock': 0.30},
                'commodity': {'price_shock': -0.12, 'volatility_shock': 0.45}
            },
            'inflation_shock': {
                'equity': {'price_shock': -0.08, 'volatility_shock': 0.20},
                'fixed_income': {'price_shock': -0.12, 'volatility_shock': 0.30},
                'commodity': {'price_shock': 0.20, 'volatility_shock': 0.40}
            }
        }
    
    def update_confidence_level(self, new_confidence_level: float):
        """Update the confidence level for VaR calculations."""
        if 0.5 <= new_confidence_level <= 0.999:
            self.confidence_level = new_confidence_level
            self.logger.info(f"Confidence level updated to {new_confidence_level*100}%")
        else:
            self.logger.error(f"Invalid confidence level: {new_confidence_level}. Must be between 0.5 and 0.999")
    
    def get_risk_summary(self, positions: Dict[str, Decimal],
                        market_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get a comprehensive risk summary.
        
        Args:
            positions: Current positions
            market_data: Market data for positions
            
        Returns:
            Comprehensive risk summary
        """
        portfolio_var = self.calculate_portfolio_var(positions, market_data)
        
        # Default risk limits for summary
        default_limits = {
            'max_position_size': Decimal('1000000'),
            'max_portfolio_var': Decimal('0.05'),
            'max_sector_concentration': Decimal('0.30')
        }
        
        limits_validation = self.validate_position_limits(positions, market_data, default_limits)
        stress_tests = self.run_stress_tests(positions, market_data)
        
        return {
            'portfolio_var': portfolio_var,
            'limits_validation': limits_validation,
            'stress_tests': stress_tests,
            'risk_summary': {
                'total_positions': len(positions),
                'portfolio_var_ok': portfolio_var.get('portfolio_var_percent', 0) < 5,  # 5% threshold
                'limits_status': limits_validation.get('overall_status', 'UNKNOWN'),
                'worst_stress_scenario': stress_tests.get('worst_case_scenario', {}).get('name', 'None')
            },
            'timestamp': datetime.now().isoformat()
        }