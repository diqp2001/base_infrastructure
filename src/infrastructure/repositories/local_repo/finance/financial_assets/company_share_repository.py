from sqlalchemy import MetaData
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.infrastructure.models.keys.finance.financial_assets.key_company_share import KeyCompanyShare
from src.infrastructure.models import CompanyShare as CompanyShareModel
from src.domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_mapper import CompanyShareMapper




class CompanyShareRepository:
    def __init__(self, session: Session):
        self.session = session

    def _to_domain(self, infra_share: CompanyShareModel) -> CompanyShareEntity:
        """Convert an infrastructure CompanyShare to a domain CompanyShare using mapper."""
        if not infra_share:
            return None
        return CompanyShareMapper.to_domain(infra_share)

    def get_all(self):
        """Retrieve all CompanyShare records from the database."""
        shares = self.session.query(CompanyShareModel).all()
        return [self._to_domain(share) for share in shares]

    def get_by_id(self, company_share_id: int):
        """Retrieve a CompanyShare record by its ID."""
        share = self.session.query(CompanyShareModel).filter(
            CompanyShareModel.id == company_share_id
        ).first()
        return self._to_domain(share)

    def exists(self, key_value: int, key_id: int):
        """
        Check if a CompanyShare exists in the database by cross-referencing with KeyCompanyShare.
        """
        return self.session.query(KeyCompanyShare).filter(
            KeyCompanyShare.key_value == key_value,
            KeyCompanyShare.key_id == key_id
        ).first() is not None

    def add(self, domain_share: CompanyShareEntity, key_id: int, key_value: int, repo_id: int):
        """
        Add a new CompanyShare record to the database.
        Verify if the share already exists by cross-referencing KeyCompanyShare.
        """
        # Check if the share exists in the repository
        existing_share = self.session.query(KeyCompanyShare).filter(
            KeyCompanyShare.key_value == key_value,
            KeyCompanyShare.key_id == key_id
        ).first()

        if existing_share:
            # Return the associated CompanyShare if it already exists
            return self.get_by_id(existing_share.company_share_id)

        # Convert domain entity to infrastructure model using mapper and add it
        new_share = CompanyShareMapper.to_orm(domain_share)
        self.session.add(new_share)
        self.session.flush()  # Get the new share ID before committing

        # Create a corresponding KeyCompanyShare
        new_key_company_share = KeyCompanyShare(
            company_share_id=new_share.id,
            repo_id=repo_id,
            key_id=key_id,
            key_value=key_value,
            start_date=domain_share.start_date,
            end_date=domain_share.end_date
        )
        self.session.add(new_key_company_share)
        self.session.commit()

        return self._to_domain(new_share)

    def update(self, company_share_id: int, **kwargs):
        """
        Update an existing CompanyShare record.
        """
        share = self.session.query(CompanyShareModel).filter(
            CompanyShareModel.id == company_share_id
        ).first()
        if not share:
            return None

        # Update attributes dynamically
        for attr, value in kwargs.items():
            if hasattr(share, attr):
                setattr(share, attr, value)

        self.session.commit()
        return self._to_domain(share)

    def delete(self, company_share_id: int):
        """
        Delete a CompanyShare record and its associated KeyCompanyShare records.
        """
        share = self.session.query(CompanyShareModel).filter(
            CompanyShareModel.id == company_share_id
        ).first()
        if not share:
            return False

        # Delete associated KeyCompanyShare records
        self.session.query(KeyCompanyShare).filter(
            KeyCompanyShare.company_share_id == company_share_id
        ).delete()

        # Delete the CompanyShare
        self.session.delete(share)
        self.session.commit()
        return True

    def get_by_ticker(self, ticker: str):
        """Retrieve CompanyShare records by ticker."""
        shares = self.session.query(CompanyShareModel).filter(
            CompanyShareModel.ticker == ticker
        ).all()
        return [self._to_domain(share) for share in shares]

    def get_by_key(self, key_id: int, key_value: int):
        """
        Retrieve a CompanyShare by key_id and key_value using KeyCompanyShare.
        """
        key_share = self.session.query(KeyCompanyShare).filter(
            KeyCompanyShare.key_id == key_id,
            KeyCompanyShare.key_value == key_value
        ).first()

        if key_share:
            return self.get_by_id(key_share.company_share_id)
        return None

    def exists_by_id(self, company_share_id: int) -> bool:
        """Check if a CompanyShare exists by its ID."""
        return self.session.query(CompanyShareModel).filter(
            CompanyShareModel.id == company_share_id
        ).first() is not None

    def add_bulk(self, domain_shares, key_mappings):
        """
        Add multiple CompanyShare records in a single atomic transaction.
        
        Args:
            domain_shares: List of CompanyShareEntity objects
            key_mappings: List of dicts with keys: key_id, key_value, repo_id
            
        Returns:
            List[CompanyShareEntity]: Successfully created entities
        """
        if not domain_shares or not key_mappings:
            return []
            
        if len(domain_shares) != len(key_mappings):
            raise ValueError("domain_shares and key_mappings must have same length")
        
        created_entities = []
        
        try:
            with self.session.begin():
                # Check for existing shares to prevent duplicates
                existing_keys = []
                for mapping in key_mappings:
                    existing = self.session.query(KeyCompanyShare).filter(
                        KeyCompanyShare.key_value == mapping['key_value'],
                        KeyCompanyShare.key_id == mapping['key_id']
                    ).first()
                    if existing:
                        existing_keys.append(existing.company_share_id)
                
                if existing_keys:
                    print(f"Warning: Found {len(existing_keys)} existing shares, skipping duplicates")
                
                # Create new CompanyShare models
                new_shares = []
                new_key_shares = []
                
                for i, (domain_share, mapping) in enumerate(zip(domain_shares, key_mappings)):
                    # Skip if already exists
                    existing = self.session.query(KeyCompanyShare).filter(
                        KeyCompanyShare.key_value == mapping['key_value'],
                        KeyCompanyShare.key_id == mapping['key_id']
                    ).first()
                    
                    if existing:
                        # Add existing entity to results
                        existing_entity = self.get_by_id(existing.company_share_id)
                        if existing_entity:
                            created_entities.append(existing_entity)
                        continue
                    
                    # Create new share using mapper
                    new_share = CompanyShareMapper.to_orm(domain_share)
                    new_shares.append(new_share)
                    self.session.add(new_share)
                    
                # Flush to get IDs for new shares
                if new_shares:
                    self.session.flush()
                    
                    # Create KeyCompanyShare entries
                    share_idx = 0
                    for i, (domain_share, mapping) in enumerate(zip(domain_shares, key_mappings)):
                        # Skip existing shares
                        existing = self.session.query(KeyCompanyShare).filter(
                            KeyCompanyShare.key_value == mapping['key_value'],
                            KeyCompanyShare.key_id == mapping['key_id']
                        ).first()
                        
                        if existing:
                            continue
                            
                        # Create key mapping for new share
                        new_key_share = KeyCompanyShare(
                            company_share_id=new_shares[share_idx].id,
                            repo_id=mapping['repo_id'],
                            key_id=mapping['key_id'],
                            key_value=mapping['key_value'],
                            start_date=domain_share.start_date,
                            end_date=domain_share.end_date
                        )
                        new_key_shares.append(new_key_share)
                        self.session.add(new_key_share)
                        
                        # Convert to domain entity and add to results
                        created_entities.append(self._to_domain(new_shares[share_idx]))
                        share_idx += 1
                
                # Commit transaction
                self.session.commit()
                
        except Exception as e:
            self.session.rollback()
            print(f"Error in bulk add operation: {str(e)}")
            raise
        
        return created_entities

    def add_bulk_from_dicts(self, company_dicts, key_mappings):
        """
        Create and add multiple CompanyShare entities from dictionaries.
        
        Args:
            company_dicts: List of dicts with CompanyShare data
            key_mappings: List of dicts with key mapping data
            
        Returns:
            List[CompanyShareEntity]: Successfully created entities
        """
        domain_shares = []
        for data in company_dicts:
            domain_share = CompanyShareEntity(
                id=data['id'],
                ticker=data['ticker'],
                exchange_id=data['exchange_id'],
                company_id=data['company_id'],
                start_date=data['start_date'],
                end_date=data.get('end_date')
            )
            domain_shares.append(domain_share)
        
        return self.add_bulk(domain_shares, key_mappings)

    def delete_bulk(self, company_share_ids):
        """
        Delete multiple CompanyShare records and their associated KeyCompanyShare records.
        
        Args:
            company_share_ids: List of CompanyShare IDs to delete
            
        Returns:
            int: Number of records deleted
        """
        if not company_share_ids:
            return 0
            
        deleted_count = 0
        
        try:
            with self.session.begin():
                # Delete associated KeyCompanyShare records first
                key_deleted = self.session.query(KeyCompanyShare).filter(
                    KeyCompanyShare.company_share_id.in_(company_share_ids)
                ).delete(synchronize_session=False)
                
                # Delete CompanyShare records
                share_deleted = self.session.query(CompanyShareModel).filter(
                    CompanyShareModel.id.in_(company_share_ids)
                ).delete(synchronize_session=False)
                
                deleted_count = share_deleted
                self.session.commit()
                
        except Exception as e:
            self.session.rollback()
            print(f"Error in bulk delete operation: {str(e)}")
            raise
            
        return deleted_count

    def update_bulk(self, updates):
        """
        Update multiple CompanyShare records.
        
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
                    share_id = update_data.pop('id')
                    updated = self.session.query(CompanyShareModel).filter(
                        CompanyShareModel.id == share_id
                    ).update(update_data, synchronize_session=False)
                    updated_count += updated
                
                self.session.commit()
                
        except Exception as e:
            self.session.rollback()
            print(f"Error in bulk update operation: {str(e)}")
            raise
            
        return updated_count