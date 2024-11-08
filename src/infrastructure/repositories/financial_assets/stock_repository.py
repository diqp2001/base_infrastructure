from src.infrastructure.models.financial_assets.stock import Stock
from src.domain.entities.financial_assets.financial_asset import FinancialAsset
from src.infrastructure.database.connections import get_database_session
from sqlalchemy.orm import Session

class StockRepository:
    def get_by_id(self, id: int) -> FinancialAsset:
        # Get a session from the database
        db: Session = get_database_session(db_type="sqlite")  # Or use other db types like "sql_server"
        try:
            # Perform the query
            return db.query(Stock).filter(Stock.id == id).first()
        finally:
            db.close()  # Ensure the session is closed after use

    def save(self, asset: FinancialAsset) -> None:
        # Get a session from the database
        db: Session = get_database_session(db_type="sqlite")  # Or use other db types like "sql_server"
        try:
            # Add the asset and commit
            db.add(asset)
            db.commit()
        finally:
            db.close()  # Ensure the session is closed after use