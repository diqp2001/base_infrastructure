"""
ETFShareOption Repository for local database operations.
The logic common to options on a share lives in ShareOptionRepository.

Legs: the constituent options of the ETF option's dispersion strategy (the options that replicate its holdings) are
the UniverseConstituent rows of the Universe "<option symbol> legs" (weight, start_date, end_date) - point in time,
like an ETF share's holdings. While legs are in force they are the option's related entities (the strategy factors'
per-entity inputs); otherwise the underlying share and currency (ShareOptionRepository).
"""

from datetime import date

from src.domain.ports.finance.financial_assets.derivatives.option.etf_share_option_port import ETFShareOptionPort
from src.infrastructure.models.finance.financial_assets.etf_share import ETFShareModel
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.option.etf_share_option_mapper import ETFShareOptionMapper
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.option.share_option_repository import ShareOptionRepository


class ETFShareOptionRepository(ShareOptionRepository, ETFShareOptionPort):
    """Repository for ETF share option operations in the local database."""

    mapper_class = ETFShareOptionMapper
    underlying_model = ETFShareModel
    underlying_repository_key = 'ETFShare'

    @staticmethod
    def legs_universe_name(symbol: str) -> str:
        """The Universe holding an ETF option's dispersion legs (the constituent options)."""
        return f"{symbol} legs"

    def get_by_id(self, option_id: int):
        orm_option = self.session.query(self.model_class).filter(self.model_class.id == option_id).one_or_none()
        return self.mapper.to_domain(orm_option) if orm_option else None

    def _legs(self, option_id: int, target_date) -> list:
        """The UniverseConstituent rows of the option's legs universe in force on target_date."""
        option = self.get_by_id(option_id)
        if option is None or self.factory is None:
            return []
        universe = self.factory.get_local_repository('InvestmentUniverse').get_by_name(
            self.legs_universe_name(option.symbol))
        if universe is None:
            return []
        day = target_date.date() if hasattr(target_date, 'date') and callable(target_date.date) else target_date
        return self.factory.get_local_repository('UniverseConstituent').get_active_by_universe(
            universe.id, day or date.today())

    def _leg_entities(self, option_id: int, target_date) -> list:
        out = []
        for row in self._legs(option_id, target_date):
            repo = self.factory.get_local_repository(row.entity_type)
            entity = repo.get_by_id(row.entity_id) if repo is not None else None
            if entity is not None:
                out.append((row, entity))
        return out

    def get_related_entities(self, option_id: int, target_date=None) -> list:
        """The legs in force on target_date; without legs, the underlying share and currency."""
        legs = [entity for _, entity in self._leg_entities(option_id, target_date)]
        return legs or super().get_related_entities(option_id)

    def get_related_weights(self, option_id: int, target_date=None) -> dict:
        """{leg option symbol: weight} of the legs in force on target_date (not normalized); {} without legs."""
        return {entity.symbol: float(row.weight) for row, entity in self._leg_entities(option_id, target_date)
                if row.weight is not None}
