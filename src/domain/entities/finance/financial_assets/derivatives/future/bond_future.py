from src.domain.entities.finance.financial_assets.derivatives.future.future import Future


class BondFuture(Future):
    """Future contract on a fixed-income (bond) underlying."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        