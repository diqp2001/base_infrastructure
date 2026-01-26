import requests
import json
import logging
from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy import MetaData
from sqlalchemy.orm import Session
from sqlalchemy import or_

logger = logging.getLogger(__name__)

from src.domain.ports.finance.financial_assets.share.company_share.company_share_port import CompanySharePort
from src.infrastructure.repositories.local_repo.finance.financial_assets.share_repository import ShareRepository
from src.infrastructure.models.finance.financial_assets.company_share import CompanyShareModel as CompanyShareModel
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare as CompanyShareEntity
from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_mapper import CompanyShareMapper


class CompanyShareRepository(ShareRepository,CompanySharePort):
    def __init__(self, session: Session, factory=None):
        # Properly call parent constructor with session
        super().__init__(session,factory)
    
    @property  
    def model_class(self):
        """Return the SQLAlchemy model class for CompanyShare."""
        return CompanyShareModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for CompanyShare."""
        return CompanyShareEntity

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

    def _create_or_get(self, ticker: str, exchange_id: int = None, 
                                    company_id: Optional[int] = None, 
                                    start_date=None, end_date=None,
                                    company_name: Optional[str] = None,
                                    sector: Optional[str] = None, 
                                    industry: Optional[str] = None,
                                    exchange_name: Optional[str] = None,
                                    country_name: Optional[str] = None,
                                    industry_name: Optional[str] = None) -> CompanyShareEntity:
        """
        Create company share entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as BaseFactorRepository._create_or_get_factor().
        Now supports automatic foreign key dependency resolution.
        
        Args:
            ticker: Stock ticker symbol (unique identifier)
            exchange_id: Exchange ID (will be auto-resolved if not provided)
            company_id: Company ID (will be auto-resolved if not provided)
            start_date: Start date for the share
            end_date: End date for the share
            company_name: Company name for entity setup
            sector: Sector for entity setup
            industry: Industry for entity setup
            exchange_name: Exchange name for dependency resolution
            country_name: Country name for dependency resolution
            industry_name: Industry name for dependency resolution
            
        Returns:
            CompanyShareEntity: Created or existing entity
        """
        # Check if entity already exists by ticker (unique identifier)
        existing_share = self.get_by_ticker(ticker)
        if existing_share:
            return existing_share[0] if isinstance(existing_share, list) else existing_share
        
        # Resolve dependencies if not provided
        if exchange_id is None:
            exchange_id = self._resolve_exchange_dependency(ticker, exchange_name)
        
        if company_id is None:
            company_id = self._resolve_company_dependency(ticker, company_name, industry_name, country_name)
        
        try:
            # Generate next available ID if not provided
            next_id = self._get_next_available_company_share_id()
            
            # Create new company share entity
            new_share = CompanyShareEntity(
                id=next_id,
                ticker=ticker,
                exchange_id=exchange_id or 1,  # Default to 1 if resolution fails
                company_id=company_id or 1,   # Default to 1 if resolution fails
                start_date=start_date,
                end_date=end_date
            )
            
            # Set additional properties if provided
            if company_name:
                new_share.set_company_name(company_name)
            if sector or industry:
                new_share.update_sector_industry(sector, industry)
            
            # Add to database
            return self.add(new_share)
            
        except Exception as e:
            print(f"Error creating company share for {ticker}: {str(e)}")
            return None
    
    def _resolve_exchange_dependency(self, ticker: str, exchange_name: Optional[str] = None) -> int:
        """Resolve exchange dependency for the company share."""
        try:
            # Use factory if available, otherwise create repository directly
            if self.factory:
                local_repos = self.factory.create_local_repositories()
                exchange_repo = local_repos.get('exchange')
                if not exchange_repo:
                    exchange_repo = self.factory.exchange_local_repo
            else:
                exchange_repo = self.factory.exchange_local_repo
            
            exchange_name = exchange_name or self._get_default_exchange_for_ticker(ticker)
            
            exchange = exchange_repo._create_or_get(
                name=exchange_name,
                legal_name=f"{exchange_name} Stock Exchange",
                country_id=1  # Default to USA
            )
            
            return exchange.id if exchange else 1
            
        except Exception as e:
            print(f"Error resolving exchange dependency: {str(e)}")
            return 1
    
    def _resolve_company_dependency(self, ticker: str, company_name: Optional[str] = None, 
                                  industry_name: Optional[str] = None,
                                  country_name: Optional[str] = None) -> int:
        """Resolve company dependency for the company share."""
        try:
            # Use factory if available, otherwise create repository directly
            if self.factory:
                local_repos = self.factory.create_local_repositories()
                company_repo = local_repos.get('company')
                if not company_repo:
                    company_repo = self.factory.company_local_repo
            else:
                company_repo = self.factory.company_local_repo
            
            company_name = company_name or f"{ticker} Inc."
            
            company = company_repo._create_or_get(
                name=company_name,
                legal_name=company_name,
                country_id=1,   # Default to USA
                industry_id=1   # Default to Technology
            )
            
            return company.id if company else 1
            
        except Exception as e:
            print(f"Error resolving company dependency: {str(e)}")
            return 1
    
    def _get_default_exchange_for_ticker(self, ticker: str) -> str:
        """Get default exchange based on ticker patterns."""
        # Simple heuristics for common exchanges
        if ticker in ['SPX', 'VIX', 'RUT']:
            return 'CBOE'
        elif len(ticker) <= 4 and ticker.isalpha():
            return 'NASDAQ'
        else:
            return 'NYSE'

    def get_or_create(self, ticker: str, exchange_id: Optional[int] = None, company_id: Optional[int] = None) -> Optional[CompanyShareEntity]:
        """
        Get or create a company share with dependency resolution.
        Integrates the functionality from to_orm_with_dependencies.
        
        Args:
            ticker: Company share ticker symbol
            exchange_id: Exchange ID (optional, will resolve if not provided)
            company_id: Company ID (optional, will resolve if not provided)
            
        Returns:
            Domain company share entity or None if creation failed
        """
        try:
            # First try to get existing company share
            existing = self.get_by_ticker(ticker)
            if existing:
                return existing
            
            # Get or create company dependency
            if not company_id:
                # Use factory if available
                if self.factory:
                    local_repos = self.factory.create_local_repositories()
                    company_repo = local_repos.get('company')
                    if not company_repo:
                        company_repo = self.factory.company_local_repo
                else:
                    company_repo = self.factory.company_local_repo
                company = company_repo.get_or_create(name=f"Company for {ticker}")
                company_id = company.id if company else 1
            
            # Get or create exchange dependency  
            if not exchange_id:
                # Use factory if available
                if self.factory:
                    local_repos = self.factory.create_local_repositories()
                    exchange_repo = local_repos.get('exchange')
                    if not exchange_repo:
                        exchange_repo = self.factory.exchange_local_repo
                else:
                    exchange_repo = self.factory.exchange_local_repo
                exchange_name = self._get_default_exchange_for_ticker(ticker)
                exchange = exchange_repo.get_or_create(name=exchange_name)
                exchange_id = exchange.id if exchange else 1
            
            # Use the existing _create_or_get method
            return self._create_or_get(ticker=ticker, exchange_id=exchange_id, company_id=company_id)
            
        except Exception as e:
            logger.error(f"Error in get_or_create for company share {ticker}: {e}")
            return None

    # ----------------------------- Standard CRUD Interface -----------------------------
    def create(self, entity: CompanyShareEntity) -> CompanyShareEntity:
        """Create new company share entity in database (standard CRUD interface)"""
        return self.add(entity)