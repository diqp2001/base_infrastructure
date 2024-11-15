# src/domain/entities/finance/financial_assets/derivatives/derivative.py

class Derivative:
    def __init__(self, underlying_asset: str, notional_value: float, maturity_date: str, price: float):
        """
        Initialize a generic derivative object.
        
        :param underlying_asset: The underlying asset for the derivative (e.g., 'Stock', 'Bond').
        :param notional_value: The notional value of the derivative (e.g., contract size).
        :param maturity_date: The maturity date of the derivative.
        :param price: The price of the derivative contract.
        """
        self.underlying_asset = underlying_asset
        self.notional_value = notional_value
        self.maturity_date = maturity_date
        self.price = price

    def get_details(self):
        """
        Return a summary of the derivative.
        """
        return {
            "underlying_asset": self.underlying_asset,
            "notional_value": self.notional_value,
            "maturity_date": self.maturity_date,
            "price": self.price
        }

    def __repr__(self):
        return f"Derivative(Underlying: {self.underlying_asset}, Notional: {self.notional_value}, Maturity: {self.maturity_date}, Price: {self.price})"
