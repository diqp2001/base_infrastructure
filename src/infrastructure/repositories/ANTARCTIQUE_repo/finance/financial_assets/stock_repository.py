from infrastructure.repositories.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.stock import Stock as Stock_Model
from src.domain.entities.finance.financial_assets.stock import Stock as Stock_Entity


"""Provides an abstraction layer for database interaction."""
### StockRepository (inherits from FinancialAssetRepository)
from src.infrastructure.models.finance.financial_assets.stock import Stock as Stock_Model
from src.domain.entities.finance.financial_assets.stock import Stock as Stock_Entity

class StockRepository(FinancialAssetRepository):
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    
    def get_by_id(self, id: int) -> Stock_Entity:
        """Fetches a Stock asset by its ID."""
        try:
            return self.db.query(Stock_Model).filter(Stock_Model.id == id).first()
        except Exception as e:
            print(f"Error retrieving stock by ID: {e}")
            return None
        finally:
            self.db.close()

    def save_list(self, list_stock_entity,db) -> None:
        try:
            # Add the asset and commit
            for stock_entity in list_stock_entity:
                db.add(stock_entity)
            db.commit()
        except Exception as e:
            db.rollback()  # Rollback in case of an error
            print(f"An error occurred while saving: {e}")
        #finally:
            #db.close()  # Ensure the session is closed after use