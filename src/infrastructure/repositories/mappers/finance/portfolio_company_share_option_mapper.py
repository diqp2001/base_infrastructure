"""
Mapper for converting between portfolio company share option domain entities and infrastructure models
"""
from typing import Optional

from src.domain.entities.finance.financial_assets.derivatives.option.portfolio_company_share_option import PortfolioCompanyShareOption
from infrastructure.models.finance.portfolio.portfolio_company_share_option import PortfolioCompanyShareOption
from src.domain.entities.finance.financial_assets.derivatives.option.option_type import OptionType


class PortfolioCompanyShareOptionMapper:
    """Mapper for converting between option entities and models"""

    def to_entity(self, model: Optional[PortfolioCompanyShareOption]) -> Optional[PortfolioCompanyShareOption]:
        """Convert PortfolioCompanyShareOptionModel to PortfolioCompanyShareOption entity"""
        if not model:
            return None

        # Create placeholder underlying - in real implementation you'd load from repository
        from src.domain.entities.finance.portfolio.portfolio_company_share import PortfolioCompanyShare
        
        underlying = PortfolioCompanyShare(
            id=model.underlying_id,
            start_date=model.start_date,
            end_date=model.end_date
        )

        # Convert string to OptionType enum
        option_type = OptionType.CALL if model.option_type.upper() == 'CALL' else OptionType.PUT

        return PortfolioCompanyShareOption(
            id=model.id,
            underlying=underlying,
            expiration_date=model.expiration_date,
            option_type=option_type,
            start_date=model.start_date,
            end_date=model.end_date
        )

    def to_model(self, entity: PortfolioCompanyShareOption) -> PortfolioCompanyShareOption:
        """Convert PortfolioCompanyShareOption entity to PortfolioCompanyShareOptionModel"""
        return PortfolioCompanyShareOption(
            id=entity.id,
            underlying_id=entity.underlying.id,
            company_id=1,  # Default - not tracked at entity level
            expiration_date=entity.expiration_date,
            option_type=entity.option_type.value,  # Convert enum to string
            exercise_style='American',  # Default - not tracked at entity level
            strike_id=None,  # Default - not tracked at entity level
            start_date=entity.start_date,
            end_date=entity.end_date
        )