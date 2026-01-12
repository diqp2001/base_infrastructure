"""
IBKR Company Repository - Interactive Brokers implementation for Companies.

This repository handles data acquisition and normalization from the IBKR API,
applying IBKR-specific business rules before delegating persistence to the local repository.
"""

from typing import Optional, List

from ibapi.contract import Contract, ContractDetails

from domain.ports.factor.factor_value_port import FactorValuePort
from src.domain.ports.finance.company_port import CompanyPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository
from src.infrastructure.repositories.local_repo.base_repository import BaseRepository
from src.domain.entities.finance.company import Company


class IBKRCompanyRepository(BaseRepository, CompanyPort):
    """
    IBKR implementation of CompanyPort.
    Handles data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_repo: CompanyPort, local_factor_value_repo: FactorValuePort):
        """
        Initialize IBKR Company Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_repo: Local repository implementing CompanyPort for persistence
        """
        self.ibkr = ibkr_client
        self.local_repo = local_repo
        self.local_factor_value_repo = local_factor_value_repo

    def get_or_create(self, symbol_or_name: str) -> Optional[Company]:
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
            contract_details = self._fetch_contract_details(contract)
            if not contract_details:
                return None
                
            # 4. Apply IBKR-specific rules and convert to domain entity
            entity = self._contract_to_company_domain(contract, contract_details)
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
            
            list_of_value = self.local_factor_value_repo.get_all_dates_by_id_entity_id(factor_id,entity.id)
            #if time selected is in list_of_value return the existing facor value
            if existing:
                return existing
            # 2. Fetch company info via stock contract from IBKR API
            contract = self._fetch_stock_contract(symbol_or_name)
            if not contract:
                return None
                
            # 3. Get contract details from IBKR
            contract_details = self._fetch_contract_details(contract)
            if not contract_details:
                return None
                
            # 4. Apply IBKR-specific rules and convert to domain entity
            entity = self._contract_to_company_domain(contract, contract_details)
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

    def _fetch_contract_details(self, contract: Contract) -> Optional[ContractDetails]:
        """
        Fetch contract details from IBKR API.
        
        Args:
            contract: IBKR Contract object
            
        Returns:
            ContractDetails object or None if not found
        """
        try:
            # Mock implementation - in real code use self.ibkr.reqContractDetails()
            contract_details = ContractDetails()
            contract_details.contract = contract
            contract_details.marketName = "Stock Market"
            contract_details.longName = f"{contract.symbol} Inc."
            contract_details.industry = self._get_mock_industry(contract.symbol)
            contract_details.category = "Common Stock"
            
            # Company-specific details that IBKR might provide
            contract_details.timeZoneId = "EST"
            contract_details.tradingHours = "20091201:0930-1600;20091202:0930-1600"
            contract_details.liquidHours = "20091201:0930-1600;20091202:0930-1600"
            
            return contract_details
        except Exception as e:
            print(f"Error fetching IBKR contract details: {e}")
            return None

    def _contract_to_company_domain(self, contract: Contract, contract_details: ContractDetails) -> Optional[Company]:
        """
        Convert IBKR contract and details directly to Company domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            
        Returns:
            Company domain entity or None if conversion failed
        """
        try:
            company_name = getattr(contract_details, 'longName', f"{contract.symbol} Inc.")
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
                ibkr_industry=getattr(contract_details, 'industry', ''),
                ibkr_category=getattr(contract_details, 'category', ''),
                ibkr_time_zone=getattr(contract_details, 'timeZoneId', ''),
                ibkr_trading_hours=getattr(contract_details, 'tradingHours', ''),
                ibkr_liquid_hours=getattr(contract_details, 'liquidHours', '')
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

    def _resolve_industry_info(self, contract_details: ContractDetails) -> dict:
        """Resolve industry and sector IDs from IBKR data."""
        industry = getattr(contract_details, 'industry', 'Technology')
        
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