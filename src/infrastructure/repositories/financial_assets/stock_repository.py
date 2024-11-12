from src.infrastructure.models.financial_assets.stock import Stock as Stock_Model
from src.domain.entities.financial_assets.stock import Stock as Stock_Entity
from src.infrastructure.database.connections import get_database_session
from sqlalchemy.orm import Session

class StockRepository:
    def get_by_id(self, id: int) -> Stock_Entity:
        # Get a session from the database
        db: Session = get_database_session(db_type="sqlite")  # Or use other db types like "sql_server"
        try:
            # Perform the query
            return db.query(Stock_Model).filter(Stock_Model.id == id).first()
        finally:
            db.close()  # Ensure the session is closed after use

    def save(self, asset: Stock_Entity) -> None:
        # Get a session from the database
        db: Session = get_database_session(db_type="sqlite")  # Or use other db types like "sql_server"
        try:
            # Add the asset and commit
            db.add(asset)
            db.commit()
        finally:
            db.close()  # Ensure the session is closed after use