# UI Chart Enhancements & MLflow-style Backtest Tracking

## Overview

This document outlines the comprehensive enhancements made to the PowerBuffet UI and backtest progress page, including the implementation of MLflow-style data storage for backtest results visualization.

## 📊 PowerBuffet UI Enhancements

### 1. Chart Presets & Search Functionality

#### Features Added:
- **4 Preset Chart Examples**: Pre-configured visualizations for common financial analysis
- **Smart Search Bar**: Search through chart presets by title, description, or tags
- **Category Filtering**: Filter presets by type (stock, financial, market, sector)
- **One-Click Loading**: Instantly configure charts with predefined settings

#### Preset Chart Types:

1. **📈 Company Share Price Trends**
   - **Purpose**: Compare stock price movements over time
   - **Data**: Close prices, volume, date ranges
   - **Tags**: AAPL, MSFT, GOOGL, AMZN, price, trend
   - **Chart Type**: Line chart

2. **📊 Financial Ratios Analysis**
   - **Purpose**: Analyze P/E ratios, debt-to-equity, valuation metrics
   - **Data**: Market cap vs financial ratios
   - **Tags**: PE, ratio, analysis, fundamental, valuation
   - **Chart Type**: Scatter plot

3. **🥧 Sector Distribution & Performance**
   - **Purpose**: Portfolio breakdown by industry sectors
   - **Data**: Sector allocation, performance metrics
   - **Tags**: sector, distribution, performance, breakdown
   - **Chart Type**: Bar chart

4. **🔗 Asset Correlation Matrix**
   - **Purpose**: Relationships between different assets
   - **Data**: Correlation coefficients, risk analysis
   - **Tags**: correlation, heatmap, relationships, risk
   - **Chart Type**: Correlation heatmap

#### Implementation Details:
```javascript
// Chart presets are loaded dynamically
const chartPresets = [
    {
        id: 'company_stock_prices',
        title: '📈 Company Share Price Trends',
        description: 'Compare stock price movements over time',
        category: 'stock',
        x_column: 'date',
        y_columns: ['close_price', 'volume'],
        chart_type: 'line',
        tags: ['AAPL', 'MSFT', 'GOOGL', 'price', 'trend']
    },
    // ... more presets
];
```

## 📈 Backtest Progress Page Enhancements

### 2. Live Performance Charts

#### New Visualization Features:
- **Real-time Chart Updates**: Live portfolio performance during backtest execution
- **3 Chart Types**: Portfolio value, returns analysis, drawdown monitoring
- **Interactive Switching**: Toggle between different chart views
- **Responsive Design**: Optimized for all screen sizes

#### Chart Types:

1. **Portfolio Value Chart**
   - Current vs initial value comparison
   - Real-time P&L calculation
   - Percentage change tracking
   - Color-coded performance indicators

2. **Returns Analysis Chart**
   - Average daily returns
   - Best/worst trading day metrics
   - Win rate statistics
   - Data point summaries

3. **Drawdown Analysis Chart**
   - Current drawdown percentage
   - Maximum drawdown tracking
   - Risk level indicators (LOW/MEDIUM/HIGH)
   - Visual progress bars

### 3. Enhanced Layout Design

#### UI Improvements:
- **Split Layout**: Progress log and charts side-by-side
- **Expandable Metrics Panel**: Detailed performance statistics
- **Real-time Updates**: Live metric updates during execution
- **Professional Styling**: Dark theme with Bootstrap 5 components

## 🏪 MLflow-style Backtest Storage

### 4. Experiment Tracking System

#### Core Features:
- **Run Storage**: Persistent storage of backtest results
- **Experiment Organization**: Group related backtests
- **Artifact Management**: Store charts, data, and reports
- **Comparison Tools**: Side-by-side run analysis

#### Storage Architecture:

```python
class MLflowBacktestTracker:
    """MLflow-style tracking for backtest experiments"""
    
    def __init__(self, tracking_uri: str = None):
        # Initialize SQLite database and artifact storage
        
    def start_run(self, experiment_name: str, run_name: str = None) -> str:
        # Create new backtest run with unique ID
        
    def log_metrics(self, run_id: str, metrics: Dict[str, float]):
        # Store performance metrics (Sharpe, drawdown, etc.)
        
    def log_parameters(self, run_id: str, parameters: Dict[str, Any]):
        # Store backtest configuration
        
    def log_artifact(self, run_id: str, filename: str, data: Any):
        # Store charts, reports, and other artifacts
```

#### Database Schema:
```sql
-- Experiments table
CREATE TABLE experiments (
    experiment_id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    creation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Runs table
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    run_name TEXT,
    status TEXT DEFAULT 'RUNNING',
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    artifacts_path TEXT
);

-- Metrics, parameters, and tags tables
-- (storing key-value pairs for flexible data structure)
```

### 5. Web Interface Integration

#### New UI Components:
- **Run Counter**: Display total stored runs
- **Current Run ID**: Track active backtest
- **Export Functionality**: Download run data as JSON
- **Comparison Tools**: Multi-run analysis
- **Storage Statistics**: Real-time storage metrics

#### API Endpoints:
```
GET  /api/backtest/tracking/experiments        # List all experiments
GET  /api/backtest/tracking/runs              # List backtest runs
GET  /api/backtest/tracking/runs/{run_id}     # Get run details
POST /api/backtest/tracking/store_run         # Store new backtest run
POST /api/backtest/tracking/runs/compare      # Compare multiple runs
DELETE /api/backtest/tracking/runs/{run_id}   # Delete a run
```

## 🔧 Technical Implementation

### 6. Frontend Enhancements

#### PowerBuffet UI (`powerbuffet.html`):
- Added preset chart selection interface
- Implemented search and filtering functionality
- Enhanced drag-and-drop column selection
- Integrated preset loading with existing visualization system

#### Backtest Progress UI (`backtest_progress.html`):
- Redesigned layout with 4-panel structure
- Added real-time chart rendering
- Implemented MLflow-style storage interface
- Enhanced metrics display and export functionality

### 7. Backend Integration

#### Controller Updates (`dashboard_controller.py`):
- Added 6 new API endpoints for tracking
- Integrated MLflowBacktestTracker service
- Enhanced error handling and logging
- Implemented run comparison functionality

#### MLflow Service (`mlflow_backtest_tracker.py`):
- Complete experiment tracking system
- SQLite database for metadata storage
- File system for artifact storage
- Context manager for easy integration

## 📊 Usage Examples

### 8. PowerBuffet Chart Presets

```javascript
// Load a preset chart
function loadPresetChart(presetId) {
    const preset = chartPresets.find(p => p.id === presetId);
    
    // Clear current selections
    clearAllSelections();
    
    // Configure chart type and columns
    document.getElementById('chartTypeSelect').value = preset.chart_type;
    
    // Auto-load column data
    addPresetColumn(preset.x_column, 'x', preset.title);
    preset.y_columns.forEach(col => {
        addPresetColumn(col, 'y', preset.title);
    });
}
```

### 9. Backtest Run Storage

```python
# Example of storing a backtest run
from src.application.services.mlflow_storage.mlflow_backtest_tracker import start_backtest_run

# Using context manager (recommended)
with start_backtest_run('momentum_strategy', 'run_20241104') as run:
    # Log parameters
    run.log_params({
        'algorithm': 'momentum',
        'lookback': 20,
        'initial_capital': 100000
    })
    
    # During backtest execution
    run.log_metrics({
        'total_return': 15.6,
        'sharpe_ratio': 1.23,
        'max_drawdown': -8.4
    })
    
    # Store artifacts
    run.log_artifact('performance_chart.png', chart_data)
    run.log_artifact('trade_log.json', trade_history)
```

### 10. Run Comparison

```javascript
// Compare multiple backtest runs
function compareRuns() {
    const runIds = ['run_001', 'run_002', 'run_003'];
    
    fetch('/api/backtest/tracking/runs/compare', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({run_ids: runIds})
    })
    .then(response => response.json())
    .then(data => {
        displayComparisonResults(data.comparison);
    });
}
```

## 🎯 Benefits

### 11. Key Advantages

1. **Enhanced User Experience**
   - Intuitive chart presets reduce setup time
   - Real-time visualization improves monitoring
   - Search functionality accelerates workflow

2. **Professional Analytics**
   - MLflow-style tracking matches industry standards
   - Comprehensive experiment organization
   - Reproducible research capabilities

3. **Performance Monitoring**
   - Live charts during backtest execution
   - Multiple visualization perspectives
   - Risk management indicators

4. **Data Persistence**
   - Long-term storage of all backtest results
   - Easy retrieval and comparison
   - Export functionality for external analysis

## 🔮 Future Enhancements

### 12. Planned Improvements

1. **Advanced Charting**
   - TradingView integration for professional charts
   - Interactive zoom and pan functionality
   - Technical indicator overlays

2. **Machine Learning Integration**
   - Model performance tracking
   - Hyperparameter optimization logs
   - Feature importance visualization

3. **Collaboration Features**
   - Shared experiments and runs
   - Team-based analysis workflows
   - Comment and annotation system

4. **Real-time WebSocket Updates**
   - Live streaming of backtest progress
   - Real-time chart updates without polling
   - Push notifications for completed runs

## 📋 Installation & Setup

### 13. Requirements

The enhancements use existing dependencies plus:
- SQLite (built into Python)
- MLflow (already in requirements.txt)
- Bootstrap 5.1.3 (CDN)
- Font Awesome 6.0.0 (CDN)

### 14. Getting Started

1. **Start the Flask Application**
   ```bash
   python -m src.main
   ```

2. **Access PowerBuffet with Presets**
   - Navigate to: `http://localhost:5000/powerbuffet`
   - Use search bar to find specific chart types
   - Click preset cards to auto-configure visualizations

3. **Monitor Backtest with Charts**
   - Navigate to: `http://localhost:5000/backtest_progress`
   - Start a backtest simulation
   - Toggle between Portfolio/Returns/Drawdown views
   - Monitor real-time metrics and storage statistics

4. **View Stored Runs**
   - Click "View Stored Runs" to see history
   - Use "Export Current Run" to download data
   - Compare runs for performance analysis

## 🏁 Conclusion

These enhancements transform the base infrastructure into a professional-grade trading analytics platform with:
- **User-Friendly Interface**: Preset charts and search functionality
- **Real-time Monitoring**: Live performance visualization
- **Professional Storage**: MLflow-style experiment tracking
- **Comprehensive Analysis**: Multi-run comparison capabilities

The implementation maintains compatibility with existing systems while adding enterprise-level features for serious quantitative trading research and development.