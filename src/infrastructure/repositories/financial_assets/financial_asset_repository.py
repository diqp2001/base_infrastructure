from sqlalchemy.orm import Session
from abc import ABC, abstractmethod
from src.infrastructure.database.connections import get_database_session

class FinancialAssetRepository(ABC):
    def __init__(self, db_type='sqlite'):
        self.db_type = db_type
        self.db: Session = get_database_session(db_type)

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
        finally:
            self.db.close()

    def close_session(self):
        """Closes the database session."""
        self.db.close()

