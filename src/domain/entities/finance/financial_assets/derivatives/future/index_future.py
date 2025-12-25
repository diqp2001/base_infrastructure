from src.domain.entities.finance.financial_assets.derivatives.future.future import Future


class IndexFuture(Future):
    """Future contract for a generic index."""
    def __init__(self, index_id: int, **kwargs):
        super().__init__(**kwargs)
        self.index_id = index_id  # link to index entity