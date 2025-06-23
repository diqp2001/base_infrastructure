from financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.bond import Bond as Bond_Model
from src.domain.entities.finance.financial_assets.bond import Bond as Bond_Entity

class BondRepository(FinancialAssetRepository):
    def get_by_id(self, id: int) -> Bond_Entity:
        """Fetches a Bond asset by its ID."""
        try:
            return self.db.query(Bond_Model).filter(Bond_Model.id == id).first()
        except Exception as e:
            print(f"Error retrieving bond by ID: {e}")
            return None
        finally:
            self.db.close()
