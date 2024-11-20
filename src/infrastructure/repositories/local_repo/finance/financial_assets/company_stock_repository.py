from .financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models import CompanyStock as CompanyStock_Model
from src.domain.entities.finance.financial_assets.company_stock import CompanyStock as CompanyStock_Entity




class CompanyStockRepository(FinancialAssetRepository):
    def __init__(self, db_session):
        super().__init__(db_session)

    
    def get_by_id(self, id: int) -> CompanyStock_Entity:
        """Fetches a Stock asset by its ID."""
        try:
            return self.db.query(CompanyStock_Model).filter(CompanyStock_Model.id == id).first()
        except Exception as e:
            print(f"Error retrieving stock by ID: {e}")
            return None
        finally:
            self.db.close()

    def save_list(self, list_company_stock_entity) -> None:
        
        try:
            # Add the asset and commit
            for company_stock_entity in list_company_stock_entity:
                company_stock_model = CompanyStock_Model(company_stock_entity)
                self.db.add(company_stock_model)
            self.db.commit()
        except Exception as e:
            self.db.rollback()  # Rollback in case of an error
            print(f"An error occurred while saving: {e}")
            
    def exists_by_id(self, id: int) -> bool:
        """Checks if a stock exists by its ID."""
        try:
            # Query the database to check if a stock with the given ID exists
            company_stock = self.db.query(CompanyStock_Model).filter(CompanyStock_Model.id == id).first()
            return company_stock is not None  # If no stock is found, returns False
        except Exception as e:
            print(f"Error checking if stock exists by ID: {e}")
            return False