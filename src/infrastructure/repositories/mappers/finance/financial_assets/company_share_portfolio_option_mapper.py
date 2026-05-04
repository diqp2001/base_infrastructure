"""
Mapper for converting between portfolio company share option domain entities and infrastructure models
"""
from typing import Optional

from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_portfolio_option import CompanySharePortfolioOptionModel
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_portfolio_option import CompanySharePortfolioOption



class CompanySharePortfolioOptionMapper:
    """Mapper for converting between option entities and models"""

    def to_entity(self, model: Optional[CompanySharePortfolioOptionModel]) -> Optional[CompanySharePortfolioOptionModel]:
        """Convert PortfolioCompanyShareOptionDerivativeModel to PortfolioCompanyShareOption entity"""
        if not model:
            return None

        # Create placeholder underlying - in real implementation you'd load from repository
        from domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
        
        underlying = CompanySharePortfolio(
            id=model.underlying_id,
            start_date=model.start_date,
            end_date=model.end_date
        )

        # Convert string to OptionType enum
        option_type = model.option_type

        return CompanySharePortfolioOptionModel(
            id=model.id,
            underlying=underlying,
            expiration_date=model.expiration_date,
            option_type=option_type,
            start_date=model.start_date,
            end_date=model.end_date
        )

    def to_model(self, entity: CompanySharePortfolioOptionModel) -> CompanySharePortfolioOptionModel:
        """Convert PortfolioCompanyShareOption entity to PortfolioCompanyShareOptionDerivativeModel"""
        return CompanySharePortfolioOptionModel(
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