


from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture


class EquityIndexFuture(IndexFuture):
    """Future contract for an equity index."""
    def __init__(self, equity_index_id: int, **kwargs):
        super().__init__(index_id=equity_index_id, **kwargs)
        self.equity_index_id = equity_index_id  # specialized link