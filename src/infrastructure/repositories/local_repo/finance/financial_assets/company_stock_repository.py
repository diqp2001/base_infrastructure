from sqlalchemy import MetaData
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.infrastructure.models.keys.finance.financial_assets.key_company_stock import KeyCompanyStock
from src.infrastructure.models import CompanyStock as CompanyStockModel
from src.domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from src.domain.entities.finance.financial_assets.company_share import CompanyStock as CompanyStockEntity  # Legacy compatibility
from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_mapper import CompanyStockMapper




class CompanyStockRepository:
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, infra_stock: CompanyStockModel) -> CompanyStockEntity:
        """Convert an infrastructure CompanyStock to a domain CompanyStock using mapper."""
        if not infra_stock:
            return None
        return CompanyStockMapper.to_domain(infra_stock)

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

        # Convert domain entity to infrastructure model using mapper and add it
        new_stock = CompanyStockMapper.to_orm(domain_stock)
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

    def add_bulk(self, domain_stocks, key_mappings):
        """
        Add multiple CompanyStock records in a single atomic transaction.
        
        Args:
            domain_stocks: List of CompanyStockEntity objects
            key_mappings: List of dicts with keys: key_id, key_value, repo_id
            
        Returns:
            List[CompanyStockEntity]: Successfully created entities
        """
        if not domain_stocks or not key_mappings:
            return []
            
        if len(domain_stocks) != len(key_mappings):
            raise ValueError("domain_stocks and key_mappings must have same length")
        
        created_entities = []
        
        try:
            with self.session.begin():
                # Check for existing stocks to prevent duplicates
                existing_keys = []
                for mapping in key_mappings:
                    existing = self.session.query(KeyCompanyStock).filter(
                        KeyCompanyStock.key_value == mapping['key_value'],
                        KeyCompanyStock.key_id == mapping['key_id']
                    ).first()
                    if existing:
                        existing_keys.append(existing.company_stock_id)
                
                if existing_keys:
                    print(f"Warning: Found {len(existing_keys)} existing stocks, skipping duplicates")
                
                # Create new CompanyStock models
                new_stocks = []
                new_key_stocks = []
                
                for i, (domain_stock, mapping) in enumerate(zip(domain_stocks, key_mappings)):
                    # Skip if already exists
                    existing = self.session.query(KeyCompanyStock).filter(
                        KeyCompanyStock.key_value == mapping['key_value'],
                        KeyCompanyStock.key_id == mapping['key_id']
                    ).first()
                    
                    if existing:
                        # Add existing entity to results
                        existing_entity = self.get_by_id(existing.company_stock_id)
                        if existing_entity:
                            created_entities.append(existing_entity)
                        continue
                    
                    # Create new stock using mapper
                    new_stock = CompanyStockMapper.to_orm(domain_stock)
                    new_stocks.append(new_stock)
                    self.session.add(new_stock)
                    
                # Flush to get IDs for new stocks
                if new_stocks:
                    self.session.flush()
                    
                    # Create KeyCompanyStock entries
                    stock_idx = 0
                    for i, (domain_stock, mapping) in enumerate(zip(domain_stocks, key_mappings)):
                        # Skip existing stocks
                        existing = self.session.query(KeyCompanyStock).filter(
                            KeyCompanyStock.key_value == mapping['key_value'],
                            KeyCompanyStock.key_id == mapping['key_id']
                        ).first()
                        
                        if existing:
                            continue
                            
                        # Create key mapping for new stock
                        new_key_stock = KeyCompanyStock(
                            company_stock_id=new_stocks[stock_idx].id,
                            repo_id=mapping['repo_id'],
                            key_id=mapping['key_id'],
                            key_value=mapping['key_value'],
                            start_date=domain_stock.start_date,
                            end_date=domain_stock.end_date
                        )
                        new_key_stocks.append(new_key_stock)
                        self.session.add(new_key_stock)
                        
                        # Convert to domain entity and add to results
                        created_entities.append(self._to_domain(new_stocks[stock_idx]))
                        stock_idx += 1
                
                # Commit transaction
                self.session.commit()
                
        except Exception as e:
            self.session.rollback()
            print(f"Error in bulk add operation: {str(e)}")
            raise
        
        return created_entities

    def add_bulk_from_dicts(self, company_dicts, key_mappings):
        """
        Create and add multiple CompanyStock entities from dictionaries.
        
        Args:
            company_dicts: List of dicts with CompanyStock data
            key_mappings: List of dicts with key mapping data
            
        Returns:
            List[CompanyStockEntity]: Successfully created entities
        """
        domain_stocks = []
        for data in company_dicts:
            domain_stock = CompanyStockEntity(
                id=data['id'],
                ticker=data['ticker'],
                exchange_id=data['exchange_id'],
                company_id=data['company_id'],
                start_date=data['start_date'],
                end_date=data.get('end_date')
            )
            domain_stocks.append(domain_stock)
        
        return self.add_bulk(domain_stocks, key_mappings)

    def delete_bulk(self, company_stock_ids):
        """
        Delete multiple CompanyStock records and their associated KeyCompanyStock records.
        
        Args:
            company_stock_ids: List of CompanyStock IDs to delete
            
        Returns:
            int: Number of records deleted
        """
        if not company_stock_ids:
            return 0
            
        deleted_count = 0
        
        try:
            with self.session.begin():
                # Delete associated KeyCompanyStock records first
                key_deleted = self.session.query(KeyCompanyStock).filter(
                    KeyCompanyStock.company_stock_id.in_(company_stock_ids)
                ).delete(synchronize_session=False)
                
                # Delete CompanyStock records
                stock_deleted = self.session.query(CompanyStockModel).filter(
                    CompanyStockModel.id.in_(company_stock_ids)
                ).delete(synchronize_session=False)
                
                deleted_count = stock_deleted
                self.session.commit()
                
        except Exception as e:
            self.session.rollback()
            print(f"Error in bulk delete operation: {str(e)}")
            raise
            
        return deleted_count

    def update_bulk(self, updates):
        """
        Update multiple CompanyStock records.
        
        Args:
            updates: List of dicts with 'id' and update fields
            
        Returns:
            int: Number of records updated
        """
        if not updates:
            return 0
            
        updated_count = 0
        
        try:
            with self.session.begin():
                for update_data in updates:
                    stock_id = update_data.pop('id')
                    updated = self.session.query(CompanyStockModel).filter(
                        CompanyStockModel.id == stock_id
                    ).update(update_data, synchronize_session=False)
                    updated_count += updated
                
                self.session.commit()
                
        except Exception as e:
            self.session.rollback()
            print(f"Error in bulk update operation: {str(e)}")
            raise
            
        return updated_count
