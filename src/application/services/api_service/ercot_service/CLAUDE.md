# ERCOT Public API Service

## 📋 Overview

This service provides access to ERCOT's (Electric Reliability Council of Texas) public API for energy market data. Unlike the private ERCOT API, **no authentication is required** - all endpoints are publicly accessible.

The service focuses on two primary data types:
- **Day-Ahead Market (DAM)** settlement point prices
- **Real-Time Market (RTM)** settlement point prices (physical prices)

---

## 🏗️ Architecture

### Service Structure
```
src/application/services/ercot_service/
├── __init__.py                     # Package initialization
├── ercot_public_api_service.py    # Main service implementation
└── CLAUDE.md                      # This documentation
```

### Key Components
- **ErcotPublicApiService**: Main service class for API interactions
- **ERCOTRateLimit**: Configuration class for rate limiting
- **Settlement Points**: Predefined major hubs and load zones

---

## 🚀 Quick Start

### Basic Usage
```python
from src.application.services.ercot_service import ErcotPublicApiService
import datetime

# Initialize service (no authentication required)
service = ErcotPublicApiService()

# Get day-ahead prices for Houston Hub
start_date = '2024-12-01'
end_date = '2024-12-05'
dam_prices = service.get_day_ahead_prices(
    start_date=start_date,
    end_date=end_date,
    settlement_point='HB_HOUSTON'
)

# Get physical/real-time prices
rtm_prices = service.get_physical_prices(
    start_date=start_date,
    end_date=end_date,
    settlement_point='LZ_HOUSTON'
)

# Check API health
health = service.check_api_health()
print(f"API Status: {health['status']}")
```

### Advanced Usage - Fetch All Data with Pagination
```python
# Get all day-ahead prices for a month (handles pagination automatically)
all_dam_prices = service.get_day_ahead_prices_all(
    start_date='2024-12-01',
    end_date='2024-12-31',
    settlement_point='HB_HOUSTON'
)

print(f"Retrieved {len(all_dam_prices)} DAM price records")

# Get all physical prices with pagination limit
limited_rtm_prices = service.get_physical_prices_all(
    start_date='2024-12-01',
    end_date='2024-12-31',
    max_pages=5  # Limit to first 5 pages
)
```

---

## 🔗 API Endpoints

### Day-Ahead Market Prices
- **Endpoint**: `/np4-190-cd/dam_stlmnt_pnt_prices`
- **Method**: GET  
- **Authentication**: None required
- **Data**: Settlement point prices for day-ahead market

### Real-Time Market Prices  
- **Endpoint**: `/np6-788-cd/rtm_stlmnt_pnt_prices`
- **Method**: GET
- **Authentication**: None required
- **Data**: Settlement point prices for real-time market

### Base URL
```
https://api.ercot.com/api/public-reports
```

---

## 📊 Settlement Points

### Major Hubs
- **HB_HOUSTON**: Houston Hub
- **HB_NORTH**: North Hub
- **HB_SOUTH**: South Hub  
- **HB_WEST**: West Hub

### Major Load Zones
- **LZ_AEN**: AEP Texas Central
- **LZ_CPS**: CPS Energy
- **LZ_HOUSTON**: Houston Load Zone
- **LZ_NORTH**: North Load Zone
- **LZ_SOUTH**: South Load Zone
- **LZ_WEST**: West Load Zone

### Usage
```python
# Get settlement point information
points_info = service.get_settlement_points_info()
print("Available Hubs:", points_info['hubs'])
print("Available Load Zones:", points_info['load_zones'])
```

---

## ⚡ Rate Limiting & Performance

### Default Rate Limits
- **Requests per minute**: 100
- **Records per request**: 5,000 (maximum)
- **Request delay**: 0.6 seconds between requests

### Custom Rate Limiting
```python
from src.application.services.ercot_service.ercot_public_api_service import ERCOTRateLimit

# Custom rate limiting configuration
custom_rate_limit = ERCOTRateLimit(
    max_requests_per_minute=80,
    max_records_per_request=3000,
    request_delay=0.8
)

service = ErcotPublicApiService(rate_limit=custom_rate_limit)
```

---

## 📅 Data Availability

### Time Windows
- **Historical Data**: 90-day rolling window
- **Real-time Availability**: Data available within 1-2 hours
- **Time Zone**: All timestamps in Central Time (CT/CDT)
- **Intervals**: 15-minute pricing intervals

### Date Range Helper
```python
# Get recommended date ranges
date_info = service.get_date_range_info()
print(f"Recommended start: {date_info['recommended_start_date']}")
print(f"Recommended end: {date_info['recommended_end_date']}")
```

---

## 🔍 Response Format

### Typical Response Structure
```json
{
  "friendlyName": "Day-Ahead Settlement Point Prices",
  "data": [
    {
      "deliveryDate": "2024-12-01T00:00:00-06:00",
      "deliveryHour": "01",
      "deliveryInterval": "15",
      "settlementPoint": "HB_HOUSTON", 
      "settlementPointPrice": 45.67,
      "settlementPointType": "HUB"
    }
  ],
  "page": {
    "startRow": 1,
    "endRow": 5000,
    "totalRows": 15000,
    "pageNum": 1,
    "totalPages": 3
  }
}
```

### Key Fields
- **deliveryDate**: ISO 8601 timestamp in Central Time
- **deliveryHour**: Hour of delivery (01-24)
- **deliveryInterval**: 15-minute interval within hour
- **settlementPoint**: Settlement point identifier
- **settlementPointPrice**: Price in $/MWh
- **settlementPointType**: Type (HUB, LOAD_ZONE, etc.)

---

## 🛠️ Error Handling

### Built-in Error Handling
- **Rate Limiting**: Automatic request spacing
- **Network Errors**: Graceful handling with None returns
- **Invalid Parameters**: Validation and clear error messages
- **Timeout Protection**: Configurable timeout (default: 30s)

### Example Error Handling
```python
try:
    prices = service.get_day_ahead_prices('2024-12-01', '2024-12-05')
    if prices is None:
        print("Failed to retrieve data - check network connectivity")
    else:
        print(f"Retrieved {len(prices['data'])} records")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## 🧪 Testing & Validation

### Health Check
```python
# Check API connectivity and health
health_status = service.check_api_health()
print(f"API Health: {health_status['status']}")
print(f"Response Time: {health_status['timestamp']}")
```

### Data Validation
```python
# Validate settlement point exists
points = service.get_settlement_points_info()
if 'HB_HOUSTON' in points['all_major_points']:
    print("Settlement point is valid")
```

---

## 🔄 Integration with Project Architecture

### Domain-Driven Design Compliance
- **Domain Independence**: Service can be used by any domain layer
- **Interface Contracts**: Clear method signatures and return types
- **Error Boundaries**: Proper exception handling
- **Configuration**: Externalized rate limiting and timeout settings

### Usage in Application Layer
```python
# In application/managers or application/services
from src.application.services.ercot_service import ErcotPublicApiService

class EnergyMarketAnalyzer:
    def __init__(self):
        self.ercot_service = ErcotPublicApiService()
    
    def analyze_price_trends(self, start_date: str, end_date: str):
        dam_prices = self.ercot_service.get_day_ahead_prices_all(start_date, end_date)
        rtm_prices = self.ercot_service.get_physical_prices_all(start_date, end_date)
        
        # Perform analysis...
        return analysis_results
```

---

## 📚 Method Reference

### Core Methods

#### `get_day_ahead_prices(start_date, end_date, settlement_point=None, page=1, page_size=5000)`
Fetch day-ahead market settlement point prices for a specific page.

**Parameters:**
- `start_date`: Start date (YYYY-MM-DD string or datetime.date)
- `end_date`: End date (YYYY-MM-DD string or datetime.date)
- `settlement_point`: Optional settlement point filter
- `page`: Page number (default: 1)
- `page_size`: Records per page (max: 5000)

**Returns:** Dictionary with `data` and `page` keys, or None if failed

#### `get_physical_prices(start_date, end_date, settlement_point=None, page=1, page_size=5000)`
Fetch real-time market settlement point prices for a specific page.

**Parameters:** Same as `get_day_ahead_prices`
**Returns:** Dictionary with `data` and `page` keys, or None if failed

#### `get_day_ahead_prices_all(start_date, end_date, settlement_point=None, max_pages=None)`
Fetch all day-ahead prices using automatic pagination.

**Parameters:**
- `start_date`: Start date
- `end_date`: End date  
- `settlement_point`: Optional settlement point filter
- `max_pages`: Optional maximum pages to fetch

**Returns:** List of all price records across pages

#### `get_physical_prices_all(start_date, end_date, settlement_point=None, max_pages=None)`
Fetch all physical prices using automatic pagination.

**Parameters:** Same as `get_day_ahead_prices_all`
**Returns:** List of all price records across pages

### Utility Methods

#### `get_settlement_points_info()`
Get information about available settlement points.
**Returns:** Dictionary with `hubs`, `load_zones`, and `all_major_points`

#### `check_api_health()`
Check API connectivity and health status.
**Returns:** Dictionary with health information and status

#### `get_date_range_info()`
Get recommended date ranges based on API limitations.
**Returns:** Dictionary with date range recommendations

---

## 🚨 Important Notes

### Authentication
- **No authentication required** for public API endpoints
- **No API keys needed** - different from private ERCOT API
- **No OAuth tokens** - direct HTTP requests

### Data Limitations
- **90-day rolling window** for historical data
- **Real-time data delayed** by 1-2 hours
- **15-minute intervals** for all pricing data
- **Central Time zone** for all timestamps

### Rate Limiting
- **100 requests per minute** enforced by ERCOT
- **5,000 records per request** maximum
- **Built-in delays** to respect rate limits
- **Automatic retry logic** not implemented (fails fast)

### Performance Considerations
- **Large date ranges** require multiple API calls
- **Pagination handling** automatic in `_all` methods
- **Memory usage** can be high for large datasets
- **Network timeouts** configurable (default 30s)

---

## 🔗 External References

- [ERCOT Public API Documentation](https://developer.ercot.com/applications/pubapi/user-guide/)
- [API Explorer](https://apiexplorer.ercot.com/api-details#api=pubapi-apim-api)
- [ERCOT Market Overview](https://www.ercot.com/markets)

---

## 🏷️ Version History

- **v1.0.0**: Initial implementation with day-ahead and physical price methods
- Core functionality: DAM prices, RTM prices, pagination, rate limiting
- Settlement point filtering and health checks
- Comprehensive error handling and documentation