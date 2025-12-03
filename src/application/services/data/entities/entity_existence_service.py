"""
Entity Existence Service - handles verification and creation of entity dependencies.

Provides a centralized service for ensuring all required entities exist in the database
before operations, following the standardized _create_or_get pattern used throughout
the codebase (e.g., BaseFactorRepository._create_or_get_factor).

This service was refactored from the _ensure_entities_exist method in FactorEnginedDataManager
to promote reusability and maintain separation of concerns.
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from application.services.database_service.database_service import DatabaseService
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.company import Company as CompanyEntity
from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
from infrastructure.repositories.local_repo.finance.exchange_repository import ExchangeRepository

from infrastructure.repositories.local_repo.finance.company_repository import CompanyRepository
from infrastructure.repositories.local_repo.geographic.country_repository import CountryRepository
from infrastructure.repositories.local_repo.geographic.industry_repository import IndustryRepository
from infrastructure.repositories.local_repo.geographic.sector_repository import SectorRepository


class EntityExistenceService:
    """
    Service for ensuring entity dependencies exist in the database.
    
    Handles verification and creation of entities like CompanyShare, Company, 
    Country, Sector, and Industry following standardized patterns.
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize the service with database access.
        
        Args:
            database_service: DatabaseService instance for database operations
        """
        self.database_service = database_service
        self.session = database_service.session
        
        # Initialize repositories
        self.company_share_repository = CompanyShareRepository(self.session)
        self.company_repository = CompanyRepository(self.session)
        self.country_repository = CountryRepository(self.session)
        self.sector_repository = SectorRepository(self.session)
        self.industry_repository = IndustryRepository(self.session)
        self.exchange_repository = ExchangeRepository(self.session)
    
    def ensure_entities_exist(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Ensure all required entities exist in the database for the given tickers.
        
        This method verifies/creates:
        1. CompanyShare entities for each ticker
        2. Company entities that the shares represent
        3. Related entities (Country, Sector, Industry) as needed
        
        Args:
            tickers: List of stock tickers to process
            
        Returns:
            Dict with verification and creation statistics
        """
        print("  📋 Verifying entities exist...")
        
        results = {
            'company_shares': {'verified': 0, 'existing': 0, 'created': 0},
            'companies': {'verified': 0, 'existing': 0, 'created': 0},
            'countries': {'verified': 0, 'existing': 0, 'created': 0},
            'sectors': {'verified': 0, 'existing': 0, 'created': 0},
            'industries': {'verified': 0, 'existing': 0, 'created': 0},
            'errors': []
        }
        
        for ticker in tickers:
            try:
                # Step 1: Ensure related entities exist first
                related_results = self._ensure_related_entities_exist(ticker)
                self._update_results(results['countries'], related_results.get('country', {}))
                self._update_results(results['sectors'], related_results.get('sector', {}))
                self._update_results(results['industries'], related_results.get('industry', {}))
                
                # Step 2: Ensure Company exists (create company first to get company_id)
                company_result = self._ensure_company_exists(ticker)
                self._update_results(results['companies'], company_result)
                
                # Step 3: Ensure CompanyShare exists with proper company_id
                if company_result.get('entity'):
                    share_result = self._ensure_company_share_exists(ticker, company_result['entity'])
                    self._update_results(results['company_shares'], share_result)
                else:
                    break
                
            except Exception as e:
                error_msg = f"Error ensuring entities exist for {ticker}: {str(e)}"
                results['errors'].append(error_msg)
                print(f"    ❌ {error_msg}")
        
        # Print summary
        self._print_summary(results, tickers)
        
        return results
    
    def _ensure_company_share_exists(self, ticker: str, company: Optional[CompanyEntity] = None) -> Dict[str, Any]:
        """
        Ensure CompanyShare entity exists for the given ticker.
        
        Args:
            ticker: Stock ticker symbol
            company: Company entity to link to the share (optional)
            
        Returns:
            Dict with creation/verification result
        """
        try:
            # Extract company_id from company entity if provided
            company_id = None
            if company:
                # Get the company ID from the database (since domain entity might not have it set)
                db_companies = self.company_repository.get_by_name(company.name)
                if db_companies:
                    # Get the first company and extract its ID from the database model
                    db_model = self.company_repository.session.query(
                        self.company_repository.model_class
                    ).filter(
                        self.company_repository.model_class.name == company.name
                    ).first()
                    company_id = db_model.id if db_model else None
            
            # Use the standardized create-or-get method from CompanyShareRepository
            share = self.company_share_repository._create_or_get_company_share(
                ticker=ticker,
                exchange_id=1,
                company_id=company_id,  # Now properly set from company
                start_date=datetime(2020, 1, 1),
                company_name=f"{ticker} Inc.",
                sector="Technology",
                industry=None
            )
            
            if share:
                # Check if this was newly created or already existed
                existing_shares = self.company_share_repository.get_by_ticker(ticker)
                was_created = len(existing_shares) == 1 and existing_shares[0].id == share.id
                
                if was_created:
                    print(f"    ✅ Created CompanyShare for {ticker} (company_id: {company_id})")
                    return {'status': 'created', 'entity': share}
                else:
                    print(f"    ✅ Found existing CompanyShare for {ticker} (company_id: {company_id})")
                    return {'status': 'existing', 'entity': share}
            else:
                print(f"    ❌ Failed to create/get CompanyShare for {ticker}")
                return {'status': 'failed'}
                
        except Exception as e:
            print(f"    ❌ Error ensuring CompanyShare exists for {ticker}: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _ensure_company_exists(self, ticker: str) -> Dict[str, Any]:
        """
        Ensure Company entity exists for the given ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with creation/verification result including the created/found entity
        """
        try:
            company_name = f"{ticker} Inc."
            
            # Use the standardized create-or-get method from CompanyRepository
            company = self.company_repository._create_or_get_company(
                name=company_name,
                legal_name=company_name,
                country_id=1,  # Default to USA (ID 1)
                industry_id=1,  # Default to Technology (ID 1)
                start_date=datetime(2020, 1, 1).date()
            )
            
            if company:
                # Check if this was newly created or already existed
                existing_companies = self.company_repository.get_by_name(company_name)
                was_created = len(existing_companies) == 1 and existing_companies[0].name == company.name
                
                if was_created:
                    print(f"    ✅ Created Company '{company_name}' for {ticker}")
                    return {'status': 'created', 'entity': company}
                else:
                    print(f"    ✅ Found existing Company '{company_name}' for {ticker}")
                    return {'status': 'existing', 'entity': company}
            else:
                print(f"    ❌ Failed to create/get Company for {ticker}")
                return {'status': 'failed'}
                
        except Exception as e:
            print(f"    ❌ Error ensuring Company exists for {ticker}: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _ensure_related_entities_exist(self, ticker: str) -> Dict[str, Dict[str, Any]]:
        """
        Ensure related entities (Country, Sector, Industry) exist.
        
        IMPORTANT: Creates entities in the correct dependency order to avoid foreign key errors.
        Order: Countries (no deps) → Sectors (no deps) → Industries (depends on sectors)
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with results for each entity type
        """
        results = {}
        
        try:
            # Step 1: Ensure Country exists (no dependencies)
            country_result = self._ensure_country_exists("United States", "US")
            results['country'] = country_result
            
            # Step 2: Ensure Sector exists (no dependencies)
            sector_result = self._ensure_sector_exists("Technology")
            results['sector'] = sector_result
            
            # Step 3: Ensure Industry exists (depends on sector_id)
            # Create industry AFTER sector to avoid foreign key constraint error
            industry_result = self._ensure_industry_exists("Technology", "Technology sector")
            results['industry'] = industry_result

            
            # Step 4: Ensure Exchange exists 
            # Create Exchange AFTER sector to avoid foreign key constraint error
            exchange_result = self._ensure_exchange_exists()
            results['exchange'] = exchange_result
            
        except Exception as e:
            print(f"    ❌ Error ensuring related entities for {ticker}: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    def _ensure_country_exists(self, name: str, iso_code: str) -> Dict[str, Any]:
        """Ensure Country entity exists using CountryRepository."""
        try:
            country = self.country_repository._create_or_get_country(
                name=name
                # Note: iso_code is stored via mapper, not constructor parameter
            )
            
            if country:
                return {'status': 'verified'}
            else:
                return {'status': 'failed'}
                
        except Exception as e:
            print(f"Error creating country {name}: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def _ensure_sector_exists(self, name: str) -> Dict[str, Any]:
        """Ensure Sector entity exists using SectorRepository."""
        try:
            sector = self.sector_repository._create_or_get_sector(name=name)
            
            if sector:
                return {'status': 'verified'}
            else:
                return {'status': 'failed'}
                
        except Exception as e:
            print(f"Error creating sector {name}: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def _ensure_industry_exists(self, name: str, description: str = "") -> Dict[str, Any]:
        """Ensure Industry entity exists using IndustryRepository."""
        try:
            industry = self.industry_repository._create_or_get_industry(
                name=name,
                description=description
            )
            
            if industry:
                return {'status': 'verified'}
            else:
                return {'status': 'failed'}
                
        except Exception as e:
            print(f"Error creating industry {name}: {str(e)}")
            return {'status': 'failed', 'error': str(e)}
    
    def _update_results(self, target_results: Dict[str, int], operation_result: Dict[str, Any]):
        """Update results dictionary with operation outcome."""
        status = operation_result.get('status', 'unknown')
        
        if status in ['created']:
            target_results['created'] += 1
            target_results['verified'] += 1
        elif status in ['existing', 'verified']:
            target_results['existing'] += 1
            target_results['verified'] += 1
        # Errors and failures don't increment counters
    
    def _print_summary(self, results: Dict[str, Any], tickers: List[str]):
        """Print a summary of entity verification results."""
        print(f"\n  📊 Entity verification complete for {len(tickers)} tickers:")
        
        # CompanyShares
        cs = results['company_shares']
        print(f"    • CompanyShares: {cs['verified']} verified ({cs['existing']} existing, {cs['created']} created)")
        
        # Companies  
        c = results['companies']
        print(f"    • Companies: {c['verified']} verified ({c['existing']} existing, {c['created']} created)")
        
        # Countries
        co = results['countries']
        print(f"    • Countries: {co['verified']} verified ({co['existing']} existing, {co['created']} created)")
        
        # Sectors
        s = results['sectors']
        print(f"    • Sectors: {s['verified']} verified ({s['existing']} existing, {s['created']} created)")
        
        # Errors
        if results['errors']:
            print(f"    ⚠️  {len(results['errors'])} errors encountered")
            for error in results['errors'][:3]:  # Show first 3 errors
                print(f"      - {error}")
            if len(results['errors']) > 3:
                print(f"      - ... and {len(results['errors']) - 3} more")