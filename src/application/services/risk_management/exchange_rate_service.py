# application/services/exchange_rate_service.py

class ExchangeRateExposureService:
    
    def calculate_elasticity(self, h1: float, h2: float, r: float) -> float:
        """
        Calculate the elasticity of exchange rate exposure for a company.

        Args:
            h1 (float): Total foreign sales / total sales (%) as a decimal (e.g., 0.3 for 30%).
            h2 (float): Total foreign costs / total costs (%) as a decimal (e.g., 0.2 for 20%).
            r (float): Return margin rate (%) as a decimal (e.g., 0.1 for 10%).

        Returns:
            float: Elasticity of exchange rate exposure (e).
        """
        if r <= 0:
            raise ValueError("Return margin rate (r) must be greater than 0.")
        
        elasticity = h1 + (h1 - h2) * ((1 / r) - 1)
        return elasticity
    
    def calculate_optimal_hedge_ratio(self, h1: float, h2: float, r: float):
        elasticity = self.calculate_elasticity(h1,h2,r)
        hedge_ratio = elasticity/(1 + elasticity)

        return hedge_ratio
