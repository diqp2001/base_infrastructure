import requests
import json
from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy import MetaData
from sqlalchemy.orm import Session
from sqlalchemy import or_
from infrastructure.repositories.local_repo.finance.financial_assets.share_repository import ShareRepository
from src.infrastructure.models import CompanyShare as CompanyShareModel
from src.domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_mapper import CompanyShareMapper


class CompanyShareRepository(ShareRepository):
    def __init__(self, session: Session):
        # Properly call parent constructor with session
        super().__init__(session)
    
    @property  
    def model_class(self):
        """Return the SQLAlchemy model class for CompanyShare."""
        return CompanyShareModel

    def _to_entity(self, infra_share: CompanyShareModel) -> CompanyShareEntity:
        """Convert an infrastructure CompanyShare to a domain CompanyShare using mapper."""
        if not infra_share:
            return None
        return CompanyShareMapper.to_domain(infra_share)
    
    def _to_model(self, entity: CompanyShareEntity) -> CompanyShareModel:
        """Convert domain entity to ORM model."""
        return CompanyShareMapper.to_infrastructure(entity)
    
    def _to_domain(self, infra_share: CompanyShareModel) -> CompanyShareEntity:
        """Legacy method - delegates to _to_entity."""
        return self._to_entity(infra_share)

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

    def exists_by_ticker(self, ticker: str) -> bool:
        """
        Check if a CompanyShare exists in the database by ticker.
        """
        return self.session.query(CompanyShareModel).filter(
            CompanyShareModel.ticker == ticker
        ).first() is not None

    def add(self, domain_share: CompanyShareEntity) -> CompanyShareEntity:
        """
        Add a new CompanyShare record to the database.
        Checks if share already exists by ticker to prevent duplicates.
        """
        # Check if the share already exists by ticker
        if self.exists_by_ticker(domain_share.ticker):
            existing_share = self.get_by_ticker(domain_share.ticker)
            if existing_share:
                return existing_share[0]  # Return first match

        # Convert domain entity to infrastructure model using mapper and add it
        new_share = CompanyShareMapper.to_orm(domain_share)
        self.session.add(new_share)
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

    def delete(self, company_share_id: int) -> bool:
        """
        Delete a CompanyShare record by ID.
        """
        share = self.session.query(CompanyShareModel).filter(
            CompanyShareModel.id == company_share_id
        ).first()
        if not share:
            return False

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

    def get_by_company_id(self, company_id: int) -> List[CompanyShareEntity]:
        """
        Retrieve CompanyShare records by company_id.
        """
        shares = self.session.query(CompanyShareModel).filter(
            CompanyShareModel.company_id == company_id
        ).all()
        return [self._to_domain(share) for share in shares]

    def exists_by_id(self, company_share_id: int) -> bool:
        """Check if a CompanyShare exists by its ID."""
        return self.session.query(CompanyShareModel).filter(
            CompanyShareModel.id == company_share_id
        ).first() is not None

    def add_bulk(self, domain_shares: List[CompanyShareEntity]) -> List[CompanyShareEntity]:
        """
        Add multiple CompanyShare records in a single atomic transaction.
        
        Args:
            domain_shares: List of CompanyShareEntity objects
            
        Returns:
            List[CompanyShareEntity]: Successfully created entities
        """
        if not domain_shares:
            return []
        
        created_entities = []
        
        try:
            with self.session.begin():
                # Check for existing shares to prevent duplicates
                existing_tickers = []
                for domain_share in domain_shares:
                    if self.exists_by_ticker(domain_share.ticker):
                        existing_share = self.get_by_ticker(domain_share.ticker)
                        if existing_share:
                            created_entities.append(existing_share[0])
                            existing_tickers.append(domain_share.ticker)
                
                if existing_tickers:
                    print(f"Warning: Found {len(existing_tickers)} existing shares, skipping duplicates")
                
                # Create new CompanyShare models
                new_shares = []
                for domain_share in domain_shares:
                    # Skip if already exists
                    if domain_share.ticker in existing_tickers:
                        continue
                    
                    # Create new share using mapper
                    new_share = CompanyShareMapper.to_orm(domain_share)
                    new_shares.append(new_share)
                    self.session.add(new_share)
                    
                # Flush to get IDs for new shares
                if new_shares:
                    self.session.flush()
                    
                    # Convert to domain entities and add to results
                    for new_share in new_shares:
                        created_entities.append(self._to_domain(new_share))
                
                # Commit transaction
                self.session.commit()
                
        except Exception as e:
            self.session.rollback()
            print(f"Error in bulk add operation: {str(e)}")
            raise
        
        return created_entities

    def add_bulk_from_dicts(self, company_dicts: List[Dict[str, Any]]) -> List[CompanyShareEntity]:
        """
        Create and add multiple CompanyShare entities from dictionaries.
        
        Args:
            company_dicts: List of dicts with CompanyShare data
            
        Returns:
            List[CompanyShareEntity]: Successfully created entities
        """
        domain_shares = []
        for data in company_dicts:
            domain_share = CompanyShareEntity(
                id=data.get('id'),
                ticker=data['ticker'],
                exchange_id=data['exchange_id'],
                company_id=data['company_id'],
                start_date=data['start_date'],
                end_date=data.get('end_date')
            )
            domain_shares.append(domain_share)
        
        return self.add_bulk(domain_shares)

    def delete_bulk(self, company_share_ids: List[int]) -> int:
        """
        Delete multiple CompanyShare records.
        
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
                # Delete CompanyShare records
                deleted_count = self.session.query(CompanyShareModel).filter(
                    CompanyShareModel.id.in_(company_share_ids)
                ).delete(synchronize_session=False)
                
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

    def add_with_openfigi(self, ticker: str, exchange_code: str = "US", 
                         market_sec_des: str = "Equity", use_openfigi: bool = True) -> Optional[CompanyShareEntity]:
        """
        Add a CompanyShare using OpenFIGI API for additional data enrichment.
        This is optional and will fallback to basic creation if API fails.
        
        Args:
            ticker: Stock ticker symbol
            exchange_code: Exchange code (default: "US")  
            market_sec_des: Market sector description (default: "Equity")
            use_openfigi: Whether to use OpenFIGI API (default: True)
            
        Returns:
            CompanyShareEntity: Created or existing share entity
        """
        # Check if share already exists
        if self.exists_by_ticker(ticker):
            existing_shares = self.get_by_ticker(ticker)
            if existing_shares:
                return existing_shares[0]
        
        # Try to get additional data from OpenFIGI API if requested
        openfigi_data = {}
        if use_openfigi:
            try:
                openfigi_data = self._fetch_openfigi_data(ticker, exchange_code, market_sec_des)
                print(f"Successfully fetched OpenFIGI data for {ticker}")
            except Exception as e:
                print(f"Warning: OpenFIGI API failed for {ticker}: {str(e)}. Proceeding with basic data.")
        
        # Create CompanyShare entity with available data
        try:
            # Use OpenFIGI data if available, otherwise use defaults
            company_share = CompanyShareEntity(
                id=None,  # Let database generate
                ticker=ticker,
                exchange_id=openfigi_data.get('exchange_id', 1),  # Default to ID 1
                company_id=openfigi_data.get('company_id', 1),   # Default to ID 1
                start_date=openfigi_data.get('start_date'),
                end_date=openfigi_data.get('end_date')
            )
            
            return self.add(company_share)
            
        except Exception as e:
            print(f"Error creating CompanyShare for {ticker}: {str(e)}")
            return None
    
    def _fetch_openfigi_data(self, ticker: str, exchange_code: str, market_sec_des: str) -> Dict[str, Any]:
        """
        Fetch data from OpenFIGI API.
        Based on: https://github.com/OpenFIGI/api-examples
        
        Args:
            ticker: Stock ticker symbol
            exchange_code: Exchange code
            market_sec_des: Market sector description
            
        Returns:
            Dict containing enriched data from OpenFIGI
        """
        openfigi_api_url = 'https://api.openfigi.com/v3/mapping'
        
        # Prepare request payload
        request_payload = [{
            'idType': 'TICKER',
            'idValue': ticker,
            'exchCode': exchange_code,
            'marketSecDes': market_sec_des
        }]
        
        # Add User-Agent header as recommended by OpenFIGI
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'base_infrastructure/1.0'
        }
        
        try:
            response = requests.post(
                openfigi_api_url, 
                json=request_payload, 
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0 and result[0].get('data'):
                    figi_data = result[0]['data'][0]  # Get first match
                    
                    # Extract useful information
                    return {
                        'figi': figi_data.get('figi'),
                        'security_type': figi_data.get('securityType'),
                        'market_sector': figi_data.get('marketSector'),
                        'security_description': figi_data.get('securityDescription'),
                        'exchange_code': figi_data.get('exchCode'),
                        'company_name': figi_data.get('name'),
                        # Add default IDs - in real implementation, you'd map these properly
                        'exchange_id': 1,  # Map from exchCode in production
                        'company_id': 1,   # Map from company_name in production
                        'start_date': None,
                        'end_date': None
                    }
                else:
                    raise ValueError(f"No data found for ticker {ticker}")
            else:
                raise ValueError(f"OpenFIGI API returned status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            raise ValueError(f"OpenFIGI API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from OpenFIGI API: {str(e)}")
    
    def bulk_add_with_openfigi(self, tickers: List[str], exchange_code: str = "US", 
                              use_openfigi: bool = True) -> List[CompanyShareEntity]:
        """
        Bulk add CompanyShares using OpenFIGI API for data enrichment.
        
        Args:
            tickers: List of ticker symbols
            exchange_code: Exchange code (default: "US")
            use_openfigi: Whether to use OpenFIGI API (default: True)
            
        Returns:
            List[CompanyShareEntity]: Created shares
        """
        created_shares = []
        
        for ticker in tickers:
            try:
                share = self.add_with_openfigi(ticker, exchange_code, use_openfigi=use_openfigi)
                if share:
                    created_shares.append(share)
            except Exception as e:
                print(f"Failed to create share for {ticker}: {str(e)}")
                continue
        
        return created_shares

    def _get_next_available_company_share_id(self) -> int:
        """
        Get the next available ID for company share creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(CompanyShareModel.id).order_by(CompanyShareModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available company share ID: {str(e)}")
            return 1  # Default to 1 if query fails

    # ----------------------------- Standard CRUD Interface -----------------------------
    def create(self, entity: CompanyShareEntity) -> CompanyShareEntity:
        """Create new company share entity in database (standard CRUD interface)"""
        return self.add(entity)