# 📊 Data Visualization and Database Explorer Tool

## Overview
This tool extends the existing **Misbuffet Web Interface** by adding a **Data Visualization and Database Explorer** option.  
Unlike Power BI, all **data preparation and formatting** are handled entirely in **Python**, ensuring consistency with backend computation and analytical workflows.  

The web interface will only act as a **front-end selector and visualization display layer**, not a data transformer.

---

## 🎯 Objective
To provide an integrated interface within the existing Flask-based web tool that allows users to:
1. Select a **database connection** (e.g., SQLite, SQL Server, PostgreSQL).
2. Browse available **tables** within the selected database.
3. Choose a **predefined visualization template**, fully formatted by Python.
4. View the resulting interactive plots and tables directly in the browser.

This will serve as a **lightweight Power BI alternative**, tightly integrated with backend analytics logic and Python data pipelines.

---

## 🧩 Architecture

### 1. **Frontend (Flask Web Interface)**
- Integrated as a new page in the existing Flask interface (e.g., `/powerbuffet`).
- Built with HTML + JavaScript + Jinja2 templates.
- Provides dropdowns and selectors for:
  - Available databases (queried from Python backend).
  - Available tables (fetched dynamically once a database is chosen).
  - Predefined Python visualizations (list of registered plotting functions).
- Displays interactive outputs (plots, tables) using:
  - `Plotly.js` or `Bokeh` for charts.
  - `DataTables.js` for tabular views.

### 2. **Backend (Python + Flask)**
- New Flask routes to handle:
  - `/list_databases`: Returns available database connections.
  - `/list_tables/<database>`: Returns tables for the selected database.
  - `/run_visualization`: Executes a registered Python visualization function and returns JSON/HTML output.
- Visualization functions are defined in Python and preformatted using libraries such as:
  - **Plotly**, **Matplotlib**, or **Altair** for charts.
  - **Pandas** or **Polars** for data aggregation and formatting.

### 3. **Visualization Registry**
- A Python dictionary maps visualization names to preformatted Python functions:
  ```python
  VISUALIZATION_REGISTRY = {
      "Monthly Performance": plot_monthly_performance,
      "Factor Correlation Heatmap": plot_factor_correlation,
      "Portfolio Composition": plot_portfolio_weights,
  }
