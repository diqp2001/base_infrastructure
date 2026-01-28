"""
IBKR Company Repository - Interactive Brokers implementation for Companies.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List

from ibapi.contract import Contract, ContractDetails

from src.domain.ports.factor.factor_value_port import FactorValuePort
from src.domain.ports.finance.company_port import CompanyPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.domain.entities.finance.company import Company
from src.infrastructure.repositories.mappers.finance.company_mapper import CompanyMapper


class IBKRCompanyRepository(BaseIBKRRepository, CompanyPort):
    """
    IBKR implementation of CompanyPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory, mapper: CompanyMapper = None):
        """
        Initialize IBKR Company Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client (InteractiveBrokersBroker instance)
            factory: Repository factory for dependency injection (preferred)
            mapper: Company mapper for entity/model conversion (optional, will create if not provided)
        """
        self.ib_broker = ibkr_client  # Use ib_broker for consistency with reference implementation
        
        self.factory = factory
        self.local_repo = self.factory.company_local_repo
        self.mapper = mapper or CompanyMapper()

    @property
    def entity_class(self):
        """Return the domain entity class for Company."""
        return Company

    def _create_or_get(self, symbol_or_name: str) -> Optional[Company]:
        """
        Get or create a company by symbol or name using IBKR API.
        
        Args:
            symbol_or_name: Stock symbol or company name
            
        Returns:
            Company entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            existing = self.local_repo.get_by_name(symbol_or_name)
            if existing:
                return existing
            
            # 2. Fetch company info via stock contract from IBKR API
            contract = self._fetch_stock_contract(symbol_or_name)
            if not contract:
                return None
                
            # 3. Get contract details from IBKR
            contract_details_list = self._fetch_contract_details(contract)
            if not contract_details_list:
                return None
                
            # 4. Apply IBKR-specific rules and convert to domain entity
            entity = self._contract_to_company_domain(contract, contract_details_list)
            if not entity:
                return None
                
            # 5. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for company {symbol_or_name}: {e}")
            return None
        
    def get_or_create_factor_value(self, symbol_or_name: str, factor_id: str, time) -> Optional[Company]:
        """
        Get or create a company by symbol or name using IBKR API.
        
        Args:
            symbol_or_name: Stock symbol or company name
            
        Returns:
            Company entity or None if creation/retrieval failed
        """
        try:
            # 1. Check local repository first
            entity = self.local_repo.get_by_name(symbol_or_name)
            
            list_of_value = self.factory.factor_value_local_repo.get_all_dates_by_id_entity_id(factor_id,entity.id)
            #if time selected is in list_of_value return the existing facor value
            if existing:
                return existing
            # 2. Fetch company info via stock contract from IBKR API
            contract = self._fetch_stock_contract(symbol_or_name)
            if not contract:
                return None
                
            # 3. Get contract details from IBKR
            contract_details_list = self._fetch_contract_details(contract)
            if not contract_details_list:
                return None
                
            # 4. Apply IBKR-specific rules and convert to domain entity
            entity = self._contract_to_company_domain(contract, contract_details_list)
            if not entity:
                return None
                
            # 5. Delegate persistence to local repository
            return self.local_repo.add(entity)
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for company {symbol_or_name}: {e}")
            return None


    def get_by_name(self, name: str) -> Optional[Company]:
        """Get company by name (delegates to local repository)."""
        return self.local_repo.get_by_name(name)

    def get_by_symbol(self, symbol: str) -> Optional[Company]:
        """Get company by stock symbol (delegates to local repository)."""
        return self.local_repo.get_by_symbol(symbol)

    def get_by_id(self, entity_id: int) -> Optional[Company]:
        """Get company by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_all(self) -> List[Company]:
        """Get all companies (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Company) -> Optional[Company]:
        """Add company entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity: Company) -> Optional[Company]:
        """Update company entity (delegates to local repository)."""
        return self.local_repo.update(entity)

    def delete(self, entity_id: int) -> bool:
        """Delete company entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def _fetch_stock_contract(self, symbol_or_name: str) -> Optional[Contract]:
        """
        Fetch stock contract to get company information.
        
        Args:
            symbol_or_name: Stock symbol or company name
            
        Returns:
            IBKR Contract object or None if not found
        """
        try:
            contract = Contract()
            # Try as symbol first
            if len(symbol_or_name) <= 5 and symbol_or_name.isupper():
                contract.symbol = symbol_or_name
            else:
                # If it looks like a company name, we'd need different approach
                # For now, assume it's a symbol
                contract.symbol = symbol_or_name.upper()
            
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            return contract
        except Exception as e:
            print(f"Error fetching IBKR stock contract for {symbol_or_name}: {e}")
            return None

    def _fetch_contract_details(self, contract: Contract) -> Optional[List[dict]]:
        """
        Fetch contract details from IBKR API using broker method.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            List of contract details dictionaries or None if not found
        """
        try:
            # Use the broker's get_contract_details method (like in reference implementation)
            contract_details = self.ib_broker.get_contract_details(contract, timeout=15)
            
            if contract_details and len(contract_details) > 0:
                return contract_details
            else:
                print(f"No contract details received for {contract.symbol}")
                return None
                
        except Exception as e:
            print(f"Error fetching IBKR contract details: {e}")
            return None

    def _contract_to_company_domain(self, contract: Contract, contract_details_list: List[dict]) -> Optional[Company]:
        """
        Convert IBKR contract and details to domain entity using real API data.
        
        Args:
            contract: IBKR Contract object
            contract_details_list: List of contract details dictionaries from IBKR API
            
        Returns:
            Company domain entity or None if conversion failed
        """
        try:
            # Use the first contract details result
            contract_details = contract_details_list[0] if contract_details_list else {}
            
            company_name = contract_details.get('long_name', f"{contract.symbol} Inc.")
            industry_info = self._resolve_industry_info(contract_details)
            
            return Company(
                id=None,  # Let database generate
                name=company_name,
                legal_name=company_name,
                ticker_symbol=contract.symbol,
                country_id=self._resolve_country_id(contract),
                industry_id=industry_info['industry_id'],
                sector_id=industry_info['sector_id'],
                founded_year=None,  # Would need separate data source
                employee_count=None,  # Would need separate data source
                market_cap=None,  # Would need market data
                description=f"{company_name} is a publicly traded company",
                # IBKR-specific fields
                ibkr_contract_id=getattr(contract, 'conId', None),
                ibkr_primary_exchange=getattr(contract, 'primaryExchange', ''),
                ibkr_industry=contract_details.get('industry', ''),
                ibkr_category=contract_details.get('category', ''),
                ibkr_time_zone=contract_details.get('time_zone_id', ''),
                ibkr_trading_hours=contract_details.get('trading_hours', ''),
                ibkr_liquid_hours=contract_details.get('liquid_hours', '')
            )
        except Exception as e:
            print(f"Error converting IBKR contract to company domain entity: {e}")
            return None

    def _get_mock_industry(self, symbol: str) -> str:
        """Get mock industry for demonstration (would use real IBKR data)."""
        industry_map = {
            'AAPL': 'Technology Hardware & Equipment',
            'MSFT': 'Software',
            'GOOGL': 'Interactive Media & Services',
            'AMZN': 'Internet & Direct Marketing Retail',
            'TSLA': 'Automobiles',
            'NVDA': 'Semiconductors & Semiconductor Equipment',
            'META': 'Interactive Media & Services',
            'JPM': 'Banks',
            'JNJ': 'Pharmaceuticals',
            'V': 'Data Processing & Outsourced Services'
        }
        return industry_map.get(symbol, 'Technology')

    def _resolve_industry_info(self, contract_details: dict) -> dict:
        """Resolve industry and sector IDs from IBKR data."""
        industry = contract_details.get('industry', 'Technology')
        
        # Map IBKR industry to our internal IDs (simplified)
        industry_mapping = {
            'Technology Hardware & Equipment': {'industry_id': 1, 'sector_id': 1},
            'Software': {'industry_id': 2, 'sector_id': 1},
            'Interactive Media & Services': {'industry_id': 3, 'sector_id': 1},
            'Internet & Direct Marketing Retail': {'industry_id': 4, 'sector_id': 2},
            'Automobiles': {'industry_id': 5, 'sector_id': 3},
            'Semiconductors & Semiconductor Equipment': {'industry_id': 6, 'sector_id': 1},
            'Banks': {'industry_id': 7, 'sector_id': 4},
            'Pharmaceuticals': {'industry_id': 8, 'sector_id': 5},
            'Data Processing & Outsourced Services': {'industry_id': 9, 'sector_id': 1}
        }
        
        return industry_mapping.get(industry, {'industry_id': 1, 'sector_id': 1})

    def _resolve_country_id(self, contract: Contract) -> int:
        """Resolve country ID from contract data."""
        # Most IBKR stocks are US-based unless specifically indicated
        currency_to_country = {
            'USD': 1,  # USA
            'CAD': 2,  # Canada
            'GBP': 3,  # UK
            'EUR': 4,  # Europe (generic)
            'JPY': 5,  # Japan
        }
        return currency_to_country.get(contract.currency, 1)

    def get_companies_by_industry(self, industry_name: str) -> List[Company]:
        """Get companies by industry using IBKR industry classification."""
        # This would involve searching IBKR for companies in specific industries
        # For now, delegate to local repository
        return self.local_repo.get_companies_by_industry(industry_name)

    def get_companies_by_sector(self, sector_name: str) -> List[Company]:
        """Get companies by sector using IBKR sector classification."""
        # This would involve searching IBKR for companies in specific sectors
        # For now, delegate to local repository
        return self.local_repo.get_companies_by_sector(sector_name)

    def search_companies_by_name(self, partial_name: str) -> List[Company]:
        """Search for companies by partial name match."""
        # IBKR provides company search functionality
        # For now, delegate to local repository
        return self.local_repo.search_companies_by_name(partial_name)

    def get_sp500_companies(self) -> List[Company]:
        """Get S&P 500 companies from IBKR."""
        # This would use IBKR's index constituent functionality
        # For demonstration, return a subset
        sp500_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 
            'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'DIS', 'BAC'
        ]
        
        companies = []
        for symbol in sp500_symbols:
            company = self.get_or_create(symbol)
            if company:
                companies.append(company)
        
        return companies