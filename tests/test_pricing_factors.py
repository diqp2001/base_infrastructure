import unittest
import math
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_black_scholes_merton_price_factor import CompanyShareOptionBlackScholesMertonPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_heston_price_factor import CompanyShareOptionHestonPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_sabr_price_factor import CompanyShareOptionSABRPriceFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_black_scholes_merton_price_factor import PortfolioCompanyShareOptionBlackScholesMertonPriceFactor


class TestPricingFactors(unittest.TestCase):
    """Test suite for new pricing factors"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.S = 100.0      # Current price
        self.K = 105.0      # Strike price
        self.r = 0.05       # Risk-free rate
        self.T = 0.25       # 3 months to expiry
        self.sigma = 0.2    # 20% volatility
        self.q = 0.02       # 2% dividend yield

    def test_company_share_option_bsm_factor(self):
        """Test Company Share Option Black-Scholes-Merton factor"""
        factor = CompanyShareOptionBlackScholesMertonPriceFactor(
            name="test_bsm_factor",
            group="test",
            definition="Test BSM factor"
        )
        
        # Test call option
        call_price = factor.calculate(
            S=self.S, K=self.K, r=self.r, sigma=self.sigma, T=self.T, q=self.q, option_type="call"
        )
        
        self.assertIsNotNone(call_price, "Call price should not be None")
        self.assertGreater(call_price, 0, "Call price should be positive")
        self.assertLess(call_price, self.S, "Call price should be less than spot price")
        
        # Test put option
        put_price = factor.calculate(
            S=self.S, K=self.K, r=self.r, sigma=self.sigma, T=self.T, q=self.q, option_type="put"
        )
        
        self.assertIsNotNone(put_price, "Put price should not be None")
        self.assertGreater(put_price, 0, "Put price should be positive")
        
        # Test put-call parity approximately (allowing for dividends)
        # C - P = S*e^(-q*T) - K*e^(-r*T)
        parity_lhs = call_price - put_price
        parity_rhs = self.S * math.exp(-self.q * self.T) - self.K * math.exp(-self.r * self.T)
        
        self.assertAlmostEqual(parity_lhs, parity_rhs, places=2, 
                              msg="Put-call parity should hold approximately")
        
        # Test Greeks calculation
        greeks = factor.calculate_greeks(
            S=self.S, K=self.K, r=self.r, sigma=self.sigma, T=self.T, q=self.q, option_type="call"
        )
        
        self.assertIn("delta", greeks, "Greeks should include delta")
        self.assertIn("gamma", greeks, "Greeks should include gamma")
        self.assertIn("theta", greeks, "Greeks should include theta")
        self.assertIn("vega", greeks, "Greeks should include vega")
        self.assertIn("rho", greeks, "Greeks should include rho")
        
        # Basic Greek sanity checks
        self.assertGreater(greeks["delta"], 0, "Call delta should be positive")
        self.assertGreater(greeks["gamma"], 0, "Gamma should be positive")
        self.assertGreater(greeks["vega"], 0, "Vega should be positive")

    def test_company_share_option_heston_factor(self):
        """Test Company Share Option Heston factor"""
        factor = CompanyShareOptionHestonPriceFactor(
            name="test_heston_factor",
            group="test",
            definition="Test Heston factor"
        )
        
        # Heston parameters
        v0 = 0.04       # Initial variance (20% vol)
        kappa = 2.0     # Mean reversion speed
        theta = 0.04    # Long-term variance
        xi = 0.3        # Vol of vol
        rho = -0.5      # Correlation
        
        # Test with reduced paths for faster testing
        call_price = factor.calculate(
            S=self.S, K=self.K, r=self.r, T=self.T, 
            v0=v0, kappa=kappa, theta=theta, xi=xi, rho=rho, q=self.q,
            option_type="call", n_paths=1000, n_steps=50
        )
        
        self.assertIsNotNone(call_price, "Heston call price should not be None")
        self.assertGreater(call_price, 0, "Heston call price should be positive")
        
        # Test Feller condition check
        self.assertTrue(factor.feller_condition_check(kappa, theta, xi), 
                       "Feller condition should be satisfied for stable parameters")

    def test_company_share_option_sabr_factor(self):
        """Test Company Share Option SABR factor"""
        factor = CompanyShareOptionSABRPriceFactor(
            name="test_sabr_factor",
            group="test",
            definition="Test SABR factor"
        )
        
        # SABR parameters
        F = self.S * math.exp((self.r - self.q) * self.T)  # Forward price
        alpha = 0.2     # Initial volatility
        beta = 0.7      # CEV exponent
        rho = -0.3      # Correlation
        nu = 0.4        # Vol of vol
        
        # Test call option
        call_price = factor.calculate(
            F=F, K=self.K, T=self.T, alpha=alpha, beta=beta, rho=rho, nu=nu, 
            r=self.r, option_type="call"
        )
        
        self.assertIsNotNone(call_price, "SABR call price should not be None")
        self.assertGreater(call_price, 0, "SABR call price should be positive")
        
        # Test implied volatility calculation
        implied_vol = factor._sabr_implied_volatility(F, self.K, self.T, alpha, beta, rho, nu)
        self.assertIsNotNone(implied_vol, "SABR implied volatility should not be None")
        self.assertGreater(implied_vol, 0, "SABR implied volatility should be positive")

    def test_portfolio_company_share_option_bsm_factor(self):
        """Test Portfolio Company Share Option BSM factor"""
        factor = PortfolioCompanyShareOptionBlackScholesMertonPriceFactor(
            name="test_portfolio_bsm_factor",
            group="test",
            definition="Test Portfolio BSM factor"
        )
        
        # Test single-asset equivalent
        call_price = factor.calculate(
            S=self.S, K=self.K, r=self.r, sigma=self.sigma, T=self.T, q=self.q, 
            option_type="call", multiplier=100
        )
        
        self.assertIsNotNone(call_price, "Portfolio call price should not be None")
        self.assertGreater(call_price, 0, "Portfolio call price should be positive")
        
        # Test basket option with two assets
        spot_prices = [100.0, 120.0]
        weights = [0.6, 0.4]
        volatilities = [0.2, 0.25]
        correlations = [[1.0, 0.5], [0.5, 1.0]]
        dividend_yields = [0.02, 0.03]
        
        basket_price = factor.calculate_basket_option(
            spot_prices=spot_prices,
            weights=weights,
            K=self.K,
            r=self.r,
            T=self.T,
            correlations=correlations,
            volatilities=volatilities,
            dividend_yields=dividend_yields,
            option_type="call",
            multiplier=100
        )
        
        self.assertIsNotNone(basket_price, "Basket option price should not be None")
        self.assertGreater(basket_price, 0, "Basket option price should be positive")

    def test_invalid_parameters(self):
        """Test handling of invalid parameters"""
        factor = CompanyShareOptionBlackScholesMertonPriceFactor(
            name="test_invalid_factor",
            group="test"
        )
        
        # Test negative spot price
        result = factor.calculate(S=-10, K=self.K, r=self.r, sigma=self.sigma, T=self.T)
        self.assertIsNone(result, "Should return None for negative spot price")
        
        # Test zero volatility
        result = factor.calculate(S=self.S, K=self.K, r=self.r, sigma=0, T=self.T)
        self.assertIsNone(result, "Should return None for zero volatility")
        
        # Test zero time to maturity
        result = factor.calculate(S=self.S, K=self.K, r=self.r, sigma=self.sigma, T=0)
        self.assertIsNone(result, "Should return None for zero time to maturity")

    def test_at_the_money_options(self):
        """Test ATM option pricing"""
        factor = CompanyShareOptionBlackScholesMertonPriceFactor(
            name="test_atm_factor",
            group="test"
        )
        
        # ATM call and put
        call_price = factor.calculate(
            S=self.S, K=self.S, r=self.r, sigma=self.sigma, T=self.T, q=self.q, option_type="call"
        )
        put_price = factor.calculate(
            S=self.S, K=self.S, r=self.r, sigma=self.sigma, T=self.T, q=self.q, option_type="put"
        )
        
        self.assertIsNotNone(call_price, "ATM call price should not be None")
        self.assertIsNotNone(put_price, "ATM put price should not be None")
        
        # For ATM options with dividends, call should be slightly cheaper than put when q > 0
        if self.q > 0:
            self.assertLess(call_price, put_price, "ATM call should be cheaper than put when dividend yield > 0")


if __name__ == '__main__':
    unittest.main()