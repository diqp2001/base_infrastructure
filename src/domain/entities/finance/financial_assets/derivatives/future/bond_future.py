from src.domain.entities.finance.financial_assets.derivatives.future.future import Future


class BondFuture(Future):
    """Future contract for a bond."""
    def __init__(self, bond_id: int, **kwargs):
        super().__init__(**kwargs)
        self.bond_id = bond_id  # link to bond entity