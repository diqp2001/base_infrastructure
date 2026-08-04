# Flask Interface Layer - CLAUDE.md

## 📂 Directory Structure

```
src/interfaces/flask/
├── flask.py                     👈 Main Flask app factory
├── web/                         👈 HTML views + controllers
│   ├── controllers/
│   │   └── dashboard_controller.py
│   ├── templates/
│   │   ├── index.html          👈 Legacy home page
│   │   ├── dashboard_hub.html  👈 NEW: Comprehensive dashboard
│   │   ├── performance_results.html
│   │   └── test_manager.html
│   └── static/
│       └── style.css
└── api/                         👈 REST/JSON API
    ├── controllers/
    │   └── backtest_controller.py
    └── routes/
        └── routes.py
```

## 🎯 New Features Implemented

### 0. Entity & Factor Upload (`/entity-upload`)

**Blueprint**: `entity_upload_bp` in `src/interfaces/flask/web/controllers/entity_upload_controller.py`

**Routes**:
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/entity-upload` | Upload form page — select entity type, download template, upload file |
| `GET` | `/entity-upload/template/<entity_type>` | Stream an Excel template (.xlsx) as attachment download |
| `POST` | `/entity-upload` | Process uploaded .xlsx; reads sheet `Data`; returns JSON `{success, processed, errors}` |

**Application service**: `src/application/services/data/entities/entity_upload_service.py`
- `ENTITY_SCHEMAS` — dict of entity type → `{columns, required, example_row, description}`
- `generate_template(entity_type)` — produces a two-sheet openpyxl workbook (Data + Instructions) as `io.BytesIO`
- `process_upload(entity_type, df, session)` — iterates DataFrame rows, resolves FK references by name, persists via `RepositoryFactory`

**Supported entity types** (11 total):
- `Continent` — name only
- `Country` — name, iso_code; FK: continent_name → Continent
- `Exchange` — name, legal_name, start_date; FK: country_name → Country
- `Sector` — name, description
- `Industry` — name, description; FK: sector_name → Sector
- `Currency` — name, symbol; optional FK: country_name → Country
- `Index` — name, symbol; optional FK: currency_symbol → Currency.symbol
- `CompanyShare` — symbol; FK: currency_symbol → Currency.symbol, exchange_name → Exchange
- `Model` — name (backtest model / algorithm)
- `Universe` — name, creation_date, description
- `BacktestFactor` — name, group, and optional subgroup/frequency/data_type/source/definition

**FK resolution**: Name lookups (`get_by_name`) are used for all FK columns. Symbol lookups query `model_class.symbol` directly for Currency and CompanyShare.

**Adding a new entity type**:
1. Add a new key to `ENTITY_SCHEMAS` in `entity_upload_service.py` with `columns`, `required`, `example_row`, and `description`.
2. Add a corresponding handler `_handle_<type>(row)` inside `_build_handlers()`.
3. Add the handler to the returned dict in `_build_handlers()`.
No controller or template changes needed.

### 1. Comprehensive Trading Dashboard Hub (`/dashboard`)
- **7-View Navigation System**: Algorithm Management, Portfolio Overview, Database Explorer, Entity Management, Order History, Backtest Results
- **Interactive Parameter Controls**: Sliders, dropdowns, and form inputs for algorithm configuration
- **Real-time KPI Display**: Portfolio value, daily P&L, active positions, algorithm status
- **Quick Action Buttons**: Run backtest, start live trading, save/load configurations
- **Responsive Bootstrap Design**: Modern UI with sidebar navigation and dynamic content loading

### 2. Enhanced API Endpoints
- `GET /api/entities/company_shares` - All company entities with market/fundamental data
- `GET /api/entities/company_shares/{id}` - Specific company by ID
- `GET /api/entities/summary` - Database summary statistics
- `POST /api/test_managers/backtest` - Execute TestProjectBacktestManager via API
- `POST /api/test_managers/live_trading` - Execute TestProjectLiveTradingManager via API

### 3. Performance Visualization
- **4-Panel Chart System**: Portfolio evolution, returns distribution, drawdown analysis, cumulative returns
- **Matplotlib Integration**: Server-side chart generation with base64 encoding
- **Performance Metrics Calculation**: Sharpe ratio, volatility, max drawdown, win rate

## 🔧 Architecture Principles

### Separation of Concerns
- **Web Layer** → HTML templates with Bootstrap UI
- **API Layer** → JSON responses for programmatic access  
- **Business Logic** → Delegated to application.services and domain layers

### Route Organization
```python
# Web Routes (dashboard_controller.py)
@web_bp.route("/")              # Legacy home page
@web_bp.route("/dashboard")     # NEW: Comprehensive dashboard hub
@web_bp.route("/test_backtest") # Backtest execution with visualization
@web_bp.route("/test_live_trading") # Live trading execution

# API Routes (backtest_controller.py)
@backtest_api.route("/api/entities/company_shares")
@backtest_api.route("/api/test_managers/backtest", methods=["POST"])
```

## 📋 Usage Instructions

### Accessing the New Dashboard
1. **Home Page**: Navigate to `/` for legacy interface with links to new features
2. **Comprehensive Dashboard**: Go to `/dashboard` for the full 7-view trading hub
3. **Direct Access**: Use specific routes like `/test_backtest` for individual features

### Algorithm Configuration
1. **Select Strategy**: Choose from dropdown (Momentum ML, Black-Litterman, etc.)
2. **Adjust Parameters**: Use sliders and inputs for lookback window, risk threshold, position size
3. **Save/Load Presets**: Store configurations in browser localStorage
4. **Execute**: Click "Run Backtest" or "Start Live Trading" buttons

### API Integration
```python
# Example: Execute backtest via API
response = requests.post('/api/test_managers/backtest', json={})

# Example: Get entity data
companies = requests.get('/api/entities/company_shares').json()
```

## 🚀 Performance Features

### Real-time Updates
- **KPI Refresh**: Portfolio metrics update every 30 seconds
- **Dynamic Status**: Live algorithm and system status indicators
- **Interactive Charts**: Hover tooltips and responsive design

### Data Handling
- **Decimal/Float Conversion**: Automatic type handling for financial calculations
- **JSON Serialization**: Custom serializers for DateTime and Decimal objects
- **Error Handling**: Comprehensive exception management with user-friendly messages

## 🔌 Integration Points

### Application Services
- `TestProjectBacktestManager` - Backtesting execution and results
- `TestProjectLiveTradingManager` - Live trading operations  
- `DatabaseManager` - Entity data access and persistence
- `CompanyShareRepository` - Company share CRUD operations

### Frontend Technologies
- **Bootstrap 5.1.3** - Responsive UI framework
- **Font Awesome 6.0** - Icon system
- **Matplotlib** - Server-side chart generation
- **JavaScript** - Dynamic content loading and user interactions

## 📈 Metrics & Monitoring

### Performance Tracking
- **Portfolio KPIs**: Total value, daily P&L, position count
- **Risk Metrics**: Sharpe ratio, volatility, maximum drawdown
- **System Health**: Database connection, TWS API status, data feed status

### User Experience
- **Loading States**: Visual feedback during operations
- **Error Messages**: Flash messages for user notifications
- **Progress Tracking**: Status indicators for long-running operations

## 🔐 Security & Best Practices

### API Security
- Input validation on all endpoints
- Proper HTTP status codes (200, 404, 500)
- Error message sanitization

### Performance Optimization  
- Lazy loading of dashboard sections
- Efficient database queries with proper repository pattern
- Client-side configuration caching

## 🧪 Testing & Development

### Local Development
```bash
# Start Flask development server
python -m src.interfaces.flask.flask

# Access endpoints
http://localhost:5000/                 # Home page
http://localhost:5000/dashboard        # Comprehensive dashboard
http://localhost:5000/api/entities/summary  # API example
```

### Future Enhancements
- [ ] Real-time WebSocket connections for live data
- [ ] User authentication and session management  
- [ ] Advanced charting with TradingView integration
- [ ] Export functionality (CSV, Excel, PDF reports)
- [ ] Mobile-responsive optimizations
