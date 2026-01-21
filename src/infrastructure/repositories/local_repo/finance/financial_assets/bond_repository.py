
import logging
from typing import Optional
from src.domain.ports.finance.financial_assets.bond_port import BondPort
from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.bond import BondModel as Bond_Model
from src.domain.entities.finance.financial_assets.bond import Bond as Bond_Entity
from src.infrastructure.repositories.mappers.finance.financial_assets.bond_mapper import BondMapper
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class BondRepository(FinancialAssetRepository,BondPort):
    def __init__(self, session: Session, factory):
        """Initialize BondRepository with database session."""
        super().__init__(session)
        self.factory = factory
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Bond."""
        return Bond_Model
    
    @property
    def entity_class(self):
        """Return the domain entity class for Bond."""
        return Bond_Entity
    
    def _to_entity(self, infra_bond: Bond_Model) -> Bond_Entity:
        """Convert an infrastructure Bond to a domain Bond using mapper."""
        if not infra_bond:
            return None
        return BondMapper.to_domain(infra_bond)
    
    def _to_model(self, entity: Bond_Entity) -> Bond_Model:
        """Convert domain entity to ORM model."""
        return BondMapper.to_orm(entity)
    
    def _to_domain(self, infra_bond: Bond_Model) -> Bond_Entity:
        """Legacy method - delegates to _to_entity."""
        return self._to_entity(infra_bond)
    
    def get_by_id(self, id: int) -> Bond_Entity:
        """Fetches a Bond asset by its ID."""
        try:
            bond = self.session.query(Bond_Model).filter(Bond_Model.id == id).first()
            return self._to_domain(bond)
        except Exception as e:
            print(f"Error retrieving bond by ID: {e}")
            return None
    
    def get_by_isin(self, isin: str) -> Bond_Entity:
        """Retrieve bond by ISIN."""
        try:
            bond = self.session.query(Bond_Model).filter(Bond_Model.isin == isin).first()
            return self._to_domain(bond)
        except Exception as e:
            print(f"Error retrieving bond by ISIN {isin}: {e}")
            return None
    
    def get_by_cusip(self, cusip: str) -> Bond_Entity:
        """Retrieve bond by CUSIP."""
        try:
            bond = self.session.query(Bond_Model).filter(Bond_Model.cusip == cusip).first()
            return self._to_domain(bond)
        except Exception as e:
            print(f"Error retrieving bond by CUSIP {cusip}: {e}")
            return None
    
    def get_or_create(self, isin: str = None, cusip: str = None, ticker: str = None,
                      name: str = None, currency_code: str = "USD") -> Optional[Bond_Entity]:
        """
        Get or create a bond with dependency resolution.
        
        Args:
            isin: International Securities Identification Number
            cusip: CUSIP identifier
            ticker: Bond ticker symbol
            name: Bond name
            currency_code: Currency ISO code (default: USD)
            
        Returns:
            Bond entity or None if creation failed
        """
        try:
            # First try to get existing bond by ISIN, CUSIP, or ticker
            if isin:
                existing = self.get_by_isin(isin)
                if existing:
                    return existing
            if cusip:
                existing = self.get_by_cusip(cusip)
                if existing:
                    return existing
            if ticker:
                existing = self.get_by_ticker(ticker)
                if existing:
                    return existing
            
            # Get or create currency dependency
            currency_local_repo = self.factory.currency_local_repo
            currency = currency_local_repo.get_or_create(iso_code=currency_code)
            
            # Create new bond
            new_bond = Bond_Entity(
                isin=isin,
                cusip=cusip,
                ticker=ticker or isin or cusip,
                name=name or f"Bond {ticker or isin or cusip}"
            )
            
            # Set currency_id if the entity supports it
            if hasattr(new_bond, 'currency_id') and currency:
                new_bond.currency_id = currency.asset_id
            
            return self.add(new_bond)
            
        except Exception as e:
            logger.error(f"Error in get_or_create for bond {isin or cusip or ticker}: {e}")
            return None

    def add(self, domain_bond: Bond_Entity) -> Bond_Entity:
        """Add a new Bond record to the database."""
        try:
            # Convert domain entity to infrastructure model using mapper
            new_bond = BondMapper.to_orm(domain_bond)
            self.session.add(new_bond)
            self.session.commit()
            self.session.refresh(new_bond)
            return self._to_domain(new_bond)
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding bond: {e}")
            return None
