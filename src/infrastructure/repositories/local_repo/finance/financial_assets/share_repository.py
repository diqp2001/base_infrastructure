from .financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.share import Share as ShareModel
from src.domain.entities.finance.financial_assets.share import Share as ShareEntity


class ShareRepository(FinancialAssetRepository):
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    
    def get_by_id(self, id: int) -> ShareEntity:
        """Fetches a Share asset by its ID."""
        try:
            return self.db.query(ShareModel).filter(ShareModel.id == id).first()
        except Exception as e:
            print(f"Error retrieving share by ID: {e}")
            return None
        finally:
            self.db.close()

    def save_list(self, list_share_entity, db) -> None:
        try:
            # Add the asset and commit
            for share_entity in list_share_entity:
                db.add(share_entity)
            db.commit()
        except Exception as e:
            db.rollback()  # Rollback in case of an error
            print(f"An error occurred while saving: {e}")
            
    def exists_by_id(self, id: int) -> bool:
        """Checks if a share exists by its ID."""
        try:
            # Query the database to check if a share with the given ID exists
            share = self.db.query(ShareModel).filter(ShareModel.id == id).first()
            return share is not None  # If no share is found, returns False
        except Exception as e:
            print(f"Error checking if share exists by ID: {e}")
            return False