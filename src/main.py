

from cProfile import Profile
from pstats import SortKey, Stats


from application.managers.project_managers.cross_sectionnal_project.cross_sectionnal_project_manager import CrossSectionnal
from application.managers.project_managers.test_base_project.test_base_project_manager import TestBaseProjectManager
from application.services.api_service.ercot_service.ercot_public_api_service import ErcotPublicApiService







def verify_ercot_api_connection():
    """
    Verify ERCOT API connection and display results.
    
    Returns:
        bool: True if API is healthy, False otherwise
    """
    print("=== ERCOT API Connection Verification ===")
    
    try:
        service = ErcotPublicApiService()
        health_check = service.check_api_health()
        
        print(f"API Status: {health_check['status'].upper()}")
        print(f"Base URL: {health_check['base_url']}")
        print(f"API Responsive: {health_check['api_responsive']}")
        
        if health_check.get('rate_limit'):
            print(f"Rate Limit: {health_check['rate_limit']['max_requests_per_minute']} requests/min")
            
        if health_check.get('test_date'):
            print(f"Test Date Used: {health_check['test_date']}")
            
        print(f"Timestamp: {health_check['timestamp']}")
        
        if health_check.get('error'):
            print(f"Error: {health_check['error']}")
            
        is_healthy = health_check['status'] == 'healthy'
        print(f"\n✅ Connection {'SUCCESSFUL' if is_healthy else '❌ FAILED'}")
        
        return is_healthy
        
    except Exception as e:
        print(f"❌ Connection verification failed: {e}")
        return False


if __name__ == '__main__':
    #TestBaseProjectManager().web_interface.start_interface_and_open_browser()
    #TestBaseProjectManager().run()
    #CrossSectionnal().run()

    # Verify API connection first
    if verify_ercot_api_connection():
        print("\n=== Testing Data Retrieval ===")
        service = ErcotPublicApiService()
        prices = service.get_physical_prices('2024-12-01', '2024-12-05', 'HB_HOUSTON')
        
        if prices and 'data' in prices and prices['data']:
            print("Sample data retrieved:")
            for record in prices['data'][:3]:  # Show first 3 records
                print(f"  - {record.get('deliveryDate', 'N/A')}: {record}")
        else:
            print("No data retrieved or empty response")
    else:
        print("\n⚠️  Skipping data retrieval due to connection issues")
    