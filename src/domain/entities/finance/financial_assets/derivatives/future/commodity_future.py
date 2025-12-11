from domain.entities.finance.financial_assets.derivatives.future.future import Future


class CommodityFuture(Future):
    """Future contract for a commodity."""
    def __init__(self, commodity_id: int, **kwargs):
        super().__init__(**kwargs)
        self.commodity_id = commodity_id  # link to commodity entity
