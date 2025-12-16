"""
Mapper for converting between PortfolioCompanyShareOption domain entities and infrastructure models.
Follows the established mapper pattern in the codebase.
"""

from datetime import datetime
from typing import Optional

from domain.entities.finance.financial_assets.derivatives.option.portfolio_company_share_option import PortfolioCompanyShareOption
from domain.entities.finance.financial_assets.derivatives.option.option_type import OptionType
from src.infrastructure.models.finance.financial_assets.portfolio_company_share_option import PortfolioCompanyShareOptionModel


class PortfolioCompanyShareOptionMapper:
    """Mapper for PortfolioCompanyShareOption entities."""
    
    @staticmethod
    def to_entity(model: PortfolioCompanyShareOptionModel) -> Optional[PortfolioCompanyShareOption]:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        
        # Convert option type
        option_type = OptionType.CALL
        try:
            option_type = OptionType(model.option_type.value) if model.option_type else OptionType.CALL
        except (ValueError, AttributeError):
            pass
        
        return PortfolioCompanyShareOption(
            id=model.id,
            underlying=None,  # Will need to be loaded separately
            company_id=model.company_id,
            expiration_date=model.expiration_date,
            option_type=option_type,
            exercise_style=model.exercise_style or 'American',
            strike_id=None,  # Derived from strike_price
            start_date=model.start_date,
            end_date=model.end_date
        )
    
    @staticmethod
    def to_model(entity: PortfolioCompanyShareOption) -> Optional[PortfolioCompanyShareOptionModel]:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return PortfolioCompanyShareOptionModel(
            id=getattr(entity, 'id', None),
            symbol=getattr(entity, 'symbol', ''),
            underlying_symbol=getattr(entity, 'underlying_symbol', ''),
            option_type=entity.option_type if hasattr(entity, 'option_type') else OptionType.CALL,
            portfolio_id=getattr(entity, 'portfolio_id', None),
            company_id=entity.company_id,
            strike_price=float(getattr(entity, 'strike_price', 0)) if hasattr(entity, 'strike_price') else 0.0,
            expiration_date=entity.expiration_date,
            exercise_style=entity.exercise_style or 'American',
            contract_size=getattr(entity, 'contract_size', 100),
            current_price=float(getattr(entity, 'current_price', 0)) if hasattr(entity, 'current_price') else 0.0,
            bid_price=float(entity.bid_price) if hasattr(entity, 'bid_price') and entity.bid_price else None,
            ask_price=float(entity.ask_price) if hasattr(entity, 'ask_price') and entity.ask_price else None,
            volume=getattr(entity, 'volume', None),
            open_interest=getattr(entity, 'open_interest', None),
            delta=float(entity.delta) if hasattr(entity, 'delta') and entity.delta else None,
            gamma=float(entity.gamma) if hasattr(entity, 'gamma') and entity.gamma else None,
            theta=float(entity.theta) if hasattr(entity, 'theta') and entity.theta else None,
            vega=float(entity.vega) if hasattr(entity, 'vega') and entity.vega else None,
            rho=float(entity.rho) if hasattr(entity, 'rho') and entity.rho else None,
            implied_volatility=float(entity.implied_volatility) if hasattr(entity, 'implied_volatility') and entity.implied_volatility else None,
            theoretical_value=float(entity.theoretical_value) if hasattr(entity, 'theoretical_value') and entity.theoretical_value else None,
            is_tradeable=getattr(entity, 'is_tradeable', True),
            is_american=getattr(entity, 'is_american', True),
            start_date=entity.start_date,
            end_date=entity.end_date,
            created_at=getattr(entity, 'created_at', datetime.now()),
            updated_at=getattr(entity, 'updated_at', datetime.now())
        )
    
    @staticmethod
    def update_model_from_entity(model: PortfolioCompanyShareOptionModel, 
                                entity: PortfolioCompanyShareOption) -> None:
        """Update an existing model with entity data."""
        if not model or not entity:
            return
        
        # Update basic fields
        model.symbol = getattr(entity, 'symbol', model.symbol)
        model.underlying_symbol = getattr(entity, 'underlying_symbol', model.underlying_symbol)
        model.option_type = entity.option_type if hasattr(entity, 'option_type') else model.option_type
        model.company_id = entity.company_id
        model.expiration_date = entity.expiration_date
        model.exercise_style = entity.exercise_style or model.exercise_style
        model.start_date = entity.start_date
        model.end_date = entity.end_date
        
        # Update market data if present
        if hasattr(entity, 'strike_price'):
            model.strike_price = float(entity.strike_price)
        if hasattr(entity, 'current_price'):
            model.current_price = float(entity.current_price)
        if hasattr(entity, 'bid_price') and entity.bid_price:
            model.bid_price = float(entity.bid_price)
        if hasattr(entity, 'ask_price') and entity.ask_price:
            model.ask_price = float(entity.ask_price)
        
        # Update Greeks if present
        if hasattr(entity, 'delta') and entity.delta:
            model.delta = float(entity.delta)
        if hasattr(entity, 'gamma') and entity.gamma:
            model.gamma = float(entity.gamma)
        if hasattr(entity, 'theta') and entity.theta:
            model.theta = float(entity.theta)
        if hasattr(entity, 'vega') and entity.vega:
            model.vega = float(entity.vega)
        if hasattr(entity, 'rho') and entity.rho:
            model.rho = float(entity.rho)
        
        # Update timestamps
        model.updated_at = datetime.now()