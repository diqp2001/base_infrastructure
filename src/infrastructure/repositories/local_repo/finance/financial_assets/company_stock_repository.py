from sqlalchemy import MetaData
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.infrastructure.models.keys.finance.financial_assets.key_company_stock import KeyCompanyStock
from src.infrastructure.models import CompanyStock as CompanyStockModel
from src.domain.entities.finance.financial_assets.company_stock import CompanyStock as CompanyStockEntity




class CompanyStockRepository:
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, infra_stock: CompanyStockModel) -> CompanyStockEntity:
        """Convert an infrastructure CompanyStock to a domain CompanyStock."""
        if not infra_stock:
            return None
        return CompanyStockEntity(
            id=infra_stock.id,
            ticker=infra_stock.ticker,
            exchange_id=infra_stock.exchange_id,
            company_id=infra_stock.company_id,
            start_date=infra_stock.start_date,
            end_date=infra_stock.end_date,
        )

    def get_all(self):
        """Retrieve all CompanyStock records from the database."""
        stocks = self.session.query(CompanyStockModel).all()
        return [self._to_domain(stock) for stock in stocks]

    def get_by_id(self, company_stock_id: int):
        """Retrieve a CompanyStock record by its ID."""
        stock = self.session.query(CompanyStockModel).filter(
            CompanyStockModel.id == company_stock_id
        ).first()
        return self._to_domain(stock)

    def exists(self, key_value: int, key_id: int):
        """
        Check if a CompanyStock exists in the database by cross-referencing with KeyCompanyStock.
        """
        return self.session.query(KeyCompanyStock).filter(
            KeyCompanyStock.key_value == key_value,
            KeyCompanyStock.key_id == key_id
        ).first() is not None

    def add(self, domain_stock: CompanyStockEntity, key_id: int, key_value: int, repo_id: int):
        """
        Add a new CompanyStock record to the database.
        Verify if the stock already exists by cross-referencing KeyCompanyStock.
        """
        # Check if the stock exists in the repository
        existing_stock = self.session.query(KeyCompanyStock).filter(
            KeyCompanyStock.key_value == key_value,
            KeyCompanyStock.key_id == key_id
        ).first()

        if existing_stock:
            # Return the associated CompanyStock if it already exists
            return self.get_by_id(existing_stock.company_stock_id)

        # Convert domain entity to infrastructure model and add it
        new_stock = CompanyStockModel(domain_entity=domain_stock)
        self.session.add(new_stock)
        self.session.flush()  # Get the new stock ID before committing

        # Create a corresponding KeyCompanyStock
        new_key_company_stock = KeyCompanyStock(
            company_stock_id=new_stock.id,
            repo_id=repo_id,
            key_id=key_id,
            key_value=key_value,
            start_date=domain_stock.start_date,
            end_date=domain_stock.end_date
        )
        self.session.add(new_key_company_stock)
        self.session.commit()

        return self._to_domain(new_stock)

    def update(self, company_stock_id: int, **kwargs):
        """
        Update an existing CompanyStock record.
        """
        stock = self.session.query(CompanyStockModel).filter(
            CompanyStockModel.id == company_stock_id
        ).first()
        if not stock:
            return None

        # Update attributes dynamically
        for attr, value in kwargs.items():
            if hasattr(stock, attr):
                setattr(stock, attr, value)

        self.session.commit()
        return self._to_domain(stock)

    def delete(self, company_stock_id: int):
        """
        Delete a CompanyStock record and its associated KeyCompanyStock records.
        """
        stock = self.session.query(CompanyStockModel).filter(
            CompanyStockModel.id == company_stock_id
        ).first()
        if not stock:
            return False

        # Delete associated KeyCompanyStock records
        self.session.query(KeyCompanyStock).filter(
            KeyCompanyStock.company_stock_id == company_stock_id
        ).delete()

        # Delete the CompanyStock
        self.session.delete(stock)
        self.session.commit()
        return True

    def get_by_ticker(self, ticker: str):
        """Retrieve CompanyStock records by ticker."""
        stocks = self.session.query(CompanyStockModel).filter(
            CompanyStockModel.ticker == ticker
        ).all()
        return [self._to_domain(stock) for stock in stocks]

    def get_by_key(self, key_id: int, key_value: int):
        """
        Retrieve a CompanyStock by key_id and key_value using KeyCompanyStock.
        """
        key_stock = self.session.query(KeyCompanyStock).filter(
            KeyCompanyStock.key_id == key_id,
            KeyCompanyStock.key_value == key_value
        ).first()

        if key_stock:
            return self.get_by_id(key_stock.company_stock_id)
        return None
