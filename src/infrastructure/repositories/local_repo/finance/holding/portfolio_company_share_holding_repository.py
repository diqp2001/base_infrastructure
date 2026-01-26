from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.domain.ports.finance.holding.portfolio_company_share_holding_port import PortfolioCompanyShareHoldingPort
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding
from src.infrastructure.models.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHoldingModel
from src.infrastructure.repositories.mappers.finance.holding.portfolio_company_share_holding_mapper import PortfolioCompanyShareHoldingMapper


class PortfolioCompanyShareHoldingRepository(BaseLocalRepository, PortfolioCompanyShareHoldingPort):
    """Repository for portfolio company share holding entities"""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = PortfolioCompanyShareHoldingMapper()

    def get_by_id(self, holding_id: int) -> Optional[PortfolioCompanyShareHoldingModel]:
        """Get a portfolio company share holding by ID"""
        model = self.session.query(PortfolioCompanyShareHoldingModel).filter_by(id=holding_id).first()
        return self.mapper.to_entity(model) if model else None

    def get_by_portfolio_company_share_id(self, portfolio_id: int) -> List[PortfolioCompanyShareHoldingModel]:
        """Get all company share holdings for a specific portfolio company share"""
        models = self.session.query(PortfolioCompanyShareHoldingModel).filter_by(
            portfolio_company_share_id=portfolio_id
        ).all()
        return [self.mapper.to_entity(model) for model in models]

    def save(self, holding: PortfolioCompanyShareHoldingModel) -> PortfolioCompanyShareHoldingModel:
        """Save or update a portfolio company share holding"""
        model = self.mapper.to_model(holding)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)

    def get_or_create(self, primary_key: str, **kwargs) -> Optional[PortfolioCompanyShareHolding]:
        """
        Get or create a portfolio company share holding with dependency resolution.
        
        Args:
            primary_key: Combination of portfolio_company_share_id and holding_date
            **kwargs: Additional parameters for entity creation
            
        Returns:
            PortfolioCompanyShareHolding entity or None if creation failed
        """
        try:
            # Parse primary key - expecting format "portfolio_id_date"
            parts = primary_key.split('_', 1)
            if len(parts) != 2:
                print(f"Invalid primary key format: {primary_key}. Expected format: 'portfolio_id_date'")
                return None
                
            portfolio_company_share_id = int(parts[0])
            holding_date_str = parts[1]
            
            # Check if holding already exists
            existing = self.session.query(PortfolioCompanyShareHoldingModel).filter_by(
                portfolio_company_share_id=portfolio_company_share_id,
                date=holding_date_str
            ).first()
            
            if existing:
                return self.mapper.to_entity(existing)
            
            # Create new portfolio company share holding with defaults
            from datetime import datetime
            holding_date = datetime.strptime(holding_date_str, '%Y-%m-%d').date()
            
            new_holding = PortfolioCompanyShareHolding(
                portfolio_company_share_id=portfolio_company_share_id,
                date=holding_date,
                quantity=kwargs.get('quantity', 0),
                average_price=kwargs.get('average_price', 0.0),
                market_value=kwargs.get('market_value', 0.0),
                unrealized_pnl=kwargs.get('unrealized_pnl', 0.0)
            )
            
            return self.save(new_holding)
            
        except Exception as e:
            print(f"Error in get_or_create for portfolio company share holding {primary_key}: {e}")
            return None