"""Enhanced CompanyStockRepository with bulk operations and improved transaction management."""
import logging
from typing import List, Dict, Optional, Any
from sqlalchemy import MetaData
from sqlalchemy.orm import Session
from sqlalchemy import or_
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
        """Check if a CompanyStock exists by its ID."""
        return self.session.query(CompanyStockModel).filter(
            CompanyStockModel.id == company_stock_id
        ).first() is not None
    
    def add_bulk(self, domain_stocks: List[CompanyStockEntity], key_mappings: List[Dict[str, Any]]) -> List[CompanyStockEntity]:
        """
        Add multiple CompanyStock entities in a single atomic transaction.
        
        Args:
            domain_stocks: List of CompanyStock domain entities to add
            key_mappings: List of dictionaries containing key_id, key_value, repo_id for each stock
            
        Returns:
            List of created CompanyStock entities
            
        Raises:
            ValueError: If input validation fails
            Exception: If database operation fails
        """
        if not domain_stocks or not key_mappings:
            raise ValueError("Domain stocks and key mappings cannot be empty")
            
        if len(domain_stocks) != len(key_mappings):
            raise ValueError("Number of domain stocks must match number of key mappings")
        
        try:
            with self.session.begin():
                created_stocks = []
                
                for domain_stock, key_mapping in zip(domain_stocks, key_mappings):
                    key_id = key_mapping['key_id']
                    key_value = key_mapping['key_value']
                    repo_id = key_mapping['repo_id']
                    
                    # Check if stock already exists
                    existing_stock = self.session.query(KeyCompanyStock).filter(
                        KeyCompanyStock.key_value == key_value,
                        KeyCompanyStock.key_id == key_id
                    ).first()
                    
                    if existing_stock:
                        # Return existing stock
                        existing_domain_stock = self.get_by_id(existing_stock.company_stock_id)
                        created_stocks.append(existing_domain_stock)
                        logger.info(f"Stock {domain_stock.ticker} already exists, skipping creation")
                        continue
                    
                    # Create new stock
                    new_stock = CompanyStockModel(domain_entity=domain_stock)
                    self.session.add(new_stock)
                    self.session.flush()  # Get the new stock ID
                    
                    # Create corresponding KeyCompanyStock
                    new_key_company_stock = KeyCompanyStock(
                        company_stock_id=new_stock.id,
                        repo_id=repo_id,
                        key_id=key_id,
                        key_value=key_value,
                        start_date=domain_stock.start_date,
                        end_date=domain_stock.end_date
                    )
                    self.session.add(new_key_company_stock)
                    
                    created_stocks.append(self._to_domain(new_stock))
                    
                logger.info(f"Successfully created {len(created_stocks)} company stocks in bulk operation")
                return created_stocks
                
        except Exception as e:
            logger.error(f"Error in bulk add operation: {str(e)}")
            raise
    
    def add_bulk_from_dicts(self, company_dicts: List[Dict[str, Any]], key_mappings: List[Dict[str, Any]]) -> List[CompanyStockEntity]:
        """
        Create and add multiple CompanyStock entities from dictionary data.
        
        Args:
            company_dicts: List of dictionaries containing stock data
            key_mappings: List of dictionaries containing key_id, key_value, repo_id
            
        Returns:
            List of created CompanyStock entities
        """
        if not company_dicts or not key_mappings:
            raise ValueError("Company dicts and key mappings cannot be empty")
            
        try:
            # Convert dictionaries to domain entities
            domain_stocks = []
            for stock_data in company_dicts:
                # Ensure required fields are present
                required_fields = ['id', 'ticker', 'exchange_id', 'company_id', 'start_date']
                for field in required_fields:
                    if field not in stock_data:
                        raise ValueError(f"Missing required field '{field}' in stock data")
                
                domain_stock = CompanyStockEntity(**stock_data)
                domain_stocks.append(domain_stock)
            
            return self.add_bulk(domain_stocks, key_mappings)
            
        except Exception as e:
            logger.error(f"Error creating CompanyStock entities from dictionaries: {str(e)}")
            raise
    
    def delete_bulk(self, company_stock_ids: List[int]) -> int:
        """
        Delete multiple CompanyStock records and their associated KeyCompanyStock records.
        
        Args:
            company_stock_ids: List of company stock IDs to delete
            
        Returns:
            Number of records deleted
        """
        if not company_stock_ids:
            return 0
            
        try:
            with self.session.begin():
                # Delete associated KeyCompanyStock records
                key_delete_count = self.session.query(KeyCompanyStock).filter(
                    KeyCompanyStock.company_stock_id.in_(company_stock_ids)
                ).delete(synchronize_session=False)
                
                # Delete CompanyStock records
                stock_delete_count = self.session.query(CompanyStockModel).filter(
                    CompanyStockModel.id.in_(company_stock_ids)
                ).delete(synchronize_session=False)
                
                logger.info(f"Deleted {stock_delete_count} stocks and {key_delete_count} key relationships")
                return stock_delete_count
                
        except Exception as e:
            logger.error(f"Error in bulk delete operation: {str(e)}")
            raise
    
    def update_bulk(self, updates: List[Dict[str, Any]]) -> List[CompanyStockEntity]:
        """
        Update multiple CompanyStock records in bulk.
        
        Args:
            updates: List of dictionaries with 'id' and fields to update
            
        Returns:
            List of updated CompanyStock entities
        """
        if not updates:
            return []
            
        try:
            with self.session.begin():
                updated_stocks = []
                
                for update_data in updates:
                    if 'id' not in update_data:
                        raise ValueError("Update data must contain 'id' field")
                        
                    stock_id = update_data.pop('id')
                    stock = self.session.query(CompanyStockModel).filter(
                        CompanyStockModel.id == stock_id
                    ).first()
                    
                    if not stock:
                        logger.warning(f"Stock with ID {stock_id} not found for update")
                        continue
                    
                    # Update attributes
                    for attr, value in update_data.items():
                        if hasattr(stock, attr):
                            setattr(stock, attr, value)
                    
                    updated_stocks.append(self._to_domain(stock))
                
                logger.info(f"Successfully updated {len(updated_stocks)} company stocks")
                return updated_stocks
                
        except Exception as e:
            logger.error(f"Error in bulk update operation: {str(e)}")
            raise
