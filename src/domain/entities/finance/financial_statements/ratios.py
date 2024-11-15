# domain/entities/financial_statements/ratios.py

class Ratios:
    """
    Financial ratios for a company.
    """

    @staticmethod
    def debt_to_equity(liabilities: float, equity: float) -> float:
        return liabilities / equity if equity != 0 else None

    @staticmethod
    def return_on_equity(net_income: float, equity: float) -> float:
        return net_income / equity if equity != 0 else None
