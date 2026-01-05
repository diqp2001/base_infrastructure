from typing import Optional
from sqlalchemy.orm import Session

from src.infrastructure.repositories.local_repo.finance.financial_assets.future_repository import (
    FutureRepository
)
from src.domain.entities.finance.financial_assets.derivatives.future.future import (
    Future as Future_Entity
)


class IndexFutureRepository(FutureRepository):
    """
    Repository for INDEX Future instruments (e.g., ES, NQ, RTY).
    Specialization of FutureRepository.
    """

    def __init__(self, session: Session):
        super().__init__(session)

    # ------------------------------------------------------------------
    # Index-specific queries
    # ------------------------------------------------------------------

    def get_by_index_symbol(self, symbol: str) -> Optional[Future_Entity]:
        """
        Fetch an INDEX future by symbol.
        Ensures future_type = 'INDEX'.
        """
        future = self.get_by_symbol(symbol)

        if future and future.future_type == "INDEX":
            return future

        return None

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    def create_or_get_index_future(
        self,
        symbol: str,
        underlying_index: str,
        exchange: str = "CME",
        currency: str = "USD",
        contract_name: Optional[str] = None,
        **kwargs
    ) -> Future_Entity:
        """
        Create or retrieve an INDEX future.

        Args:
            symbol: Future symbol (e.g., 'ESZ5')
            underlying_index: Underlying index (e.g., 'SPX')
            exchange: Exchange (default CME)
            currency: Currency (default USD)
            contract_name: Optional explicit contract name
            **kwargs: Additional Future parameters

        Returns:
            Future_Entity
        """
        return self._create_or_get(
            symbol=symbol,
            contract_name=contract_name or f"{symbol} Index Future",
            future_type="INDEX",
            underlying_asset=underlying_index,
            exchange=exchange,
            currency=currency,
            **kwargs,
        )
