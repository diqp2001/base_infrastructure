from sqlalchemy import MetaData
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict
import logging
from src.infrastructure.models.keys.finance.financial_assets.key_company_stock import KeyCompanyStock
from src.infrastructure.models import CompanyStock as CompanyStockModel
from src.domain.entities.finance.financial_assets.company_stock import CompanyStock as CompanyStockEntity

logger = logging.getLogger(__name__)




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

    def exists_by_id(self, company_stock_id: int) -> bool:
        """Check if a CompanyStock exists by ID."""
        return self.session.query(CompanyStockModel).filter(
            CompanyStockModel.id == company_stock_id
        ).first() is not None

    def add_bulk(self, domain_stocks: List[CompanyStockEntity], key_mappings: List[Dict]) -> List[CompanyStockEntity]:
        """
        Add multiple CompanyStock records in a single transaction.
        
        Args:
            domain_stocks: List of CompanyStock domain entities
            key_mappings: List of dictionaries containing key_id, key_value, and repo_id for each stock
            
        Returns:
            List of created CompanyStock domain entities
        """
        if len(domain_stocks) != len(key_mappings):
            raise ValueError("Number of stocks must match number of key mappings")
            
        try:
            created_stocks = []
            
            # Begin transaction
            with self.session.begin():
                for domain_stock, key_mapping in zip(domain_stocks, key_mappings):
                    key_id = key_mapping['key_id']
                    key_value = key_mapping['key_value']
                    repo_id = key_mapping['repo_id']
                    
                    # Check if stock already exists
                    existing_key = self.session.query(KeyCompanyStock).filter(
                        KeyCompanyStock.key_value == key_value,
                        KeyCompanyStock.key_id == key_id
                    ).first()
                    
                    if existing_key:
                        # Get existing stock
                        existing_stock = self.get_by_id(existing_key.company_stock_id)
                        created_stocks.append(existing_stock)
                        continue
                    
                    # Create new stock
                    new_stock = CompanyStockModel(domain_entity=domain_stock)
                    self.session.add(new_stock)
                    self.session.flush()  # Get the ID
                    
                    # Create key relationship
                    new_key_stock = KeyCompanyStock(
                        company_stock_id=new_stock.id,
                        repo_id=repo_id,
                        key_id=key_id,
                        key_value=key_value,
                        start_date=domain_stock.start_date,
                        end_date=domain_stock.end_date
                    )
                    self.session.add(new_key_stock)
                    
                    created_stocks.append(self._to_domain(new_stock))
                    
                # Commit all changes
                self.session.commit()
                
            logger.info(f"Successfully created {len(created_stocks)} company stocks in bulk")
            return created_stocks
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error in bulk add operation: {str(e)}")
            raise

    def add_bulk_from_dicts(self, company_dicts: List[Dict], key_mappings: List[Dict]) -> List[CompanyStockEntity]:
        """
        Create and add multiple companies from dictionaries.
        
        Args:
            company_dicts: List of dictionaries with company data
            key_mappings: List of dictionaries containing key_id, key_value, and repo_id
            
        Returns:
            List of created CompanyStock domain entities
        """
        domain_stocks = []
        for company_dict in company_dicts:
            domain_stock = CompanyStockEntity(
                id=company_dict.get('id'),
                ticker=company_dict['ticker'],
                exchange_id=company_dict['exchange_id'],
                company_id=company_dict['company_id'],
                start_date=company_dict['start_date'],
                end_date=company_dict['end_date']
            )
            domain_stocks.append(domain_stock)
            
        return self.add_bulk(domain_stocks, key_mappings)
