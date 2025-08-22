from sqlalchemy import MetaData
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict, Tuple, Optional
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

    def add_bulk(self, domain_stocks_with_keys: List[Tuple[CompanyStockEntity, int, int, int]]) -> List[CompanyStockEntity]:
        """
        Add multiple CompanyStock entities in a single transaction.
        
        Args:
            domain_stocks_with_keys: List of tuples containing (CompanyStockEntity, key_id, key_value, repo_id)
            
        Returns:
            List of added CompanyStockEntity objects
            
        Raises:
            Exception: If the bulk operation fails
        """
        if not domain_stocks_with_keys:
            return []
            
        try:
            # Use session transaction context
            with self.session.begin():
                added_stocks = []
                
                # First, check for existing stocks to avoid duplicates
                existing_keys = set()
                for _, key_id, key_value, _ in domain_stocks_with_keys:
                    existing_key = self.session.query(KeyCompanyStock).filter(
                        KeyCompanyStock.key_id == key_id,
                        KeyCompanyStock.key_value == key_value
                    ).first()
                    if existing_key:
                        existing_keys.add((key_id, key_value))
                        # Add existing stock to results
                        existing_stock = self.get_by_id(existing_key.company_stock_id)
                        if existing_stock:
                            added_stocks.append(existing_stock)
                
                # Filter out existing stocks
                new_stocks_data = [
                    (stock, key_id, key_value, repo_id) 
                    for stock, key_id, key_value, repo_id in domain_stocks_with_keys 
                    if (key_id, key_value) not in existing_keys
                ]
                
                if not new_stocks_data:
                    logger.info("All stocks already exist in database")
                    return added_stocks
                
                # Create CompanyStock models
                new_stock_models = []
                for domain_stock, _, _, _ in new_stocks_data:
                    stock_model = CompanyStockModel(domain_entity=domain_stock)
                    new_stock_models.append(stock_model)
                
                # Bulk add CompanyStock entities
                self.session.add_all(new_stock_models)
                self.session.flush()  # Get IDs for the new stocks
                
                # Create KeyCompanyStock relationships
                key_stock_models = []
                for i, (domain_stock, key_id, key_value, repo_id) in enumerate(new_stocks_data):
                    stock_model = new_stock_models[i]
                    key_stock = KeyCompanyStock(
                        company_stock_id=stock_model.id,
                        repo_id=repo_id,
                        key_id=key_id,
                        key_value=key_value,
                        start_date=domain_stock.start_date,
                        end_date=domain_stock.end_date
                    )
                    key_stock_models.append(key_stock)
                
                # Bulk add KeyCompanyStock relationships
                self.session.add_all(key_stock_models)
                
                # Convert new models to domain entities
                new_domain_stocks = [self._to_domain(stock) for stock in new_stock_models]
                added_stocks.extend(new_domain_stocks)
                
                logger.info(f"Successfully added {len(new_domain_stocks)} new company stocks in bulk")
                return added_stocks
                
        except Exception as e:
            logger.error(f"Error during bulk company stock addition: {str(e)}")
            self.session.rollback()
            raise

    def add_bulk_from_dicts(self, companies_data: List[Dict], key_mapping: Dict[str, Tuple[int, int, int]]) -> List[CompanyStockEntity]:
        """
        Create and add multiple CompanyStock entities from dictionary data.
        
        Args:
            companies_data: List of dictionaries containing company stock data
            key_mapping: Dictionary mapping ticker to (key_id, key_value, repo_id) tuples
            
        Returns:
            List of added CompanyStockEntity objects
        """
        domain_stocks_with_keys = []
        
        for company_data in companies_data:
            # Create domain entity
            domain_stock = CompanyStockEntity(**company_data)
            
            # Get key mapping for this ticker
            ticker = company_data.get('ticker')
            if ticker in key_mapping:
                key_id, key_value, repo_id = key_mapping[ticker]
                domain_stocks_with_keys.append((domain_stock, key_id, key_value, repo_id))
            else:
                logger.warning(f"No key mapping found for ticker: {ticker}")
        
        return self.add_bulk(domain_stocks_with_keys)

    def exists_by_id(self, company_stock_id: int) -> bool:
        """Check if a CompanyStock exists by ID."""
        return self.session.query(CompanyStockModel).filter(
            CompanyStockModel.id == company_stock_id
        ).first() is not None
