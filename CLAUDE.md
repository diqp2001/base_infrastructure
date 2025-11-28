# CLAUDE.md

## 🧠 Contributor Logic, Architecture, and Unified Development Essentials

Welcome to the `base_infrastructure` project! This guide outlines key conventions and architectural decisions to ensure all contributors align with the vision and structure of the codebase.

---

## 1. 🔧 Project Structure (DDD-Oriented)

We use **Domain-Driven Design (DDD)** principles to separate concerns:

src/
├── domain/ # Core business logic (independent of frameworks)
│ ├── entities/ # Pure domain models (no SQLAlchemy)
│ └── ports/ # Interfaces for repository/service contracts
├── infrastructure/
│ ├── models/ # ORM models (SQLAlchemy)
│ └── repositories/ # Concrete implementations of domain ports
├── application/
│ └── services/ # Use cases, orchestrating domain and infra
tests/


---

## 2. 📏 Code Conventions

- **Language**: Python 3.11+
- **ORM**: SQLAlchemy (v2-style)
- **Testing**: `unittest` with `test_*.py` naming in `/tests`
- **Imports**: Use absolute imports within `src/`

> ✨ Tip: Run `python -m unittest discover tests` to execute all tests.

---

## 3. ✅ Contribution Guidelines

- Fork and branch from `main`
- Follow feature/bugfix branch naming:

- Keep PRs under ~300 lines when possible
- Include/modify relevant unit tests
- Keep domain logic pure: no SQLAlchemy in `domain/`

---

## 4. 🧪 Testing Philosophy

- Domain logic: tested in isolation (no DB)
- Infrastructure: tested using mocks or local SQLite
- Use `@dataclass` for entities when appropriate

---

## 5. 📦 Virtual Environment Setup

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

---

## 6. 🎯 Recent Enhancements (2025-01-16)

### ✅ Fixed TestProjectBacktestManager Error
- **Issue**: `unsupported operand type(s) for -: 'float' and 'decimal.Decimal'`
- **Solution**: Added type conversion in line 204 of `test_project_backtest_manager.py`
- **Location**: `src/application/managers/project_managers/test_project_backtest/`

### 🚀 Comprehensive Trading Dashboard Hub
- **New Route**: `/dashboard` - Complete 7-view trading interface
- **Features**:
  - Algorithm selection with interactive parameter controls
  - Real-time KPI display (portfolio value, daily P&L, positions)
  - 7 specialized views: Algorithm Management, Portfolio Overview, Database Explorer, Entity Management, Order History, Backtest Results
  - Bootstrap 5.1.3 responsive design with sidebar navigation
  - Save/load configuration presets

### 📊 Enhanced Performance Visualization  
- **4-Panel Chart System**: Portfolio evolution, returns distribution, drawdown analysis, cumulative returns
- **Matplotlib Integration**: Server-side chart generation with base64 encoding
- **Performance Metrics**: Sharpe ratio, volatility, max drawdown, win rate calculations
- **Routes**: `/test_backtest` and `/test_live_trading` with visualization

### 🔌 Comprehensive API Endpoints
```
GET  /api/entities/company_shares          # All company data with market/fundamental info
GET  /api/entities/company_shares/{id}     # Specific company by ID  
GET  /api/entities/summary                 # Database entities summary with sector breakdown
POST /api/test_managers/backtest           # Execute TestProjectBacktestManager via API
POST /api/test_managers/live_trading       # Execute TestProjectLiveTradingManager via API
```

### 📱 Web Interface Improvements
- **Landing Page**: Updated with comprehensive dashboard link and feature highlights
- **Navigation**: Seamless integration between legacy and new interfaces  
- **Error Handling**: Flash messages, loading states, user-friendly error displays
- **Performance**: Lazy loading, client-side caching, efficient database queries

---

## 7. 🏗️ Architecture Enhancements

### Interface Layer Structure
```
src/interfaces/
└── flask/
    ├── flask.py                    # Main Flask app factory
    ├── web/                        # HTML views + controllers
    │   ├── controllers/
    │   │   └── dashboard_controller.py
    │   ├── templates/
    │   │   ├── index.html         # Legacy home page
    │   │   ├── dashboard_hub.html # NEW: Comprehensive dashboard
    │   │   └── performance_results.html
    │   └── static/
    └── api/                        # REST/JSON API
        ├── controllers/
        │   └── backtest_controller.py
        └── routes/
```

### Data Flow Integration
- **Type Safety**: Automatic Decimal ↔ Float conversion for financial calculations
- **JSON Serialization**: Custom serializers for DateTime and Decimal objects
- **Error Boundaries**: Comprehensive exception handling with proper HTTP status codes

---

## 8. 🧪 Testing & Usage

### Quick Start Commands
```bash
# Run Flask development server  
python -m src.interfaces.flask.flask

# Execute backtest with visualization
# Navigate to: http://localhost:5000/dashboard

# API testing
curl http://localhost:5000/api/entities/summary
curl -X POST http://localhost:5000/api/test_managers/backtest
```

### Testing Suite
```bash
# Run all unit tests
python -m unittest discover tests

# Test specific components
python -m unittest tests.test_backtest_manager
python -m unittest tests.test_flask_interface
```

---

## 9. 📚 Documentation Structure

Each layer now includes comprehensive CLAUDE.md files:
- `/CLAUDE.md` - Main project overview (this file)
- `/src/interfaces/CLAUDE.md` - Interface layer architecture
- `/src/interfaces/flask/CLAUDE.md` - Flask implementation details
- `/src/application/managers/CLAUDE.md` - Manager layer patterns
- `/src/application/services/misbuffet/*/CLAUDE.md` - Service-specific documentation

---

## 10. 🔮 Future Roadmap

### Immediate Priorities
- [ ] Real-time WebSocket integration for live market data
- [ ] User authentication and role-based access control
- [ ] Advanced charting with TradingView integration
- [ ] Export functionality (PDF reports, CSV downloads)

### Long-term Vision
- [ ] Microservice architecture migration
- [ ] Mobile companion app (React Native/Flutter)
- [ ] Machine learning model marketplace
- [ ] Multi-broker support expansion

---

## 11. 🔗 External References

### SpatioTemporalMomentum Implementation
For tensor creation, training of multivariate and univariate models, MLP models, and TFT models, refer to the reference implementation at:
https://github.com/KurochkinAlexey/SpatioTemporalMomentum

This repository provides the foundational algorithms and data structures used in the spatiotemporal modeling components of this project.
