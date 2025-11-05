#!/usr/bin/env python3

import sys
import os
import json
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.application.services.misbuffet.web.powerbuffet.powerbuffet import PowerBuffetService
    
    print("Testing PowerBuffet service...")
    
    # Test service initialization
    service = PowerBuffetService()
    print("✅ PowerBuffet service initialized successfully")
    
    # Test database discovery
    databases = service.get_available_databases()
    print(f"✅ Found {len(databases)} databases")
    
    if databases:
        first_db = databases[0]
        print(f"Testing tables for: {first_db['name']}")
        
        # Test table discovery
        tables = service.get_database_tables(first_db['connection_string'])
        print(f"✅ Found {len(tables)} tables")
        
        # Test JSON serialization
        try:
            json_str = json.dumps({'databases': databases, 'tables': tables})
            print("✅ JSON serialization successful!")
            print(f"JSON length: {len(json_str)} characters")
            
            # Test specific table preview if available
            if tables:
                first_table = tables[0]['name']
                preview = service.get_table_preview(first_db['connection_string'], first_table)
                json_preview = json.dumps(preview)
                print(f"✅ Table preview JSON serialization successful! Length: {len(json_preview)}")
                
        except Exception as e:
            print(f"❌ JSON serialization failed: {e}")
            return False
    else:
        print("No databases found")
    
    print("✅ All PowerBuffet tests passed!")
    return True
    
except Exception as e:
    print(f"❌ PowerBuffet test failed: {e}")
    import traceback
    traceback.print_exc()
    return False

if __name__ == "__main__":
    success = main() if 'main' in locals() else True
    sys.exit(0 if success else 1)