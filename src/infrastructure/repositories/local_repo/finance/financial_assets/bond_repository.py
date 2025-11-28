from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_base_repository import FinancialAssetBaseRepository
from src.infrastructure.models.finance.financial_assets.bond import Bond as Bond_Model
from src.domain.entities.finance.financial_assets.bond import Bond as Bond_Entity
from src.infrastructure.repositories.mappers.finance.financial_assets.bond_mapper import BondMapper
from sqlalchemy.orm import Session

class BondRepository(FinancialAssetBaseRepository):
    def __init__(self, session: Session):
        """Initialize BondRepository with database session."""
        super().__init__(session)
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Bond."""
        return Bond_Model
    
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
            print(f"Error adding bond: {e}")
            return None
