# Repository IBKR: _create_or_get Pattern Documentation

## Overview
IBKR repositories extend the `_create_or_get` pattern to integrate with Interactive Brokers API, combining real-time market data retrieval with local entity persistence. These repositories handle contract validation, market data fetching, and entity creation while maintaining compatibility with the local repository pattern.

## Core Architecture

### IBKR Repository Hierarchy
```
BaseIBKRRepository (IBKR-specific base)
├── BaseIBKRFactorRepository (Factor-specific IBKR base)
│   ├── IBKRIndexFactorRepository
│   ├── IBKRCompanyShareFactorRepository
│   ├── IBKRIndexFutureFactorRepository
│   └── ... (other IBKR factor repositories)
├── IBKRFinancialAssetRepository (Asset-specific IBKR base)
│   ├── IBKRIndexRepository
│   ├── IBKRCompanyShareRepository
│   ├── IBKRIndexFutureRepository
│   └── ... (other IBKR asset repositories)
└── IBKRUtilityRepository
    ├── IBKRFactorValueRepository
    └── ... (other IBKR utility repositories)
```

### Base IBKR Repository Pattern
```python
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository

class BaseIBKRRepository(BaseLocalRepository):
    """Base repository with IBKR integration capabilities."""
    
    def __init__(self, session, ibkr_client=None, factory=None):
        super().__init__(session)
        self.ibkr_client = ibkr_client
        self.factory = factory
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @property
    def is_ibkr_connected(self) -> bool:
        """Check if IBKR client is connected."""
        return (self.ibkr_client is not None and 
                hasattr(self.ibkr_client, 'ib_connection') and
                self.ibkr_client.ib_connection.connected_flag)
    
    @abstractmethod
    def _create_or_get(self, symbol: str, **kwargs) -> Optional[Any]:
        """Create or get entity with IBKR integration."""
        pass
        
    @abstractmethod
    def _fetch_contract_ibkr(self, symbol: str, **kwargs) -> Optional[Dict]:
        """Fetch contract details from IBKR API."""
        pass
        
    def _fallback_to_local(self, symbol: str, **kwargs) -> Optional[Any]:
        """Fallback to local repository when IBKR unavailable."""
        if hasattr(self, 'local_repository'):
            return self.local_repository._create_or_get(symbol, **kwargs)
        return None
```

## IBKR _create_or_get Pattern Analysis

### Example: IBKRIndexFactorRepository._create_or_get
**File**: `/src/infrastructure/repositories/ibkr_repo/factor/finance/financial_assets/ibkr_index_factor_repository.py`

```python
class IBKRIndexFactorRepository(BaseIBKRFactorRepository, IndexFactorPort):
    """IBKR repository for IndexFactor entities with real-time data integration."""
    
    def __init__(self, session, ibkr_client=None, factory=None):
        super().__init__(session, ibkr_client, factory)
        self.mapper = IBKRIndexFactorMapper()
    
    def _create_or_get(self, symbol: str, group: str = "market_data", 
                      subgroup: str = "real_time", **kwargs) -> Optional[IndexFactor]:
        """
        Create or get IndexFactor with IBKR contract validation.
        
        Args:
            symbol: Factor name/symbol
            group: Factor group classification  
            subgroup: Factor subgroup classification
            **kwargs: Additional IBKR-specific parameters
            
        Returns:
            IndexFactor: Created or existing factor with IBKR data
        """
        try:
            # Step 1: Check if factor already exists locally
            existing_factor = self.get_by_name(symbol)
            if existing_factor and existing_factor.source == 'ibkr':
                self.logger.debug(f"IBKR IndexFactor {symbol} already exists")
                return existing_factor
            
            # Step 2: Validate IBKR connection
            if not self.is_ibkr_connected:
                self.logger.warning("IBKR not connected, falling back to local creation")
                return self._create_local_factor(symbol, group, subgroup, **kwargs)
            
            # Step 3: Fetch contract details from IBKR
            contract_data = self._fetch_contract_ibkr(symbol, **kwargs)
            if not contract_data:
                self.logger.warning(f"Could not fetch IBKR contract for {symbol}")
                return self._create_local_factor(symbol, group, subgroup, **kwargs)
            
            # Step 4: Create IndexFactor with IBKR-enhanced data
            self.logger.info(f"Creating IBKR IndexFactor: {symbol}")
            
            new_factor = IndexFactor(
                name=symbol,
                group=group,
                subgroup=subgroup,
                frequency=kwargs.get('frequency', 'real_time'),
                data_type=kwargs.get('data_type', 'market_data'),
                source='ibkr',
                definition=f"IBKR market data factor for {contract_data.get('longName', symbol)}",
                # IBKR-specific metadata
                contract_id=contract_data.get('conId'),
                exchange=contract_data.get('exchange'),
                currency=contract_data.get('currency'),
                market_data_type=contract_data.get('secType')
            )
            
            # Step 5: Persist with IBKR metadata
            factor_model = self.mapper.to_orm(new_factor)
            
            # Add IBKR-specific model fields
            factor_model.ibkr_contract_id = contract_data.get('conId')
            factor_model.ibkr_symbol = contract_data.get('symbol')
            factor_model.ibkr_exchange = contract_data.get('exchange')
            
            self.session.add(factor_model)
            self.session.commit()
            
            # Step 6: Return domain entity with database ID
            persisted_factor = self.mapper.to_domain(factor_model)
            
            self.logger.info(f"Successfully created IBKR IndexFactor {symbol} with ID {persisted_factor.factor_id}")
            return persisted_factor
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error creating IBKR IndexFactor {symbol}: {e}")
            # Fallback to local creation
            return self._create_local_factor(symbol, group, subgroup, **kwargs)
    
    def _fetch_contract_ibkr(self, symbol: str, **kwargs) -> Optional[Dict]:
        """
        Fetch contract details from IBKR API.
        
        Args:
            symbol: Security symbol
            **kwargs: Additional contract parameters
            
        Returns:
            Dict with contract details or None if not found
        """
        try:
            if not self.is_ibkr_connected:
                return None
            
            # Create contract specification
            contract_spec = {
                'symbol': symbol,
                'secType': kwargs.get('sec_type', 'IND'),  # Index
                'exchange': kwargs.get('exchange', 'CBOE'),
                'currency': kwargs.get('currency', 'USD')
            }
            
            # Request contract details from IBKR
            contract_details = self.ibkr_client.get_contract_details(contract_spec)
            
            if contract_details and len(contract_details) > 0:
                # Extract relevant contract information
                detail = contract_details[0]
                return {
                    'conId': detail.contract.conId,
                    'symbol': detail.contract.symbol,
                    'longName': detail.longName,
                    'exchange': detail.contract.exchange,
                    'currency': detail.contract.currency,
                    'secType': detail.contract.secType,
                    'marketName': detail.marketName,
                    'minTick': detail.minTick,
                    'orderTypes': detail.orderTypes,
                    'validExchanges': detail.validExchanges
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching IBKR contract for {symbol}: {e}")
            return None
    
    def _create_local_factor(self, symbol: str, group: str, subgroup: str, **kwargs) -> Optional[IndexFactor]:
        """Fallback to local factor creation when IBKR unavailable."""
        try:
            local_factor = IndexFactor(
                name=symbol,
                group=group,
                subgroup=subgroup,
                frequency=kwargs.get('frequency', 'daily'),
                data_type=kwargs.get('data_type', 'calculated'),
                source='local',
                definition=f"Local factor for {symbol} (IBKR unavailable)"
            )
            
            factor_model = self.mapper.to_orm(local_factor)
            self.session.add(factor_model)
            self.session.commit()
            
            return self.mapper.to_domain(factor_model)
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error creating local fallback factor {symbol}: {e}")
            return None
```

### Market Data Integration Pattern

```python
def _create_or_get_with_market_data(self, symbol: str, what_to_show: str = "TRADES",
                                   duration_str: str = "6 M", bar_size_setting: str = "1 day",
                                   **kwargs) -> Optional[IndexFactor]:
    """
    Create or get factor with immediate market data retrieval.
    
    Args:
        symbol: Factor symbol
        what_to_show: Type of data ("TRADES", "MIDPOINT", "BID", "ASK")
        duration_str: Historical data duration ("1 D", "1 W", "1 M", "6 M", "1 Y")
        bar_size_setting: Bar size ("1 sec", "5 mins", "1 hour", "1 day")
        **kwargs: Additional parameters
    """
    try:
        # Step 1: Create or get factor entity
        factor = self._create_or_get(symbol, **kwargs)
        if not factor:
            return None
        
        # Step 2: Fetch historical market data if IBKR connected
        if self.is_ibkr_connected:
            market_data = self._fetch_historical_data(
                symbol, what_to_show, duration_str, bar_size_setting
            )
            
            if market_data:
                # Step 3: Store market data as factor values
                self._store_market_data_as_factor_values(factor, market_data)
        
        return factor
        
    except Exception as e:
        self.logger.error(f"Error creating factor with market data {symbol}: {e}")
        return None

def _fetch_historical_data(self, symbol: str, what_to_show: str, 
                          duration_str: str, bar_size_setting: str) -> Optional[List[Dict]]:
    """Fetch historical market data from IBKR."""
    try:
        if not self.is_ibkr_connected:
            return None
        
        # Create contract for data request
        contract = {
            'symbol': symbol,
            'secType': 'IND',
            'exchange': 'CBOE',
            'currency': 'USD'
        }
        
        # Request historical data
        bars = self.ibkr_client.get_historical_bars(
            contract=contract,
            endDateTime='',  # Current time
            durationStr=duration_str,
            barSizeSetting=bar_size_setting,
            whatToShow=what_to_show,
            useRTH=1,  # Regular trading hours
            formatDate=1
        )
        
        if bars:
            return [
                {
                    'date': bar.date,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume,
                    'average': bar.average,
                    'barCount': bar.barCount
                }
                for bar in bars
            ]
        
        return None
        
    except Exception as e:
        self.logger.error(f"Error fetching historical data for {symbol}: {e}")
        return None

def _store_market_data_as_factor_values(self, factor: IndexFactor, market_data: List[Dict]):
    """Store market data as factor values in database."""
    try:
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        from datetime import datetime
        from decimal import Decimal
        
        factor_values = []
        
        for bar_data in market_data:
            # Create factor values for each OHLCV component
            ohlcv_data = {
                'open': bar_data['open'],
                'high': bar_data['high'], 
                'low': bar_data['low'],
                'close': bar_data['close'],
                'volume': bar_data['volume']
            }
            
            bar_date = datetime.strptime(bar_data['date'], '%Y%m%d').date()
            
            for component, value in ohlcv_data.items():
                if value is not None:
                    factor_value = FactorValueModel(
                        factor_id=factor.factor_id,
                        entity_id=1,  # Default entity for index factors
                        date=bar_date,
                        value=Decimal(str(value)),
                        source='ibkr',
                        quality_score=0.95  # High quality for IBKR data
                    )
                    factor_values.append(factor_value)
        
        # Bulk insert factor values
        if factor_values:
            self.session.add_all(factor_values)
            self.session.commit()
            self.logger.info(f"Stored {len(factor_values)} factor values for {factor.name}")
        
    except Exception as e:
        self.session.rollback()
        self.logger.error(f"Error storing market data as factor values: {e}")
```

## Complex IBKR Integration Patterns

### 1. Option Contract Handling
```python
def _create_or_get_option(self, symbol: str, strike_price: float, 
                         expiry: str, option_type: str, **kwargs) -> Optional[IndexFutureOption]:
    """
    Create or get option contract with IBKR validation.
    
    Args:
        symbol: Underlying symbol
        strike_price: Strike price
        expiry: Expiry date (YYYYMMDD format)
        option_type: 'C' for call, 'P' for put
    """
    try:
        # Step 1: Check existing option
        composite_key = f"{symbol}_{strike_price}_{expiry}_{option_type}"
        existing_option = self.get_by_composite_key(symbol, strike_price, expiry, option_type)
        if existing_option:
            return existing_option
        
        # Step 2: Validate with IBKR
        if self.is_ibkr_connected:
            contract_data = self._fetch_option_contract_ibkr(
                symbol, strike_price, expiry, option_type, **kwargs
            )
            
            if not contract_data:
                self.logger.warning(f"IBKR option contract not found: {composite_key}")
                return None
        else:
            self.logger.warning("IBKR not connected, creating option without validation")
            contract_data = {}
        
        # Step 3: Create option entity
        new_option = IndexFutureOption(
            symbol=symbol,
            strike_price=strike_price,
            expiry_date=datetime.strptime(expiry, '%Y%m%d').date(),
            option_type=option_type,
            # IBKR contract data
            contract_id=contract_data.get('conId'),
            underlying_contract_id=contract_data.get('underlyingConId'),
            multiplier=contract_data.get('multiplier', 100),
            exchange=contract_data.get('exchange', 'CBOE'),
            currency=contract_data.get('currency', 'USD'),
            # Option Greeks and pricing (if available)
            delta=contract_data.get('delta'),
            gamma=contract_data.get('gamma'),
            theta=contract_data.get('theta'),
            vega=contract_data.get('vega'),
            implied_volatility=contract_data.get('impliedVol'),
            option_price=contract_data.get('optionPrice')
        )
        
        # Step 4: Persist
        option_model = self.mapper.to_orm(new_option)
        self.session.add(option_model)
        self.session.commit()
        
        return self.mapper.to_domain(option_model)
        
    except Exception as e:
        self.session.rollback()
        self.logger.error(f"Error creating IBKR option {composite_key}: {e}")
        return None

def _fetch_option_contract_ibkr(self, symbol: str, strike: float, 
                               expiry: str, option_type: str, **kwargs) -> Optional[Dict]:
    """Fetch option contract details from IBKR."""
    try:
        if not self.is_ibkr_connected:
            return None
        
        # Create option contract specification
        contract_spec = {
            'symbol': symbol,
            'secType': 'OPT',
            'exchange': kwargs.get('exchange', 'CBOE'),
            'currency': kwargs.get('currency', 'USD'),
            'strike': strike,
            'right': option_type,  # 'C' or 'P'
            'lastTradeDateOrContractMonth': expiry
        }
        
        # Get contract details
        contract_details = self.ibkr_client.get_contract_details(contract_spec)
        
        if contract_details and len(contract_details) > 0:
            detail = contract_details[0]
            contract_data = {
                'conId': detail.contract.conId,
                'symbol': detail.contract.symbol,
                'strike': detail.contract.strike,
                'right': detail.contract.right,
                'expiry': detail.contract.lastTradeDateOrContractMonth,
                'multiplier': detail.contract.multiplier,
                'exchange': detail.contract.exchange,
                'currency': detail.contract.currency,
                'underlyingConId': detail.underConId,
                'minTick': detail.minTick
            }
            
            # Try to get real-time option data (Greeks, IV, price)
            market_data = self._get_option_market_data(detail.contract)
            if market_data:
                contract_data.update(market_data)
            
            return contract_data
        
        return None
        
    except Exception as e:
        self.logger.error(f"Error fetching option contract from IBKR: {e}")
        return None

def _get_option_market_data(self, contract) -> Optional[Dict]:
    """Get real-time option market data (Greeks, IV, price)."""
    try:
        # Request market data for option
        ticker = self.ibkr_client.reqMktData(contract, '106,100,101,102,103,104,105', False, False)
        
        # Wait for data (with timeout)
        import time
        timeout = 5  # 5 second timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if hasattr(ticker, 'modelGreeks') and ticker.modelGreeks:
                return {
                    'delta': ticker.modelGreeks.delta,
                    'gamma': ticker.modelGreeks.gamma,
                    'theta': ticker.modelGreeks.theta,
                    'vega': ticker.modelGreeks.vega,
                    'impliedVol': ticker.impliedVolatility,
                    'optionPrice': ticker.marketPrice(),
                    'bid': ticker.bid,
                    'ask': ticker.ask,
                    'last': ticker.last
                }
            time.sleep(0.1)
        
        return None
        
    except Exception as e:
        self.logger.error(f"Error getting option market data: {e}")
        return None
```

### 2. Batch Processing with IBKR
```python
def get_or_create_batch_optimized(self, entities_data: List[Dict], 
                                 what_to_show: str = "TRADES",
                                 duration_str: str = "6 M", 
                                 bar_size_setting: str = "1 day") -> List[Any]:
    """
    Optimized batch processing with IBKR bulk data retrieval.
    
    Args:
        entities_data: List of entity specifications
        what_to_show: Market data type
        duration_str: Historical data duration
        bar_size_setting: Bar size for historical data
    """
    try:
        results = []
        
        if not self.is_ibkr_connected:
            # Fallback to local batch processing
            return self._batch_create_local(entities_data)
        
        # Step 1: Separate existing vs new entities
        existing_entities, new_entity_specs = self._separate_existing_new(entities_data)
        results.extend(existing_entities)
        
        if not new_entity_specs:
            return results
        
        # Step 2: Batch validate contracts with IBKR
        valid_contracts = self._batch_validate_contracts(new_entity_specs)
        
        # Step 3: Batch create entities
        new_entities = self._batch_create_with_contracts(valid_contracts)
        results.extend(new_entities)
        
        # Step 4: Batch fetch historical data if requested
        if duration_str and bar_size_setting:
            self._batch_fetch_historical_data(
                new_entities, what_to_show, duration_str, bar_size_setting
            )
        
        return results
        
    except Exception as e:
        self.logger.error(f"Error in IBKR batch processing: {e}")
        return []

def _batch_validate_contracts(self, entity_specs: List[Dict]) -> List[Dict]:
    """Validate multiple contracts with IBKR in batch."""
    valid_contracts = []
    
    try:
        # Create contract specifications
        contract_specs = []
        for spec in entity_specs:
            contract_spec = {
                'symbol': spec['symbol'],
                'secType': spec.get('sec_type', 'IND'),
                'exchange': spec.get('exchange', 'CBOE'),
                'currency': spec.get('currency', 'USD')
            }
            contract_specs.append((spec, contract_spec))
        
        # Batch request contract details (IBKR allows multiple simultaneous requests)
        for original_spec, contract_spec in contract_specs:
            try:
                contract_details = self.ibkr_client.get_contract_details(contract_spec)
                if contract_details and len(contract_details) > 0:
                    detail = contract_details[0]
                    valid_contract = {
                        **original_spec,
                        'ibkr_contract_data': {
                            'conId': detail.contract.conId,
                            'longName': detail.longName,
                            'exchange': detail.contract.exchange,
                            'currency': detail.contract.currency
                        }
                    }
                    valid_contracts.append(valid_contract)
                else:
                    self.logger.warning(f"Invalid contract: {original_spec['symbol']}")
                    
            except Exception as e:
                self.logger.error(f"Error validating contract {contract_spec['symbol']}: {e}")
        
        return valid_contracts
        
    except Exception as e:
        self.logger.error(f"Error in batch contract validation: {e}")
        return []

def _batch_fetch_historical_data(self, entities: List[Any], what_to_show: str,
                                duration_str: str, bar_size_setting: str):
    """Fetch historical data for multiple entities in batch."""
    try:
        if not self.is_ibkr_connected:
            return
        
        # Process entities in smaller batches to avoid IBKR rate limits
        batch_size = 10
        for i in range(0, len(entities), batch_size):
            batch_entities = entities[i:i + batch_size]
            
            for entity in batch_entities:
                try:
                    # Fetch data for each entity
                    market_data = self._fetch_historical_data(
                        entity.symbol, what_to_show, duration_str, bar_size_setting
                    )
                    
                    if market_data:
                        self._store_market_data_as_factor_values(entity, market_data)
                    
                    # Small delay to respect IBKR rate limits
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"Error fetching data for {entity.symbol}: {e}")
            
            # Longer delay between batches
            time.sleep(1.0)
        
    except Exception as e:
        self.logger.error(f"Error in batch historical data fetch: {e}")
```

## Error Handling and Resilience

### Connection Management
```python
class IBKRConnectionManager:
    """Manages IBKR connection state and recovery."""
    
    def __init__(self, repository):
        self.repository = repository
        self.connection_retry_count = 0
        self.max_retries = 3
        
    def execute_with_retry(self, operation_func, *args, **kwargs):
        """Execute IBKR operation with automatic retry on connection issues."""
        
        for attempt in range(self.max_retries + 1):
            try:
                if not self.repository.is_ibkr_connected:
                    if attempt < self.max_retries:
                        self._attempt_reconnection()
                        continue
                    else:
                        raise ConnectionError("IBKR connection unavailable after retries")
                
                result = operation_func(*args, **kwargs)
                self.connection_retry_count = 0  # Reset on success
                return result
                
            except ConnectionError as e:
                self.repository.logger.warning(f"IBKR connection error (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                if "connection" in str(e).lower():
                    self.repository.logger.warning(f"Connection-related error: {e}")
                    if attempt < self.max_retries:
                        continue
                raise
    
    def _attempt_reconnection(self):
        """Attempt to reconnect to IBKR."""
        try:
            if hasattr(self.repository.ibkr_client, 'reconnect'):
                self.repository.ibkr_client.reconnect()
                time.sleep(2)  # Allow time for connection to establish
        except Exception as e:
            self.repository.logger.error(f"Failed to reconnect to IBKR: {e}")

# Usage in repository methods
def _create_or_get_with_resilience(self, symbol: str, **kwargs):
    """Create or get with connection resilience."""
    connection_manager = IBKRConnectionManager(self)
    
    try:
        return connection_manager.execute_with_retry(
            self._create_or_get_internal, symbol, **kwargs
        )
    except ConnectionError:
        self.logger.warning(f"IBKR unavailable for {symbol}, falling back to local")
        return self._create_local_factor(symbol, **kwargs)
    except Exception as e:
        self.logger.error(f"Error creating entity {symbol}: {e}")
        return None
```

### Data Quality Validation
```python
def _validate_ibkr_data(self, contract_data: Dict) -> bool:
    """Validate quality and completeness of IBKR data."""
    
    quality_checks = [
        ('conId', lambda x: x and x > 0),
        ('symbol', lambda x: x and len(x.strip()) > 0),
        ('exchange', lambda x: x and len(x.strip()) > 0),
        ('currency', lambda x: x and len(x) == 3)  # ISO currency code
    ]
    
    quality_score = 1.0
    issues = []
    
    for field, validator in quality_checks:
        value = contract_data.get(field)
        if not validator(value):
            issues.append(f"Invalid {field}: {value}")
            quality_score -= 0.2
    
    # Check for suspicious data
    if 'longName' in contract_data and len(contract_data['longName']) < 3:
        issues.append("Suspiciously short longName")
        quality_score -= 0.1
    
    if quality_score < 0.7:
        self.logger.warning(f"Low quality IBKR data: {issues}")
        return False
    
    return True

def _enrich_entity_with_ibkr_data(self, entity: Any, contract_data: Dict) -> Any:
    """Enrich entity with validated IBKR data."""
    
    if not self._validate_ibkr_data(contract_data):
        return entity
    
    # Add IBKR metadata
    entity.ibkr_contract_id = contract_data.get('conId')
    entity.ibkr_symbol = contract_data.get('symbol')
    entity.exchange = contract_data.get('exchange')
    entity.currency = contract_data.get('currency')
    entity.full_name = contract_data.get('longName')
    
    # Add trading information
    entity.min_tick = contract_data.get('minTick')
    entity.multiplier = contract_data.get('multiplier')
    entity.trading_class = contract_data.get('tradingClass')
    
    # Mark as IBKR-validated
    entity.data_source = 'ibkr'
    entity.validation_timestamp = datetime.utcnow()
    
    return entity
```

## Performance Optimization

### Request Batching
```python
class IBKRBatchProcessor:
    """Batches and optimizes IBKR API requests."""
    
    def __init__(self, ibkr_client, batch_size: int = 50, rate_limit: float = 0.1):
        self.ibkr_client = ibkr_client
        self.batch_size = batch_size
        self.rate_limit = rate_limit  # Seconds between requests
        self.request_times = []
    
    def batch_contract_details(self, contract_specs: List[Dict]) -> Dict[str, Dict]:
        """Get contract details for multiple contracts with rate limiting."""
        
        results = {}
        
        for i in range(0, len(contract_specs), self.batch_size):
            batch = contract_specs[i:i + self.batch_size]
            
            # Process batch
            batch_results = self._process_contract_batch(batch)
            results.update(batch_results)
            
            # Rate limiting
            if i + self.batch_size < len(contract_specs):
                time.sleep(self.rate_limit * len(batch))
        
        return results
    
    def _process_contract_batch(self, batch: List[Dict]) -> Dict[str, Dict]:
        """Process a single batch of contract requests."""
        
        batch_results = {}
        
        for contract_spec in batch:
            try:
                symbol = contract_spec['symbol']
                details = self.ibkr_client.get_contract_details(contract_spec)
                
                if details and len(details) > 0:
                    batch_results[symbol] = self._extract_contract_info(details[0])
                
                # Small delay between individual requests
                time.sleep(self.rate_limit)
                
            except Exception as e:
                logger.error(f"Error processing contract {contract_spec['symbol']}: {e}")
        
        return batch_results
    
    def _extract_contract_info(self, contract_detail) -> Dict:
        """Extract relevant information from contract detail."""
        return {
            'conId': contract_detail.contract.conId,
            'symbol': contract_detail.contract.symbol,
            'longName': contract_detail.longName,
            'exchange': contract_detail.contract.exchange,
            'currency': contract_detail.contract.currency,
            'secType': contract_detail.contract.secType,
            'minTick': contract_detail.minTick,
            'marketName': contract_detail.marketName
        }
```

### Caching Strategy
```python
class IBKRCachedRepository(BaseIBKRRepository):
    """IBKR repository with intelligent caching."""
    
    def __init__(self, session, ibkr_client=None, factory=None):
        super().__init__(session, ibkr_client, factory)
        self.contract_cache = {}
        self.cache_ttl = 3600  # 1 hour cache TTL
    
    def _get_cached_contract(self, cache_key: str) -> Optional[Dict]:
        """Get contract from cache if valid."""
        
        if cache_key in self.contract_cache:
            cached_data, timestamp = self.contract_cache[cache_key]
            
            if time.time() - timestamp < self.cache_ttl:
                self.logger.debug(f"Cache hit for contract {cache_key}")
                return cached_data
            else:
                # Cache expired
                del self.contract_cache[cache_key]
        
        return None
    
    def _cache_contract(self, cache_key: str, contract_data: Dict):
        """Cache contract data with timestamp."""
        self.contract_cache[cache_key] = (contract_data, time.time())
    
    def _fetch_contract_ibkr_cached(self, symbol: str, **kwargs) -> Optional[Dict]:
        """Fetch contract with caching."""
        
        # Create cache key
        cache_key = f"{symbol}_{kwargs.get('secType', 'IND')}_{kwargs.get('exchange', 'CBOE')}"
        
        # Check cache first
        cached_data = self._get_cached_contract(cache_key)
        if cached_data:
            return cached_data
        
        # Fetch from IBKR
        contract_data = self._fetch_contract_ibkr(symbol, **kwargs)
        
        # Cache the result
        if contract_data:
            self._cache_contract(cache_key, contract_data)
        
        return contract_data
```

## Testing IBKR Repositories

### Mock IBKR Client
```python
class MockIBKRClient:
    """Mock IBKR client for testing."""
    
    def __init__(self):
        self.connected = True
        self.contract_responses = {}
        self.market_data_responses = {}
    
    def add_contract_response(self, symbol: str, contract_data: Dict):
        """Add mock contract response."""
        self.contract_responses[symbol] = contract_data
    
    def get_contract_details(self, contract_spec: Dict) -> List:
        """Mock contract details response."""
        symbol = contract_spec.get('symbol')
        
        if symbol in self.contract_responses:
            # Create mock contract detail object
            mock_detail = type('MockContractDetail', (), {})()
            mock_detail.contract = type('MockContract', (), {})()
            
            contract_data = self.contract_responses[symbol]
            mock_detail.contract.conId = contract_data.get('conId', 12345)
            mock_detail.contract.symbol = symbol
            mock_detail.longName = contract_data.get('longName', f'{symbol} Index')
            mock_detail.contract.exchange = contract_data.get('exchange', 'CBOE')
            mock_detail.contract.currency = contract_data.get('currency', 'USD')
            
            return [mock_detail]
        
        return []
    
    @property
    def ib_connection(self):
        """Mock connection object."""
        return type('MockConnection', (), {'connected_flag': self.connected})()

# Test usage
class TestIBKRRepository(unittest.TestCase):
    def setUp(self):
        self.session = create_test_session()
        self.mock_ibkr = MockIBKRClient()
        self.repository = IBKRIndexFactorRepository(self.session, self.mock_ibkr)
    
    def test_create_or_get_with_ibkr_data(self):
        """Test entity creation with IBKR contract data."""
        
        # Setup mock response
        self.mock_ibkr.add_contract_response('SPX', {
            'conId': 416904,
            'longName': 'S&P 500 Stock Index',
            'exchange': 'CBOE',
            'currency': 'USD'
        })
        
        # Test creation
        factor = self.repository._create_or_get('SPX')
        
        assert factor is not None
        assert factor.name == 'SPX'
        assert factor.source == 'ibkr'
        assert factor.ibkr_contract_id == 416904
    
    def test_fallback_when_ibkr_unavailable(self):
        """Test fallback to local creation when IBKR unavailable."""
        
        # Disconnect mock IBKR
        self.mock_ibkr.connected = False
        
        # Test creation
        factor = self.repository._create_or_get('TEST_INDEX')
        
        assert factor is not None
        assert factor.name == 'TEST_INDEX'
        assert factor.source == 'local'  # Should fallback to local
```

The IBKR repository pattern extends the local `_create_or_get` pattern with real-time market data integration, contract validation, and comprehensive error handling while maintaining compatibility with the local repository infrastructure.