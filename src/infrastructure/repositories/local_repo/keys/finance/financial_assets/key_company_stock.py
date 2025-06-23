from sqlalchemy.orm import Session
from src.infrastructure.models.keys.finance.financial_assets.key_company_stock import KeyCompanyStock

class KeyCompanyStockRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self):
        """Retrieve all KeyCompanyStock records from the database."""
        return self.session.query(KeyCompanyStock).all()

    def get_by_id(self, company_stock_id: int):
        """Retrieve a single KeyCompanyStock record by its Company Stock ID."""
        return self.session.query(KeyCompanyStock).filter(KeyCompanyStock.company_stock_id == company_stock_id).first()

    def add(self, company_stock_id: int, repo_id: int, key_id: int, key_value: int, start_date, end_date=None):
        """Add a new KeyCompanyStock record to the database."""
        #need to make sure it doesn't all ready exist
        new_key_company_stock = KeyCompanyStock(
            company_stock_id=company_stock_id,
            repo_id=repo_id,
            key_id=key_id,
            key_value=key_value,
            start_date=start_date,
            end_date=end_date
        )
        self.session.add(new_key_company_stock)
        self.session.commit()
        return new_key_company_stock

    def exists(self, company_stock_id: int, key_id: int):
        """Check if a KeyCompanyStock record exists with the given Company Stock ID and Key ID."""
        return self.session.query(KeyCompanyStock).filter(
            KeyCompanyStock.company_stock_id == company_stock_id,
            KeyCompanyStock.key_id == key_id
        ).first() is not None

    def update(self, company_stock_id: int, key_id: int, key_value: int, start_date, end_date=None):
        """Update an existing KeyCompanyStock record."""
        key_company_stock = self.session.query(KeyCompanyStock).filter(
            KeyCompanyStock.company_stock_id == company_stock_id,
            KeyCompanyStock.key_id == key_id
        ).first()

        if key_company_stock:
            key_company_stock.key_value = key_value
            key_company_stock.start_date = start_date
            key_company_stock.end_date = end_date
            self.session.commit()
            return key_company_stock
        return None

    def delete(self, company_stock_id: int, key_id: int):
        """Delete a KeyCompanyStock record."""
        key_company_stock = self.session.query(KeyCompanyStock).filter(
            KeyCompanyStock.company_stock_id == company_stock_id,
            KeyCompanyStock.key_id == key_id
        ).first()

        if key_company_stock:
            self.session.delete(key_company_stock)
            self.session.commit()
            return True
        return False

    def get_by_repo_id(self, repo_id: int):
        """Retrieve all KeyCompanyStock records by a specific Repo ID."""
        return self.session.query(KeyCompanyStock).filter(KeyCompanyStock.repo_id == repo_id).all()
