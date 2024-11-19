from sqlalchemy.orm import Session
from abc import ABC, abstractmethod


class FinancialAssetRepository(ABC):
    def __init__(self, db_session):
        self.db = db_session

    @abstractmethod
    def get_by_id(self, id: int):
        """Abstract method to get an asset by its ID."""
        pass

    def save(self, asset) -> None:
        """Saves a single asset to the database."""
        try:
            self.db.add(asset)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error saving asset: {e}")
        finally:
            self.db.close()

    def save_list(self, asset_list) -> None:
        """Saves a list of assets to the database."""
        try:
            for asset in asset_list:
                self.db.add(asset)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error saving asset list: {e}")

    '''def exists_by_id(self, id: int) -> bool:
        """Checks if a stock exists by its ID."""
        try:
            # Query the database to check if a stock with the given ID exists
            asset = self.db.query(CompanyStock_Model).filter(CompanyStock_Model.id == id).first()
            return asset is not None  # If no stock is found, returns False
        except Exception as e:
            print(f"Error checking if stock exists by ID: {e}")
            return False'''

    def close_session(self):
        """Closes the database session."""
        self.db.close()

