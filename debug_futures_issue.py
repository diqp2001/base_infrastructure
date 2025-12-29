#!/usr/bin/env python3
"""
Debug script to investigate why ES futures historical data is failing
while AAPL stock historical data works.
"""

import logging
import sys
import os
import time

# Add src to path
sys.path.append('/home/runner/work/base_infrastructure/base_infrastructure/src')

from application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
from application.services.misbuffet.brokers.ibkr.contract_resolver import ContractResolver

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_futures_contract_resolution():
    """Debug the futures contract resolution process."""
    logger.info("=" * 60)
    logger.info("DEBUGGING FUTURES CONTRACT RESOLUTION ISSUE")
    logger.info("=" * 60)
    
    # Create broker instance
    config = {
        'host': '127.0.0.1',
        'port': 7497,  # Paper trading
        'client_id': 1,
        'paper_trading': True,
        'timeout': 60,
        'account_id': 'DEFAULT',
        'enable_logging': True,
    }
    
    broker = InteractiveBrokersBroker(config)
    
    try:
        # Connect to IB
        logger.info("Connecting to Interactive Brokers...")
        if not broker.connect():
            logger.error("Failed to connect to IB")
            return
        
        logger.info("Connected successfully")
        
        # Test 1: Create ES futures contract 
        logger.info("\n" + "=" * 40)
        logger.info("TEST 1: Creating ES futures contract")
        logger.info("=" * 40)
        
        es_contract = broker.create_stock_contract("ES", "FUT", "CME")
        es_contract.currency = "USD"
        
        logger.info(f"Created ES contract: symbol={es_contract.symbol}, secType={es_contract.secType}, exchange={es_contract.exchange}")
        
        # Test 2: Contract resolution process
        logger.info("\n" + "=" * 40)
        logger.info("TEST 2: Contract resolution process")
        logger.info("=" * 40)
        
        if not hasattr(broker, 'contract_resolver'):
            broker.contract_resolver = ContractResolver(broker.ib_connection)
        
        # Test resolve_front_future step by step
        logger.info("Attempting to resolve front month ES future...")
        
        # Debug the resolver with detailed logging
        resolver = broker.contract_resolver
        
        # Manually trace through resolve_front_future logic
        symbol = "ES"
        exchange = "CME"
        
        # Create base contract
        from ibapi.contract import Contract
        base_contract = Contract()
        base_contract.symbol = symbol
        base_contract.secType = "FUT"
        base_contract.exchange = exchange
        base_contract.currency = "USD"
        
        logger.info(f"Base contract created: {base_contract.symbol}, {base_contract.secType}, {base_contract.exchange}")
        
        # Request contract details manually with debug
        req_id = abs(hash(f"debug_{symbol}_{time.time()}")) % 10000
        resolver.ib.contract_details.pop(req_id, None)
        
        logger.info(f"Requesting contract details with req_id: {req_id}")
        resolver.ib.request_contract_details(req_id, base_contract)
        
        # Wait with detailed progress logging
        timeout = 15
        waited = 0.0
        
        while waited < timeout:
            time.sleep(0.5)
            waited += 0.5
            
            if req_id in resolver.ib.contract_details:
                details_list = resolver.ib.contract_details[req_id]
                logger.info(f"Contract details received! Found {len(details_list) if details_list else 0} contracts")
                break
            else:
                logger.debug(f"Waiting for contract details... {waited:.1f}s")
        
        # Analyze what we got
        details_list = resolver.ib.contract_details.get(req_id, [])
        
        if not details_list:
            logger.error("❌ No contract details received - this is the root cause!")
            logger.error("This means IB rejected the contract details request for ES futures")
            return
        
        logger.info(f"✅ Received {len(details_list)} contract details")
        
        # Test contract parsing
        logger.info("\n" + "=" * 40)
        logger.info("TEST 3: Contract details analysis")
        logger.info("=" * 40)
        
        valid_contracts = []
        
        for i, d in enumerate(details_list):
            logger.info(f"Contract {i+1}: {d}")
            local_symbol = d.get("local_symbol", "")
            expiry = resolver.parse_expiry_from_local_symbol(local_symbol)
            
            logger.info(f"  Local Symbol: {local_symbol}")
            logger.info(f"  Parsed Expiry: {expiry}")
            
            if expiry:
                valid_contracts.append((expiry, d))
                logger.info(f"  ✅ Valid contract added")
            else:
                logger.warning(f"  ⚠️  Failed to parse expiry from {local_symbol}")
        
        if not valid_contracts:
            logger.error("❌ No valid expiries found - this is the secondary issue!")
            return
        
        # Test front month selection
        logger.info("\n" + "=" * 40)
        logger.info("TEST 4: Front month selection")
        logger.info("=" * 40)
        
        logger.info(f"Valid contracts: {len(valid_contracts)}")
        for expiry, contract in valid_contracts:
            logger.info(f"  {expiry}: {contract.get('local_symbol', 'N/A')}")
        
        front_contract_tuple = min(valid_contracts, key=lambda x: x[0])
        front_expiry, front_contract_dict = front_contract_tuple
        
        logger.info(f"✅ Selected front month: {front_expiry} -> {front_contract_dict.get('local_symbol')}")
        
        # Test historical data request
        logger.info("\n" + "=" * 40)
        logger.info("TEST 5: Historical data request")
        logger.info("=" * 40)
        
        # Now test the actual historical data call
        resolved_contract = resolver.resolve_front_future("ES", "CME")
        
        if not resolved_contract:
            logger.error("❌ resolve_front_future returned None!")
            return
        
        logger.info(f"✅ Resolved contract: {resolved_contract.localSymbol} (conId: {resolved_contract.conId})")
        
        # Test historical data call
        logger.info("Testing historical data request...")
        
        hist_data = broker.get_historical_data(
            contract=resolved_contract,
            duration_str="5 D",
            bar_size_setting="1 day",
            what_to_show="TRADES",
            timeout=15
        )
        
        if hist_data:
            logger.info(f"✅ Historical data success: {len(hist_data)} bars received")
            logger.info(f"Sample bar: {hist_data[0] if hist_data else 'None'}")
        else:
            logger.error("❌ Historical data request failed - no data received")
        
    except Exception as e:
        logger.error(f"Debug failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            broker.disconnect()
            logger.info("Disconnected from IB")
        except:
            pass

if __name__ == "__main__":
    debug_futures_contract_resolution()