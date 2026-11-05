"""
Mapper for CompanyShareOption domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption as DomainCompanyShareOption
from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import CompanyShareOptionModel as ORMCompanyShareOption
from src.infrastructure.repositories.mappers.finance.financial_assets.derivatives.option.share_option_mapper import ShareOptionMapper


class CompanyShareOptionMapper(ShareOptionMapper):
    """Mapper for CompanyShareOption domain entity and ORM model."""
    domain_class = DomainCompanyShareOption
    orm_class = ORMCompanyShareOption
    DISCRIMINATOR = 'CompanyShareOption'
