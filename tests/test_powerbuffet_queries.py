#!/usr/bin/env python3
"""
Quick test of the new PowerBuffet sample queries
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.application.services.misbuffet.web.powerbuffet.powerbuffet import PowerBuffetService

def test_sample_queries():
    """Test the new sample queries"""
    service = PowerBuffetService()
    
    # Get sample queries
    sample_queries = service.get_sample_queries()
    print(f"Total sample queries available: {len(sample_queries)}")
    
    # Test a simple TOP 1000 query
    print("\n=== Testing AAPL Top 1000 Query ===")
    aapl_query = None
    for query in sample_queries:
        if query['id'] == 'aapl_top_1000':
            aapl_query = query
            break
    
    if aapl_query:
        print(f"Query: {aapl_query['title']}")
        print(f"SQL: {aapl_query['query']}")
        
        # Execute the query
        result = service.execute_sql_query(aapl_query['query'])
        if result['success']:
            print(f"✅ Query executed successfully!")
            print(f"   Rows returned: {result['row_count']}")
            print(f"   Columns: {result['column_names']}")
            print(f"   First 3 rows:")
            for i, row in enumerate(result['data'][:3]):
                print(f"     Row {i+1}: {row}")
        else:
            print(f"❌ Query failed: {result['error']}")
    
    # Test a JOIN query
    print("\n=== Testing Stock Correlation JOIN Query ===")
    join_query = None
    for query in sample_queries:
        if query['id'] == 'stock_correlation_join':
            join_query = query
            break
    
    if join_query:
        print(f"Query: {join_query['title']}")
        print(f"SQL: {join_query['query']}")
        
        # Execute the query
        result = service.execute_sql_query(join_query['query'])
        if result['success']:
            print(f"✅ JOIN query executed successfully!")
            print(f"   Rows returned: {result['row_count']}")
            print(f"   Columns: {result['column_names']}")
            if result['data']:
                print(f"   First row: {result['data'][0]}")
        else:
            print(f"❌ JOIN query failed: {result['error']}")
    
    # List all new queries
    print("\n=== New Queries Added ===")
    for query in sample_queries:
        if query['category'] in ['Data Exploration', 'JOIN Analysis']:
            print(f"- {query['title']} ({query['category']})")

if __name__ == "__main__":
    test_sample_queries()