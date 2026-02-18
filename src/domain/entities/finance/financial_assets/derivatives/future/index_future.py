from src.domain.entities.finance.financial_assets.derivatives.future.future import Future


class IndexFuture(Future):
    """Future contract for a generic index."""
    def __init__(self, underlying_index: str = None, **kwargs):
        # Map underlying_index to underlying_asset_id if provided
        if underlying_index:
            kwargs['underlying_asset_id'] = kwargs.get('underlying_asset_id', None)
        super().__init__(**kwargs)
        self.underlying_index = underlying_index