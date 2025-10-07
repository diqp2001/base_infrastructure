from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project_web import config
from application.services.misbuffet.web.web_interface import WebInterfaceManager

from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal

import logging
import requests
import time
import json
import threading
import webbrowser


class TestProjectWebManager(ProjectManager):
    """
    Enhanced Project Manager for web interface testing operations.
    Tests all web application URLs and functionality including PowerBuffet.
    """
    def __init__(self):
        super().__init__()
        # Initialize required managers
        self.setup_database_manager(DatabaseManager(config.CONFIG_TEST['DB_TYPE']))
        self.company_share_repository_local = CompanyShareRepositoryLocal(self.database_manager.session)
        
        # Web testing components
        self.data_generator = None
        self.algorithm = None
        self.results = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Web interface manager
        self.web_interface = WebInterfaceManager()
        
        # Base URL for testing
        self.base_url = "http://localhost:5000"
        
        # Define all web app URLs to test
        self.web_urls = {
            'home': '/',
            'dashboard': '/dashboard',
            'powerbuffet': '/powerbuffet',
            'test_backtest_get': '/test_backtest',
            'test_live_trading_get': '/test_live_trading',
            'backtest_progress': '/backtest_progress',
            'progress_stream': '/progress_stream',
            'api_powerbuffet_databases': '/api/powerbuffet/databases',
            'api_powerbuffet_visualizations': '/api/powerbuffet/visualizations',
            'api_entities_company_shares': '/api/entities/company_shares',
            'api_entities_summary': '/api/entities/summary'
        }
        
        # Define POST endpoints that require special testing
        self.post_urls = {
            'api_backtest': '/api/backtest',
            'api_test_managers_backtest': '/api/test_managers/backtest',
            'api_test_managers_live_trading': '/api/test_managers/live_trading',
            'api_powerbuffet_run_visualization': '/api/powerbuffet/run_visualization'
        }

    def run(self):
        """Main run method that launches web interface and tests all URLs"""
        try:
            self.logger.info("🚀 Starting TestProjectWebManager - Web Interface Testing")
            
            # Start web interface and open browser
            self.web_interface.start_interface_and_open_browser()
            
            # Wait for web interface to start
            self.logger.info("⏳ Waiting for web interface to start...")
            time.sleep(8)
            
            # Test all GET web URLs
            self.test_all_web_urls()
            
            # Test POST endpoints
            self.test_post_endpoints()
            
            # Test PowerBuffet functionality specifically
            self.test_powerbuffet_functionality()
            
            # Keep server running for manual testing
            self.logger.info("🌐 All tests completed! Web interface is running at http://localhost:5000")
            self.logger.info("📊 PowerBuffet is accessible at http://localhost:5000/powerbuffet")
            self.logger.info("⌨️  Press Ctrl+C to stop the server")
            
            # Open PowerBuffet in browser for manual testing
            time.sleep(2)
            webbrowser.open(f'{self.base_url}/powerbuffet')
            
            # Keep running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("🛑 Server shutting down...")
                
        except Exception as e:
            self.logger.error(f"❌ Error in TestProjectWebManager: {e}")
            raise
    
    def test_all_web_urls(self):
        """Test all web application URLs"""
        self.logger.info("🧪 Testing all web application URLs...")
        
        test_results = {}
        
        for name, url in self.web_urls.items():
            try:
                full_url = f"{self.base_url}{url}"
                self.logger.info(f"Testing {name}: {full_url}")
                
                response = requests.get(full_url, timeout=10)
                test_results[name] = {
                    'url': full_url,
                    'status_code': response.status_code,
                    'success': response.status_code == 200,
                    'response_time': response.elapsed.total_seconds()
                }
                
                if response.status_code == 200:
                    self.logger.info(f"✅ {name} - SUCCESS ({response.status_code}) - {response.elapsed.total_seconds():.2f}s")
                else:
                    self.logger.warning(f"⚠️  {name} - FAILED ({response.status_code}) - {response.elapsed.total_seconds():.2f}s")
                    
            except requests.exceptions.RequestException as e:
                test_results[name] = {
                    'url': f"{self.base_url}{url}",
                    'status_code': None,
                    'success': False,
                    'error': str(e)
                }
                self.logger.error(f"❌ {name} - ERROR: {e}")
        
        # Print summary
        successful_tests = sum(1 for result in test_results.values() if result['success'])
        total_tests = len(test_results)
        
        self.logger.info(f"📊 URL Testing Summary: {successful_tests}/{total_tests} tests passed")
        
        return test_results
    
    def test_post_endpoints(self):
        """Test POST endpoints with sample data"""
        self.logger.info("🔐 Testing POST endpoints...")
        
        test_results = {}
        
        for name, url in self.post_urls.items():
            try:
                full_url = f"{self.base_url}{url}"
                self.logger.info(f"Testing POST {name}: {full_url}")
                
                # Prepare sample data based on endpoint
                sample_data = self._get_sample_post_data(name)
                
                response = requests.post(full_url, json=sample_data, timeout=30)
                test_results[name] = {
                    'url': full_url,
                    'status_code': response.status_code,
                    'success': response.status_code in [200, 400, 422],  # Accept validation errors
                    'response_time': response.elapsed.total_seconds()
                }
                
                if response.status_code == 200:
                    self.logger.info(f"✅ POST {name} - SUCCESS ({response.status_code}) - {response.elapsed.total_seconds():.2f}s")
                elif response.status_code in [400, 422]:
                    self.logger.info(f"⚠️  POST {name} - VALIDATION ERROR ({response.status_code}) - Expected for sample data")
                else:
                    self.logger.warning(f"❌ POST {name} - FAILED ({response.status_code}) - {response.elapsed.total_seconds():.2f}s")
                    
            except requests.exceptions.RequestException as e:
                test_results[name] = {
                    'url': f"{self.base_url}{url}",
                    'status_code': None,
                    'success': False,
                    'error': str(e)
                }
                self.logger.error(f"❌ POST {name} - ERROR: {e}")
        
        # Print summary
        successful_tests = sum(1 for result in test_results.values() if result['success'])
        total_tests = len(test_results)
        
        self.logger.info(f"📊 POST Testing Summary: {successful_tests}/{total_tests} tests passed")
        
        return test_results
    
    def _get_sample_post_data(self, endpoint_name):
        """Get sample data for POST endpoint testing"""
        sample_data = {
            'api_backtest': {
                'algorithm': 'test_algorithm',
                'start_date': '2024-01-01',
                'end_date': '2024-12-31',
                'initial_capital': 100000
            },
            'api_test_managers_backtest': {},
            'api_test_managers_live_trading': {},
            'api_powerbuffet_run_visualization': {
                'database_path': '/test/path',
                'table_name': 'test_table',
                'visualization_name': 'Portfolio Performance',
                'params': {}
            }
        }
        return sample_data.get(endpoint_name, {})
    
    def test_powerbuffet_functionality(self):
        """Test PowerBuffet specific functionality"""
        self.logger.info("🔬 Testing PowerBuffet functionality...")
        
        try:
            # Test database discovery
            databases_url = f"{self.base_url}/api/powerbuffet/databases"
            response = requests.get(databases_url, timeout=10)
            
            if response.status_code == 200:
                databases_data = response.json()
                self.logger.info(f"✅ PowerBuffet databases API - SUCCESS")
                self.logger.info(f"📁 Found {len(databases_data.get('databases', []))} databases")
                
                # Test visualizations API
                viz_url = f"{self.base_url}/api/powerbuffet/visualizations"
                viz_response = requests.get(viz_url, timeout=10)
                
                if viz_response.status_code == 200:
                    viz_data = viz_response.json()
                    self.logger.info(f"✅ PowerBuffet visualizations API - SUCCESS")
                    self.logger.info(f"📈 Found {len(viz_data.get('visualizations', []))} visualization types")
                    
                    # Test table discovery if databases exist
                    if databases_data.get('databases') and len(databases_data['databases']) > 0:
                        first_db = databases_data['databases'][0]
                        tables_url = f"{self.base_url}/api/powerbuffet/tables/{requests.utils.quote(first_db['path'], safe='')}"
                        tables_response = requests.get(tables_url, timeout=10)
                        
                        if tables_response.status_code == 200:
                            tables_data = tables_response.json()
                            self.logger.info(f"✅ PowerBuffet tables API - SUCCESS")
                            self.logger.info(f"🗃️  Found {len(tables_data.get('tables', []))} tables in {first_db['name']}")
                            
                            # Test visualization generation if we have tables and visualizations
                            if (tables_data.get('tables') and len(tables_data['tables']) > 0 and
                                viz_data.get('visualizations') and len(viz_data['visualizations']) > 0):
                                
                                self.test_powerbuffet_visualization(
                                    first_db['path'], 
                                    tables_data['tables'][0]['name'],
                                    viz_data['visualizations'][0]
                                )
                        else:
                            self.logger.warning(f"⚠️  PowerBuffet tables API - FAILED ({tables_response.status_code})")
                    else:
                        self.logger.info("ℹ️  No databases found for table testing")
                        
                else:
                    self.logger.warning(f"⚠️  PowerBuffet visualizations API - FAILED ({viz_response.status_code})")
                    
            else:
                self.logger.warning(f"⚠️  PowerBuffet databases API - FAILED ({response.status_code})")
                
        except Exception as e:
            self.logger.error(f"❌ PowerBuffet functionality test error: {e}")
    
    def test_powerbuffet_visualization(self, database_path, table_name, visualization_name):
        """Test PowerBuffet visualization generation"""
        try:
            viz_url = f"{self.base_url}/api/powerbuffet/run_visualization"
            
            payload = {
                'database_path': database_path,
                'table_name': table_name,
                'visualization_name': visualization_name,
                'params': {}
            }
            
            response = requests.post(viz_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.logger.info(f"✅ PowerBuffet visualization '{visualization_name}' - SUCCESS")
                    if result.get('visualization', {}).get('plot_image'):
                        self.logger.info(f"🖼️  Visualization image generated successfully")
                    else:
                        self.logger.warning(f"⚠️  Visualization completed but no image generated")
                else:
                    self.logger.warning(f"⚠️  PowerBuffet visualization - FAILED: {result.get('error', 'Unknown error')}")
            else:
                self.logger.warning(f"⚠️  PowerBuffet visualization API - FAILED ({response.status_code})")
                
        except Exception as e:
            self.logger.error(f"❌ PowerBuffet visualization test error: {e}")