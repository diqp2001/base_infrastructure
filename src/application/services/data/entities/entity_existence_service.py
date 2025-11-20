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
from infrastructure.repositories.local_repo.geographic.country_repository import CountryRepository
from infrastructure.repositories.local_repo.finance.sector_repository import SectorRepository
from infrastructure.repositories.local_repo.finance.industry_repository import IndustryRepository


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
        self.country_repository = CountryRepository(self.session)
        self.sector_repository = SectorRepository(self.session)
        self.industry_repository = IndustryRepository(self.session)
    
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
                # Ensure CompanyShare exists
                share_result = self._ensure_company_share_exists(ticker)
                self._update_results(results['company_shares'], share_result)
                
                if share_result.get('entity'):
                    # Ensure Company exists (if CompanyShare was created/found)
                    company_result = self._ensure_company_exists_for_share(
                        share_result['entity'], ticker
                    )
                    self._update_results(results['companies'], company_result)
                    
                    # Ensure related entities exist
                    related_results = self._ensure_related_entities_exist(ticker)
                    self._update_results(results['countries'], related_results.get('country', {}))
                    self._update_results(results['sectors'], related_results.get('sector', {}))
                    self._update_results(results['industries'], related_results.get('industry', {}))
                
            except Exception as e:
                error_msg = f"Error ensuring entities exist for {ticker}: {str(e)}"
                results['errors'].append(error_msg)
                print(f"    ❌ {error_msg}")
        
        # Print summary
        self._print_summary(results, tickers)
        
        return results
    
    def _ensure_company_share_exists(self, ticker: str) -> Dict[str, Any]:
        """
        Ensure CompanyShare entity exists for the given ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with creation/verification result
        """
        try:
            # Use the standardized create-or-get method from CompanyShareRepository
            share = self.company_share_repository._create_or_get_company_share(
                ticker=ticker,
                exchange_id=1,
                company_id=None,  # Will be set when Company is created
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
                    print(f"    ✅ Created CompanyShare for {ticker}")
                    return {'status': 'created', 'entity': share}
                else:
                    return {'status': 'existing', 'entity': share}
            else:
                print(f"    ❌ Failed to create/get CompanyShare for {ticker}")
                return {'status': 'failed'}
                
        except Exception as e:
            print(f"    ❌ Error ensuring CompanyShare exists for {ticker}: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _ensure_company_exists_for_share(self, share: CompanyShareEntity, ticker: str) -> Dict[str, Any]:
        """
        Ensure Company entity exists for the given CompanyShare.
        
        Note: This is a placeholder implementation as there's no dedicated CompanyRepository yet.
        In a full implementation, this would use a CompanyRepository with _create_or_get_company.
        
        Args:
            share: CompanyShare entity
            ticker: Stock ticker symbol
            
        Returns:
            Dict with creation/verification result
        """
        try:
            # Check if share already has company_id set
            if hasattr(share, 'company_id') and share.company_id is not None:
                print(f"    ✅ Company already exists for {ticker} (ID: {share.company_id})")
                return {'status': 'existing'}
            
            # Since there's no CompanyRepository yet, we'll create a placeholder approach
            # In a full implementation, this would use CompanyRepository._create_or_get_company
            
            # For now, we simulate company creation by setting a company_id on the share
            # This would be replaced with actual Company entity creation when CompanyRepository is available
            
            print(f"    ⚠️  Company verification skipped for {ticker} - CompanyRepository not implemented")
            print(f"    💡 Suggestion: Create CompanyRepository with _create_or_get_company method")
            
            return {'status': 'skipped', 'reason': 'CompanyRepository not implemented'}
            
        except Exception as e:
            print(f"    ❌ Error ensuring Company exists for {ticker}: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _ensure_related_entities_exist(self, ticker: str) -> Dict[str, Dict[str, Any]]:
        """
        Ensure related entities (Country, Sector, Industry) exist.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with results for each entity type
        """
        results = {}
        
        try:
            # Ensure Country exists (default to USA for most stocks)
            country_result = self._ensure_country_exists("United States", "US")
            results['country'] = country_result
            
            # Ensure Sector exists (default to Technology)
            sector_result = self._ensure_sector_exists("Technology")
            results['sector'] = sector_result
            
            # Industry can be None for now
            results['industry'] = {'status': 'skipped'}
            
        except Exception as e:
            print(f"    ❌ Error ensuring related entities for {ticker}: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    def _ensure_country_exists(self, name: str, iso_code: str) -> Dict[str, Any]:
        """Ensure Country entity exists using CountryRepository."""
        try:
            country = self.country_repository._create_or_get_country(
                name=name,
                iso_code=iso_code
            )
            
            if country:
                return {'status': 'verified'}
            else:
                return {'status': 'failed'}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _ensure_sector_exists(self, name: str) -> Dict[str, Any]:
        """Ensure Sector entity exists using SectorRepository."""
        try:
            sector = self.sector_repository._create_or_get_sector(name=name)
            
            if sector:
                return {'status': 'verified'}
            else:
                return {'status': 'failed'}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
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