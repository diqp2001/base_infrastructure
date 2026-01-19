from src.domain.entities.finance.financial_assets.commodity import Commodity
from src.domain.entities.finance.financial_assets.derivatives.future.future import Future


class CommodityFuture(Future):
    """Future contract for a commodity."""
    def __init__(self, underlying_asset: Commodity, **kwargs):
        super().__init__(underlying_asset=underlying_asset,**kwargs)