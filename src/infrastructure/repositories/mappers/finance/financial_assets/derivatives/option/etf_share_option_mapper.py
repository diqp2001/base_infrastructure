"""
Mapper for ETFShareOption domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from src.domain.entities.finance.financial_assets.derivatives.option.etf_share_option import ETFShareOption as DomainETFShareOption
from src.infrastructure.models.finance.financial_assets.derivative.option.etf_share_option import ETFShareOptionModel as ORMETFShareOption
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.option.share_option_mapper import ShareOptionMapper


class ETFShareOptionMapper(ShareOptionMapper):
    """Mapper for ETFShareOption domain entity and ORM model."""
    domain_class = DomainETFShareOption
    orm_class = ORMETFShareOption
    DISCRIMINATOR = 'ETFShareOption'
