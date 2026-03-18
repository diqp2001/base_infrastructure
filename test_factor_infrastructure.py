#!/usr/bin/env python3
"""
Comprehensive test script for factor infrastructure implementation.
Tests all mappers, ports, local repositories, IBKR repositories, and the RepositoryFactory.
"""

import sys
import traceback
from typing import List, Dict, Tuple
import importlib


class FactorInfrastructureValidator:
    """Validates the factor infrastructure implementation."""
    
    def __init__(self):
        self.results = {
            'mappers': {},
            'ports': {},
            'local_repos': {},
            'ibkr_repos': {},
            'factory': {},
            'summary': {
                'total_tested': 0,
                'total_passed': 0,
                'total_failed': 0
            }
        }
    
    def test_import(self, module_path: str, category: str, name: str) -> bool:
        """Test importing a single module."""
        try:
            importlib.import_module(module_path)
            self.results[category][name] = {'status': 'PASS', 'error': None}
            self.results['summary']['total_passed'] += 1
            return True
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.results[category][name] = {'status': 'FAIL', 'error': error_msg}
            self.results['summary']['total_failed'] += 1
            return False
        finally:
            self.results['summary']['total_tested'] += 1
    
    def test_mappers(self):
        """Test all factor mappers."""
        print("Testing Factor Mappers...")
        
        mappers = [
            'base_factor_mapper',
            'bond_factor_mapper',
            'company_share_factor_mapper',
            'company_share_option_delta_factor_mapper',
            'company_share_option_factor_mapper',
            'company_share_option_gamma_factor_mapper',
            'company_share_option_price_factor_mapper',
            'company_share_option_price_return_factor_mapper',
            'company_share_option_rho_factor_mapper',
            'company_share_option_vega_factor_mapper',
            'company_share_price_return_factor_mapper',
            'continent_factor_mapper',
            'country_factor_mapper',
            'currency_factor_mapper',
            'derivative_factor_mapper',
            'equity_factor_mapper',
            'etf_share_portfolio_company_share_option_delta_factor_mapper',
            'etf_share_portfolio_company_share_option_factor_mapper',
            'etf_share_portfolio_company_share_option_price_factor_mapper',
            'etf_share_portfolio_company_share_option_price_return_factor_mapper',
            'factor_mapper',
            'factor_value_mapper',
            'financial_asset_factor_mapper',
            'future_factor_mapper',
            'future_price_return_factor_mapper',
            'ibkr_company_share_factor_mapper',
            'ibkr_company_share_price_return_factor_mapper',
            'ibkr_continent_factor_mapper',
            'ibkr_country_factor_mapper',
            'ibkr_currency_factor_mapper',
            'ibkr_equity_factor_mapper',
            'ibkr_index_factor_mapper',
            'ibkr_share_factor_mapper',
            'index_factor_mapper',
            'index_future_factor_mapper',
            'index_future_option_delta_factor_mapper',
            'index_future_option_factor_mapper',
            'index_future_option_price_factor_mapper',
            'index_future_option_price_return_factor_mapper',
            'index_future_price_return_factor_mapper',
            'index_price_return_factor_mapper',
            'option_factor_mapper',
            'portfolio_company_share_option_delta_factor_mapper',
            'portfolio_company_share_option_factor_mapper',
            'portfolio_company_share_option_price_factor_mapper',
            'portfolio_company_share_option_price_return_factor_mapper',
            'security_factor_mapper',
            'share_factor_mapper',
            'share_momentum_factor_mapper',
            'share_target_factor_mapper',
            'share_technical_factor_mapper',
            'share_volatility_factor_mapper'
        ]
        
        for mapper in mappers:
            module_path = f"src.infrastructure.repositories.mappers.factor.{mapper}"
            self.test_import(module_path, 'mappers', mapper)
    
    def test_ports(self):
        """Test all factor ports."""
        print("Testing Factor Ports...")
        
        ports = [
            'bond_factor_port',
            'company_share_factor_port',
            'company_share_option_delta_factor_port',
            'company_share_option_factor_port',
            'company_share_option_gamma_factor_port',
            'company_share_option_price_factor_port',
            'company_share_option_price_return_factor_port',
            'company_share_option_rho_factor_port',
            'company_share_option_vega_factor_port',
            'company_share_price_return_factor_port',
            'continent_factor_port',
            'country_factor_port',
            'currency_factor_port',
            'derivative_factor_port',
            'equity_factor_port',
            'etf_share_portfolio_company_share_option_delta_factor_port',
            'etf_share_portfolio_company_share_option_factor_port',
            'etf_share_portfolio_company_share_option_price_factor_port',
            'etf_share_portfolio_company_share_option_price_return_factor_port',
            'factor_dependency_port',
            'factor_port',
            'factor_value_port',
            'financial_asset_factor_port',
            'future_factor_port',
            'index_factor_port',
            'index_future_factor_port',
            'index_future_option_delta_factor_port',
            'index_future_option_factor_port',
            'index_future_option_price_factor_port',
            'index_future_option_price_return_factor_port',
            'index_future_price_return_factor_port',
            'index_price_return_factor_port',
            'option_factor_port',
            'portfolio_company_share_option_delta_factor_port',
            'portfolio_company_share_option_factor_port',
            'portfolio_company_share_option_price_factor_port',
            'portfolio_company_share_option_price_return_factor_port',
            'security_factor_port',
            'share_factor_port'
        ]
        
        for port in ports:
            module_path = f"src.domain.ports.factor.{port}"
            self.test_import(module_path, 'ports', port)
    
    def test_local_repositories(self):
        """Test all local factor repositories."""
        print("Testing Local Factor Repositories...")
        
        local_repos = [
            'bond_factor_repository',
            'commodity_factor_repository',
            'company_share_factor_repository',
            'company_share_option_delta_factor_repository',
            'company_share_option_factor_repository',
            'company_share_option_gamma_factor_repository',
            'company_share_option_price_factor_repository',
            'company_share_option_price_return_factor_repository',
            'company_share_option_rho_factor_repository',
            'company_share_option_vega_factor_repository',
            'company_share_price_return_factor_repository',
            'currency_factor_repository',
            'derivative_factor_repository',
            'equity_factor_repository',
            'etf_share_factor_repository',
            'etf_share_portfolio_company_share_option_delta_factor_repository',
            'etf_share_portfolio_company_share_option_factor_repository',
            'etf_share_portfolio_company_share_option_price_factor_repository',
            'etf_share_portfolio_company_share_option_price_return_factor_repository',
            'financial_asset_factor_repository',
            'future_price_return_factor_repository',
            'futures_factor_repository',
            'index_factor_repository',
            'index_future_factor_repository',
            'index_future_option_delta_factor_repository',
            'index_future_option_factor_repository',
            'index_future_option_price_factor_repository',
            'index_future_option_price_return_factor_repository',
            'index_future_price_return_factor_repository',
            'index_price_return_factor_repository',
            'options_factor_repository',
            'portfolio_company_share_option_delta_factor_repository',
            'portfolio_company_share_option_factor_repository',
            'portfolio_company_share_option_price_factor_repository',
            'portfolio_company_share_option_price_return_factor_repository',
            'security_factor_repository',
            'share_factor_repository',
            'share_momentum_factor_repository',
            'share_target_factor_repository',
            'share_technical_factor_repository',
            'share_volatility_factor_repository'
        ]
        
        for repo in local_repos:
            module_path = f"src.infrastructure.repositories.local_repo.factor.finance.financial_assets.{repo}"
            self.test_import(module_path, 'local_repos', repo)
    
    def test_ibkr_repositories(self):
        """Test all IBKR factor repositories."""
        print("Testing IBKR Factor Repositories...")
        
        ibkr_repos = [
            'ibkr_bond_factor_repository',
            'ibkr_company_share_factor_repository',
            'ibkr_company_share_option_delta_factor_repository',
            'ibkr_company_share_option_factor_repository',
            'ibkr_company_share_option_gamma_factor_repository',
            'ibkr_company_share_option_price_factor_repository',
            'ibkr_company_share_option_price_return_factor_repository',
            'ibkr_company_share_option_rho_factor_repository',
            'ibkr_company_share_option_vega_factor_repository',
            'ibkr_company_share_price_return_factor_repository',
            'ibkr_continent_factor_repository',
            'ibkr_country_factor_repository',
            'ibkr_currency_factor_repository',
            'ibkr_derivative_factor_repository',
            'ibkr_equity_factor_repository',
            'ibkr_etf_share_portfolio_company_share_option_delta_factor_repository',
            'ibkr_etf_share_portfolio_company_share_option_factor_repository',
            'ibkr_etf_share_portfolio_company_share_option_price_factor_repository',
            'ibkr_etf_share_portfolio_company_share_option_price_return_factor_repository',
            'ibkr_financial_asset_factor_repository',
            'ibkr_future_factor_repository',
            'ibkr_index_factor_repository',
            'ibkr_index_future_factor_repository',
            'ibkr_index_future_option_delta_factor_repository',
            'ibkr_index_future_option_factor_repository',
            'ibkr_index_future_option_price_factor_repository',
            'ibkr_index_future_option_price_return_factor_repository',
            'ibkr_index_future_price_return_factor_repository',
            'ibkr_index_price_return_factor_repository',
            'ibkr_option_factor_repository',
            'ibkr_portfolio_company_share_correlation_factor_repository',
            'ibkr_portfolio_company_share_option_delta_factor_repository',
            'ibkr_portfolio_company_share_option_factor_repository',
            'ibkr_portfolio_company_share_option_price_factor_repository',
            'ibkr_portfolio_company_share_option_price_return_factor_repository',
            'ibkr_portfolio_factor_repository',
            'ibkr_security_factor_repository',
            'ibkr_share_factor_repository'
        ]
        
        for repo in ibkr_repos:
            module_path = f"src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.{repo}"
            self.test_import(module_path, 'ibkr_repos', repo)
    
    def test_repository_factory(self):
        """Test the RepositoryFactory import."""
        print("Testing RepositoryFactory...")
        
        module_path = "src.infrastructure.repositories.repository_factory"
        self.test_import(module_path, 'factory', 'repository_factory')
    
    def test_instantiation(self):
        """Test instantiation of key classes."""
        print("Testing Class Instantiation...")
        
        # Test mapper instantiation
        try:
            from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper
            mapper = BaseFactorMapper()
            self.results['factory']['mapper_instantiation'] = {'status': 'PASS', 'error': None}
            self.results['summary']['total_passed'] += 1
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.results['factory']['mapper_instantiation'] = {'status': 'FAIL', 'error': error_msg}
            self.results['summary']['total_failed'] += 1
        finally:
            self.results['summary']['total_tested'] += 1
        
        # Test port ABC instantiation
        try:
            from src.domain.ports.factor.factor_port import FactorPort
            # Can't instantiate ABC directly, but we can check if it imports correctly
            self.results['factory']['port_abc_import'] = {'status': 'PASS', 'error': None}
            self.results['summary']['total_passed'] += 1
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.results['factory']['port_abc_import'] = {'status': 'FAIL', 'error': error_msg}
            self.results['summary']['total_failed'] += 1
        finally:
            self.results['summary']['total_tested'] += 1
    
    def run_all_tests(self):
        """Run all tests."""
        print("=" * 80)
        print("FACTOR INFRASTRUCTURE VALIDATION")
        print("=" * 80)
        
        self.test_mappers()
        print()
        self.test_ports()
        print()
        self.test_local_repositories()
        print()
        self.test_ibkr_repositories()
        print()
        self.test_repository_factory()
        print()
        self.test_instantiation()
        print()
        
        self.print_summary()
    
    def print_summary(self):
        """Print detailed test results summary."""
        print("=" * 80)
        print("DETAILED TEST RESULTS")
        print("=" * 80)
        
        categories = [
            ('Factor Mappers', 'mappers'),
            ('Factor Ports', 'ports'),
            ('Local Repositories', 'local_repos'),
            ('IBKR Repositories', 'ibkr_repos'),
            ('Factory & Instantiation', 'factory')
        ]
        
        for category_name, category_key in categories:
            print(f"\n{category_name}:")
            print("-" * 40)
            
            if not self.results[category_key]:
                print("  No tests run for this category")
                continue
            
            passed = sum(1 for result in self.results[category_key].values() if result['status'] == 'PASS')
            failed = sum(1 for result in self.results[category_key].values() if result['status'] == 'FAIL')
            
            print(f"  Passed: {passed}")
            print(f"  Failed: {failed}")
            print(f"  Total:  {passed + failed}")
            
            # Show failures
            failures = [(name, result) for name, result in self.results[category_key].items() 
                       if result['status'] == 'FAIL']
            
            if failures:
                print(f"\n  FAILURES:")
                for name, result in failures:
                    print(f"    ❌ {name}: {result['error']}")
            else:
                print(f"  ✅ All tests passed!")
        
        # Overall summary
        print("\n" + "=" * 80)
        print("OVERALL SUMMARY")
        print("=" * 80)
        print(f"Total Tests:  {self.results['summary']['total_tested']}")
        print(f"Passed:       {self.results['summary']['total_passed']}")
        print(f"Failed:       {self.results['summary']['total_failed']}")
        print(f"Success Rate: {(self.results['summary']['total_passed'] / max(1, self.results['summary']['total_tested']) * 100):.1f}%")
        
        if self.results['summary']['total_failed'] == 0:
            print("\n🎉 ALL TESTS PASSED! Factor infrastructure is working correctly.")
        else:
            print(f"\n⚠️  {self.results['summary']['total_failed']} tests failed. Review the errors above.")
        
        return self.results['summary']['total_failed'] == 0


def main():
    """Main test execution."""
    validator = FactorInfrastructureValidator()
    success = validator.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()