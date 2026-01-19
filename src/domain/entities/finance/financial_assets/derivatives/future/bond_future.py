from src.domain.entities.finance.financial_assets.bond import Bond
from src.domain.entities.finance.financial_assets.derivatives.future.future import Future


class BondFuture(Future):
    """Future contract for a bond."""
    def __init__(self, underlying_asset: Bond, **kwargs):
        super().__init__(underlying_asset=underlying_asset,**kwargs)
        