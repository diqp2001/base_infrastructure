"""
Risk Manager for SPX Call Spread Market Making

This module implements comprehensive risk management for the market making strategy,
including position limits, exposure monitoring, and risk alerts.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Risk manager for SPX call spread market making strategy.
    Monitors exposures, enforces limits, and provides risk analytics.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the risk manager.
        
        Args:
            config: Risk management configuration
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Risk limits from config
        self.max_position_size = config.get('max_position_size', 10)
        self.max_daily_loss = config.get('max_daily_loss', 5000)
        self.max_gamma_exposure = config.get('max_gamma_exposure', 1000)
        self.max_vega_exposure = config.get('max_vega_exposure', 2000)
        self.max_theta_exposure = config.get('max_theta_exposure', 500)
        self.max_delta_exposure = config.get('max_delta_exposure', 100)
        
        # Concentration limits
        self.max_single_expiry_exposure = config.get('max_single_expiry_exposure', 0.3)  # 30%
        self.max_single_strike_exposure = config.get('max_single_strike_exposure', 0.2)   # 20%
        
        # Market risk limits
        self.max_portfolio_var = config.get('max_portfolio_var', 10000)  # 1-day VaR
        self.stress_test_scenarios = config.get('stress_test_scenarios', [
            {'spx_move': -0.10, 'vol_move': 0.05},  # 10% down, 5% vol up
            {'spx_move': 0.05, 'vol_move': -0.03},  # 5% up, 3% vol down
        ])
        
        # Risk monitoring state
        self.risk_alerts = []
        self.daily_pnl = 0
        self.risk_metrics_history = []
    
    def check_position_limits(self, new_position: Dict[str, Any], existing_positions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a new position would violate risk limits.
        
        Args:
            new_position: Proposed new position
            existing_positions: Current active positions
            
        Returns:
            Dict containing limit check results
        """
        try:
            violations = []
            warnings = []
            
            # Check total position count
            current_count = len(existing_positions)
            if current_count >= self.max_position_size:
                violations.append({
                    'type': 'position_count',
                    'current': current_count,
                    'limit': self.max_position_size,
                    'message': f"Position count limit exceeded: {current_count}/{self.max_position_size}"
                })
            
            # Calculate portfolio exposures with new position
            portfolio_with_new = existing_positions.copy()
            portfolio_with_new['new_position'] = new_position
            
            exposures = self._calculate_portfolio_exposures(portfolio_with_new)
            
            # Check Greek exposures
            if abs(exposures.get('total_delta', 0)) > self.max_delta_exposure:
                violations.append({
                    'type': 'delta_exposure',
                    'current': exposures['total_delta'],
                    'limit': self.max_delta_exposure,
                    'message': f"Delta exposure limit exceeded: {exposures['total_delta']:.1f}"
                })
            
            if abs(exposures.get('total_gamma', 0)) > self.max_gamma_exposure:
                violations.append({
                    'type': 'gamma_exposure',
                    'current': exposures['total_gamma'],
                    'limit': self.max_gamma_exposure,
                    'message': f"Gamma exposure limit exceeded: {exposures['total_gamma']:.1f}"
                })
            
            if abs(exposures.get('total_vega', 0)) > self.max_vega_exposure:
                violations.append({
                    'type': 'vega_exposure',
                    'current': exposures['total_vega'],
                    'limit': self.max_vega_exposure,
                    'message': f"Vega exposure limit exceeded: {exposures['total_vega']:.1f}"
                })
            
            if abs(exposures.get('total_theta', 0)) > self.max_theta_exposure:
                violations.append({
                    'type': 'theta_exposure',
                    'current': exposures['total_theta'],
                    'limit': self.max_theta_exposure,
                    'message': f"Theta exposure limit exceeded: {exposures['total_theta']:.1f}"
                })
            
            # Check concentration limits
            concentration_issues = self._check_concentration_limits(portfolio_with_new)
            violations.extend(concentration_issues.get('violations', []))
            warnings.extend(concentration_issues.get('warnings', []))
            
            # Check daily loss limit
            if self.daily_pnl < -self.max_daily_loss:
                violations.append({
                    'type': 'daily_loss',
                    'current': self.daily_pnl,
                    'limit': -self.max_daily_loss,
                    'message': f"Daily loss limit exceeded: {self.daily_pnl:.0f}"
                })
            
            return {
                'position_approved': len(violations) == 0,
                'violations': violations,
                'warnings': warnings,
                'portfolio_exposures': exposures,
                'check_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error checking position limits: {e}")
            return {
                'position_approved': False,
                'error': str(e),
                'check_timestamp': datetime.now().isoformat(),
            }
    
    def calculate_portfolio_risk_metrics(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive risk metrics for the portfolio.
        
        Args:
            positions: Active positions dictionary
            
        Returns:
            Dict containing risk metrics
        """
        try:
            # Calculate basic exposures
            exposures = self._calculate_portfolio_exposures(positions)
            
            # Calculate VaR (Value at Risk)
            portfolio_var = self._calculate_portfolio_var(positions)
            
            # Stress test analysis
            stress_results = self._run_stress_tests(positions)
            
            # Concentration analysis
            concentration_analysis = self._analyze_concentration(positions)
            
            # Time decay analysis
            theta_analysis = self._analyze_theta_decay(positions)
            
            # Volatility sensitivity
            vega_analysis = self._analyze_vega_exposure(positions)
            
            risk_metrics = {
                'basic_exposures': exposures,
                'portfolio_var_1day': portfolio_var,
                'stress_test_results': stress_results,
                'concentration_analysis': concentration_analysis,
                'theta_analysis': theta_analysis,
                'vega_analysis': vega_analysis,
                'overall_risk_score': self._calculate_overall_risk_score(exposures, portfolio_var),
                'calculation_timestamp': datetime.now().isoformat(),
            }
            
            # Store for historical analysis
            self.risk_metrics_history.append(risk_metrics)
            
            # Keep only last 30 days of history
            cutoff_date = datetime.now() - timedelta(days=30)
            self.risk_metrics_history = [
                rm for rm in self.risk_metrics_history
                if datetime.fromisoformat(rm['calculation_timestamp']) > cutoff_date
            ]
            
            return risk_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio risk metrics: {e}")
            return {
                'error': str(e),
                'calculation_timestamp': datetime.now().isoformat(),
            }
    
    def monitor_real_time_risk(self, positions: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor real-time risk and generate alerts.
        
        Args:
            positions: Current positions
            market_data: Current market data
            
        Returns:
            Dict containing risk monitoring results
        """
        try:
            alerts = []
            
            # Update daily P&L
            self._update_daily_pnl(positions, market_data)
            
            # Check for new alerts
            current_exposures = self._calculate_portfolio_exposures(positions)
            
            # Delta exposure alert
            delta_utilization = abs(current_exposures.get('total_delta', 0)) / self.max_delta_exposure
            if delta_utilization > 0.8:
                alerts.append({
                    'type': 'delta_warning',
                    'severity': 'high' if delta_utilization > 0.95 else 'medium',
                    'message': f"Delta exposure at {delta_utilization:.1%} of limit",
                    'current_value': current_exposures['total_delta'],
                    'limit': self.max_delta_exposure,
                })
            
            # Gamma exposure alert
            gamma_utilization = abs(current_exposures.get('total_gamma', 0)) / self.max_gamma_exposure
            if gamma_utilization > 0.8:
                alerts.append({
                    'type': 'gamma_warning',
                    'severity': 'high' if gamma_utilization > 0.95 else 'medium',
                    'message': f"Gamma exposure at {gamma_utilization:.1%} of limit",
                    'current_value': current_exposures['total_gamma'],
                    'limit': self.max_gamma_exposure,
                })
            
            # Daily loss alert
            loss_utilization = abs(self.daily_pnl) / self.max_daily_loss if self.daily_pnl < 0 else 0
            if loss_utilization > 0.7:
                alerts.append({
                    'type': 'daily_loss_warning',
                    'severity': 'high' if loss_utilization > 0.9 else 'medium',
                    'message': f"Daily loss at {loss_utilization:.1%} of limit",
                    'current_value': self.daily_pnl,
                    'limit': -self.max_daily_loss,
                })
            
            # Market volatility alert
            vix = market_data.get('vix', 20)
            if vix > 35:
                alerts.append({
                    'type': 'volatility_spike',
                    'severity': 'high',
                    'message': f"VIX spike detected: {vix:.1f}",
                    'recommendation': 'Consider reducing position sizes and increasing hedging',
                })
            
            # Update risk alerts
            self.risk_alerts = alerts
            
            return {
                'active_alerts': alerts,
                'alert_count': len(alerts),
                'high_severity_count': len([a for a in alerts if a.get('severity') == 'high']),
                'current_exposures': current_exposures,
                'daily_pnl': self.daily_pnl,
                'monitoring_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error in real-time risk monitoring: {e}")
            return {
                'error': str(e),
                'monitoring_timestamp': datetime.now().isoformat(),
            }
    
    def _calculate_portfolio_exposures(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate total portfolio exposures."""
        total_delta = 0
        total_gamma = 0
        total_theta = 0
        total_vega = 0
        total_notional = 0
        
        for position_id, position in positions.items():
            if position_id == 'new_position':
                # For proposed new position
                greeks = position.get('spread_data', {}).get('greeks', {})
                size = position.get('size', 1)
            else:
                # For existing positions
                greeks = position.get('greeks', {})
                size = position.get('size', 1)
            
            delta = greeks.get('delta', 0) * size
            gamma = greeks.get('gamma', 0) * size
            theta = greeks.get('theta', 0) * size
            vega = greeks.get('vega', 0) * size
            
            total_delta += delta
            total_gamma += gamma
            total_theta += theta
            total_vega += vega
            
            # Calculate notional exposure
            underlying_price = position.get('underlying_price', 4500)
            notional = underlying_price * size
            total_notional += notional
        
        return {
            'total_delta': total_delta,
            'total_gamma': total_gamma,
            'total_theta': total_theta,
            'total_vega': total_vega,
            'total_notional': total_notional,
            'position_count': len([p for p in positions if p != 'new_position']),
        }
    
    def _check_concentration_limits(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """Check concentration limits across expiries and strikes."""
        violations = []
        warnings = []
        
        # Group positions by expiry
        expiry_exposure = {}
        strike_exposure = {}
        total_notional = 0
        
        for position_id, position in positions.items():
            expiry = position.get('expiry_date', 'unknown')
            strikes = position.get('strikes', {})
            size = position.get('size', 1)
            underlying_price = position.get('underlying_price', 4500)
            notional = underlying_price * size
            
            total_notional += notional
            
            # Expiry concentration
            if expiry not in expiry_exposure:
                expiry_exposure[expiry] = 0
            expiry_exposure[expiry] += notional
            
            # Strike concentration
            for strike_type, strike in strikes.items():
                if strike not in strike_exposure:
                    strike_exposure[strike] = 0
                strike_exposure[strike] += notional
        
        # Check expiry concentration
        for expiry, exposure in expiry_exposure.items():
            concentration = exposure / total_notional if total_notional > 0 else 0
            if concentration > self.max_single_expiry_exposure:
                violations.append({
                    'type': 'expiry_concentration',
                    'expiry': expiry,
                    'concentration': concentration,
                    'limit': self.max_single_expiry_exposure,
                    'message': f"Expiry concentration limit exceeded: {concentration:.1%}"
                })
        
        # Check strike concentration
        for strike, exposure in strike_exposure.items():
            concentration = exposure / total_notional if total_notional > 0 else 0
            if concentration > self.max_single_strike_exposure:
                violations.append({
                    'type': 'strike_concentration',
                    'strike': strike,
                    'concentration': concentration,
                    'limit': self.max_single_strike_exposure,
                    'message': f"Strike concentration limit exceeded: {concentration:.1%}"
                })
        
        return {
            'violations': violations,
            'warnings': warnings,
            'expiry_concentrations': expiry_exposure,
            'strike_concentrations': strike_exposure,
        }
    
    def _calculate_portfolio_var(self, positions: Dict[str, Any]) -> float:
        """Calculate 1-day VaR for the portfolio."""
        try:
            # Simplified VaR calculation using delta-normal method
            total_delta = self._calculate_portfolio_exposures(positions)['total_delta']
            
            # Assume SPX daily volatility of 1% (adjust based on market conditions)
            daily_vol = 0.01
            confidence_level = 0.05  # 95% confidence
            z_score = 1.645  # 95% confidence z-score
            
            # Calculate VaR
            var_1_day = abs(total_delta) * 4500 * daily_vol * z_score  # Assuming SPX at 4500
            
            return var_1_day
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio VaR: {e}")
            return 0
    
    def _run_stress_tests(self, positions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run stress test scenarios on the portfolio."""
        stress_results = []
        
        for scenario in self.stress_test_scenarios:
            spx_move = scenario['spx_move']
            vol_move = scenario['vol_move']
            
            # Calculate P&L for this scenario
            scenario_pnl = 0
            for position in positions.values():
                greeks = position.get('greeks', {})
                size = position.get('size', 1)
                underlying_price = position.get('underlying_price', 4500)
                
                # Delta P&L
                delta_pnl = greeks.get('delta', 0) * size * underlying_price * spx_move
                
                # Vega P&L (vol move in percentage points)
                vega_pnl = greeks.get('vega', 0) * size * vol_move * 100
                
                position_pnl = delta_pnl + vega_pnl
                scenario_pnl += position_pnl
            
            stress_results.append({
                'scenario': f"SPX {spx_move:+.1%}, Vol {vol_move:+.1%}",
                'spx_move': spx_move,
                'vol_move': vol_move,
                'portfolio_pnl': scenario_pnl,
                'severity': 'high' if abs(scenario_pnl) > 5000 else 'medium',
            })
        
        return stress_results
    
    def _analyze_concentration(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze portfolio concentration across various dimensions."""
        return {
            'expiry_concentration': self._calculate_expiry_concentration(positions),
            'strike_concentration': self._calculate_strike_concentration(positions),
            'strategy_concentration': self._calculate_strategy_concentration(positions),
        }
    
    def _analyze_theta_decay(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze theta decay characteristics."""
        total_theta = 0
        theta_by_expiry = {}
        
        for position in positions.values():
            theta = position.get('greeks', {}).get('theta', 0)
            size = position.get('size', 1)
            expiry = position.get('expiry_date', 'unknown')
            
            position_theta = theta * size
            total_theta += position_theta
            
            if expiry not in theta_by_expiry:
                theta_by_expiry[expiry] = 0
            theta_by_expiry[expiry] += position_theta
        
        return {
            'total_daily_theta': total_theta,
            'theta_by_expiry': theta_by_expiry,
            'weekly_theta_projection': total_theta * 5,  # 5 trading days
        }
    
    def _analyze_vega_exposure(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze vega exposure and volatility sensitivity."""
        total_vega = 0
        vega_by_expiry = {}
        
        for position in positions.values():
            vega = position.get('greeks', {}).get('vega', 0)
            size = position.get('size', 1)
            expiry = position.get('expiry_date', 'unknown')
            
            position_vega = vega * size
            total_vega += position_vega
            
            if expiry not in vega_by_expiry:
                vega_by_expiry[expiry] = 0
            vega_by_expiry[expiry] += position_vega
        
        return {
            'total_vega': total_vega,
            'vega_by_expiry': vega_by_expiry,
            'vol_sensitivity': {
                '1%_vol_move': total_vega,
                '5%_vol_move': total_vega * 5,
            },
        }
    
    def _calculate_overall_risk_score(self, exposures: Dict[str, Any], var: float) -> float:
        """Calculate overall risk score (0-100)."""
        try:
            # Normalize exposures to risk score components
            delta_score = min(abs(exposures.get('total_delta', 0)) / self.max_delta_exposure, 1) * 25
            gamma_score = min(abs(exposures.get('total_gamma', 0)) / self.max_gamma_exposure, 1) * 25
            var_score = min(var / self.max_portfolio_var, 1) * 25
            loss_score = min(abs(self.daily_pnl) / self.max_daily_loss, 1) * 25 if self.daily_pnl < 0 else 0
            
            total_score = delta_score + gamma_score + var_score + loss_score
            return min(total_score, 100)
            
        except Exception:
            return 50  # Default medium risk score
    
    def _update_daily_pnl(self, positions: Dict[str, Any], market_data: Dict[str, Any]):
        """Update daily P&L tracking."""
        # In practice, this would calculate real P&L from market prices
        # For now, use a placeholder calculation
        total_pnl = 0
        for position in positions.values():
            position_pnl = position.get('current_pnl', 0)
            total_pnl += position_pnl
        
        self.daily_pnl = total_pnl
    
    def _calculate_expiry_concentration(self, positions: Dict[str, Any]) -> Dict[str, float]:
        """Calculate concentration by expiry."""
        expiry_notional = {}
        total_notional = 0
        
        for position in positions.values():
            expiry = position.get('expiry_date', 'unknown')
            size = position.get('size', 1)
            underlying_price = position.get('underlying_price', 4500)
            notional = underlying_price * size
            
            total_notional += notional
            if expiry not in expiry_notional:
                expiry_notional[expiry] = 0
            expiry_notional[expiry] += notional
        
        # Convert to percentages
        return {
            str(expiry): (notional / total_notional) if total_notional > 0 else 0
            for expiry, notional in expiry_notional.items()
        }
    
    def _calculate_strike_concentration(self, positions: Dict[str, Any]) -> Dict[str, float]:
        """Calculate concentration by strike."""
        strike_notional = {}
        total_notional = 0
        
        for position in positions.values():
            strikes = position.get('strikes', {})
            size = position.get('size', 1)
            underlying_price = position.get('underlying_price', 4500)
            notional = underlying_price * size
            
            total_notional += notional
            for strike_type, strike in strikes.items():
                if strike not in strike_notional:
                    strike_notional[strike] = 0
                strike_notional[strike] += notional
        
        # Convert to percentages
        return {
            str(strike): (notional / total_notional) if total_notional > 0 else 0
            for strike, notional in strike_notional.items()
        }
    
    def _calculate_strategy_concentration(self, positions: Dict[str, Any]) -> Dict[str, float]:
        """Calculate concentration by strategy type."""
        strategy_count = {}
        total_positions = len(positions)
        
        for position in positions.values():
            strategy_type = position.get('spread_type', 'unknown')
            if strategy_type not in strategy_count:
                strategy_count[strategy_type] = 0
            strategy_count[strategy_type] += 1
        
        # Convert to percentages
        return {
            strategy: (count / total_positions) if total_positions > 0 else 0
            for strategy, count in strategy_count.items()
        }