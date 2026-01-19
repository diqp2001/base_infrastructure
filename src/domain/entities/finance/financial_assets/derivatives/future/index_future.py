from src.domain.entities.finance.financial_assets.index.index import Index
from src.domain.entities.finance.financial_assets.derivatives.future.future import Future


class IndexFuture(Future):
    """Future contract for a generic index."""
    def __init__(self, underlying_asset: Index, **kwargs):
        super().__init__(underlying_asset=underlying_asset,**kwargs)