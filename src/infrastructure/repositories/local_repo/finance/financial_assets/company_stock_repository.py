from sqlalchemy import MetaData
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.infrastructure.models.keys.finance.financial_assets.key_company_stock import KeyCompanyStock
from src.infrastructure.models import CompanyStock as CompanyStockModel
from src.domain.entities.finance.financial_assets.company_stock import CompanyStock as CompanyStockEntity
from typing import List, Dict, Optional
import logging

# Setup logging
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
        """Check if a CompanyStock exists by its ID"""
        return self.session.query(CompanyStockModel).filter(
            CompanyStockModel.id == company_stock_id
        ).first() is not None
    
    def add_bulk(self, domain_stocks: List[CompanyStockEntity], key_mappings: List[Dict]) -> List[CompanyStockEntity]:
        """
        Add multiple CompanyStock entities in a single atomic transaction.
        
        Args:
            domain_stocks: List of CompanyStock domain entities
            key_mappings: List of dicts with keys: key_id, key_value, repo_id
            
        Returns:
            List of created CompanyStock entities
            
        Raises:
            ValueError: If domain_stocks and key_mappings length mismatch
            Exception: If database operation fails
        """
        if len(domain_stocks) != len(key_mappings):
            raise ValueError("domain_stocks and key_mappings must have the same length")
        
        if not domain_stocks:
            return []
            
        try:
            with self.session.begin():
                created_stocks = []
                created_keys = []
                
                # Check for existing stocks to prevent duplicates
                existing_checks = []
                for i, mapping in enumerate(key_mappings):
                    existing = self.session.query(KeyCompanyStock).filter(
                        KeyCompanyStock.key_value == mapping['key_value'],
                        KeyCompanyStock.key_id == mapping['key_id']
                    ).first()
                    
                    if existing:
                        logger.warning(f"Stock already exists: key_id={mapping['key_id']}, key_value={mapping['key_value']}")
                        existing_stock = self.get_by_id(existing.company_stock_id)
                        created_stocks.append(existing_stock)
                        continue
                    
                    # Create new CompanyStock model
                    new_stock = CompanyStockModel(domain_entity=domain_stocks[i])
                    self.session.add(new_stock)
                    self.session.flush()  # Get the ID
                    
                    # Create corresponding KeyCompanyStock
                    new_key = KeyCompanyStock(
                        company_stock_id=new_stock.id,
                        repo_id=mapping['repo_id'],
                        key_id=mapping['key_id'],
                        key_value=mapping['key_value'],
                        start_date=domain_stocks[i].start_date,
                        end_date=domain_stocks[i].end_date
                    )
                    self.session.add(new_key)
                    
                    created_stocks.append(self._to_domain(new_stock))
                    created_keys.append(new_key)
                
                logger.info(f"Successfully created {len([s for s in created_stocks if s])} company stocks in bulk operation")
                return created_stocks
                
        except Exception as e:
            logger.error(f"Error in bulk add operation: {str(e)}")
            self.session.rollback()
            raise
    
    def add_bulk_from_dicts(self, company_dicts: List[Dict], key_mappings: List[Dict]) -> List[CompanyStockEntity]:
        """
        Create and add multiple CompanyStock entities from dictionaries.
        
        Args:
            company_dicts: List of dicts with CompanyStock data
            key_mappings: List of dicts with keys: key_id, key_value, repo_id
            
        Returns:
            List of created CompanyStock entities
        """
        domain_stocks = []
        for company_data in company_dicts:
            stock = CompanyStockEntity(
                id=company_data.get('id'),
                ticker=company_data['ticker'],
                exchange_id=company_data['exchange_id'],
                company_id=company_data['company_id'],
                start_date=company_data['start_date'],
                end_date=company_data.get('end_date')
            )
            domain_stocks.append(stock)
        
        return self.add_bulk(domain_stocks, key_mappings)
    
    def delete_bulk(self, company_stock_ids: List[int]) -> int:
        """
        Delete multiple CompanyStock records and their associated KeyCompanyStock records.
        
        Args:
            company_stock_ids: List of CompanyStock IDs to delete
            
        Returns:
            Number of successfully deleted records
        """
        if not company_stock_ids:
            return 0
            
        try:
            with self.session.begin():
                # Delete associated KeyCompanyStock records
                key_deletions = self.session.query(KeyCompanyStock).filter(
                    KeyCompanyStock.company_stock_id.in_(company_stock_ids)
                ).delete(synchronize_session=False)
                
                # Delete CompanyStock records
                stock_deletions = self.session.query(CompanyStockModel).filter(
                    CompanyStockModel.id.in_(company_stock_ids)
                ).delete(synchronize_session=False)
                
                logger.info(f"Bulk deleted {stock_deletions} company stocks and {key_deletions} key relationships")
                return stock_deletions
                
        except Exception as e:
            logger.error(f"Error in bulk delete operation: {str(e)}")
            self.session.rollback()
            raise
    
    def update_bulk(self, updates: List[Dict]) -> List[CompanyStockEntity]:
        """
        Update multiple CompanyStock records.
        
        Args:
            updates: List of dicts with 'id' and update fields
            
        Returns:
            List of updated CompanyStock entities
        """
        if not updates:
            return []
            
        try:
            with self.session.begin():
                updated_stocks = []
                
                for update_data in updates:
                    stock_id = update_data.pop('id')
                    stock = self.session.query(CompanyStockModel).filter(
                        CompanyStockModel.id == stock_id
                    ).first()
                    
                    if stock:
                        for attr, value in update_data.items():
                            if hasattr(stock, attr):
                                setattr(stock, attr, value)
                        updated_stocks.append(self._to_domain(stock))
                
                logger.info(f"Bulk updated {len(updated_stocks)} company stocks")
                return updated_stocks
                
        except Exception as e:
            logger.error(f"Error in bulk update operation: {str(e)}")
            self.session.rollback()
            raise
