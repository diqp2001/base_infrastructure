"""
ETFShareOption Repository for local database operations.
The logic common to options on a share lives in ShareOptionRepository.
"""

from src.domain.ports.finance.financial_assets.derivatives.option.etf_share_option_port import ETFShareOptionPort
from src.infrastructure.models.finance.financial_assets.etf_share import ETFShareModel
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.option.etf_share_option_mapper import ETFShareOptionMapper
from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.option.share_option_repository import ShareOptionRepository


class ETFShareOptionRepository(ShareOptionRepository, ETFShareOptionPort):
    """Repository for ETF share option operations in the local database."""

    mapper_class = ETFShareOptionMapper
    underlying_model = ETFShareModel
    underlying_repository_key = 'ETFShare'
