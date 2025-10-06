"""
PowerBuffet - Data Visualization and Database Explorer Tool

A lightweight Power BI alternative that provides database connectivity,
table browsing, and predefined visualization templates using Python.
All data preparation and formatting are handled in Python for consistency
with backend computation and analytical workflows.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import seaborn as sns
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import io
import base64
import numpy as np

logger = logging.getLogger(__name__)


class PowerBuffetService:
    """
    PowerBuffet service for database visualization and exploration
    """
    
    def __init__(self):
        self.visualization_registry = self._initialize_visualization_registry()
        
    def _initialize_visualization_registry(self) -> Dict[str, callable]:
        """Initialize the registry of available visualization functions"""
        return {
            "Portfolio Performance": self._plot_portfolio_performance,
            "Asset Correlation Heatmap": self._plot_correlation_heatmap,
            "Sector Distribution": self._plot_sector_distribution,
            "Market Cap Analysis": self._plot_market_cap_analysis,
            "Trading Volume Trends": self._plot_volume_trends,
            "Financial Ratios Comparison": self._plot_financial_ratios,
            "Time Series Analysis": self._plot_time_series
        }
    
    def get_available_databases(self) -> List[Dict[str, str]]:
        """Get list of available database connections"""
        databases = []
        
        # Check for SQLite databases in the project
        project_root = Path(__file__).parents[5]  # Navigate to project root
        sqlite_files = list(project_root.rglob("*.db")) + list(project_root.rglob("*.sqlite"))
        
        for db_file in sqlite_files:
            databases.append({
                "name": db_file.name,
                "type": "SQLite",
                "path": str(db_file),
                "connection_string": str(db_file)
            })
        
        # Add predefined database connections (can be extended)
        # databases.extend([
        #     {"name": "Production SQL Server", "type": "SQL Server", "connection_string": "..."},
        #     {"name": "Analytics PostgreSQL", "type": "PostgreSQL", "connection_string": "..."}
        # ])
        
        return databases
    
    def get_database_tables(self, database_path: str) -> List[Dict[str, Any]]:
        """Get tables from the selected database"""
        tables = []
        
        try:
            if database_path.endswith(('.db', '.sqlite')):
                conn = sqlite3.connect(database_path)
                cursor = conn.cursor()
                
                # Get table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                table_names = cursor.fetchall()
                
                for (table_name,) in table_names:
                    # Get table info
                    cursor.execute(f"PRAGMA table_info({table_name});")
                    columns = cursor.fetchall()
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    row_count = cursor.fetchone()[0]
                    
                    tables.append({
                        "name": table_name,
                        "columns": [{"name": col[1], "type": col[2]} for col in columns],
                        "row_count": row_count
                    })
                
                conn.close()
                
        except Exception as e:
            logger.error(f"Error getting tables from database {database_path}: {e}")
            
        return tables
    
    def get_available_visualizations(self) -> List[str]:
        """Get list of available visualization templates"""
        return list(self.visualization_registry.keys())
    
    def run_visualization(self, database_path: str, table_name: str, 
                         visualization_name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a visualization function and return the result"""
        try:
            if visualization_name not in self.visualization_registry:
                raise ValueError(f"Unknown visualization: {visualization_name}")
            
            # Load data from database
            data = self._load_table_data(database_path, table_name)
            
            # Execute visualization function
            viz_func = self.visualization_registry[visualization_name]
            result = viz_func(data, params or {})
            
            return {
                "success": True,
                "visualization": result,
                "metadata": {
                    "database": database_path,
                    "table": table_name,
                    "visualization": visualization_name,
                    "row_count": len(data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error running visualization: {e}")
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "database": database_path,
                    "table": table_name,
                    "visualization": visualization_name
                }
            }
    
    def _load_table_data(self, database_path: str, table_name: str, limit: int = 10000) -> pd.DataFrame:
        """Load data from database table"""
        if database_path.endswith(('.db', '.sqlite')):
            conn = sqlite3.connect(database_path)
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            data = pd.read_sql_query(query, conn)
            conn.close()
            return data
        else:
            raise NotImplementedError("Only SQLite databases are currently supported")
    
    def _create_plot_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string"""
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close(fig)
        return img_data

    # Visualization functions
    def _plot_portfolio_performance(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate portfolio performance visualization"""
        try:
            # Try to identify relevant columns for portfolio analysis
            numeric_cols = data.select_dtypes(include=['number']).columns
            
            if len(numeric_cols) == 0:
                return {"error": "No numeric columns found for portfolio analysis"}
            
            # Create a simple line plot with the first numeric column
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(data.index, data[numeric_cols[0]], linewidth=2, color='blue')
            ax.set_title(f"Portfolio Performance - {numeric_cols[0]}", fontsize=16, fontweight='bold')
            ax.set_ylabel(numeric_cols[0])
            ax.grid(True, alpha=0.3)
            
            plot_image = self._create_plot_base64(fig)
            
            return {
                "plot_image": plot_image,
                "summary_stats": {
                    "mean": float(data[numeric_cols[0]].mean()),
                    "std": float(data[numeric_cols[0]].std()),
                    "min": float(data[numeric_cols[0]].min()),
                    "max": float(data[numeric_cols[0]].max())
                }
            }
            
        except Exception as e:
            return {"error": f"Error generating portfolio performance plot: {str(e)}"}
    
    def _plot_correlation_heatmap(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate correlation heatmap"""
        try:
            numeric_data = data.select_dtypes(include=['number'])
            
            if len(numeric_data.columns) < 2:
                return {"error": "Need at least 2 numeric columns for correlation analysis"}
            
            corr_matrix = numeric_data.corr()
            
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, ax=ax)
            ax.set_title("Asset Correlation Heatmap", fontsize=16, fontweight='bold')
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating correlation heatmap: {str(e)}"}
    
    def _plot_sector_distribution(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate sector distribution pie chart"""
        try:
            # Look for sector-like columns
            text_cols = data.select_dtypes(include=['object']).columns
            sector_col = None
            
            for col in text_cols:
                if 'sector' in col.lower() or 'category' in col.lower() or 'type' in col.lower():
                    sector_col = col
                    break
            
            if sector_col is None and len(text_cols) > 0:
                sector_col = text_cols[0]
            
            if sector_col is None:
                return {"error": "No categorical columns found for sector analysis"}
            
            sector_counts = data[sector_col].value_counts()
            
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.pie(sector_counts.values, labels=sector_counts.index, autopct='%1.1f%%', startangle=90)
            ax.set_title(f"Distribution by {sector_col}", fontsize=16, fontweight='bold')
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating sector distribution: {str(e)}"}
    
    def _plot_market_cap_analysis(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate market cap analysis"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            
            # Look for market cap or value-related columns
            value_col = None
            for col in numeric_cols:
                if any(term in col.lower() for term in ['cap', 'value', 'market', 'price']):
                    value_col = col
                    break
            
            if value_col is None and len(numeric_cols) > 0:
                value_col = numeric_cols[0]
                
            if value_col is None:
                return {"error": "No numeric columns found for market cap analysis"}
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.hist(data[value_col].dropna(), bins=20, alpha=0.7, edgecolor='black')
            ax.set_title(f"Market Cap Distribution - {value_col}", fontsize=16, fontweight='bold')
            ax.set_xlabel(value_col)
            ax.set_ylabel('Frequency')
            ax.grid(True, alpha=0.3)
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating market cap analysis: {str(e)}"}
    
    def _plot_volume_trends(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate trading volume trends"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            
            volume_col = None
            for col in numeric_cols:
                if 'volume' in col.lower() or 'quantity' in col.lower():
                    volume_col = col
                    break
                    
            if volume_col is None and len(numeric_cols) > 0:
                volume_col = numeric_cols[0]
                
            if volume_col is None:
                return {"error": "No numeric columns found for volume analysis"}
            
            # Limit to first 20 rows for readability
            plot_data = data.head(20)
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(range(len(plot_data)), plot_data[volume_col], alpha=0.7)
            ax.set_title(f"Volume Trends - {volume_col}", fontsize=16, fontweight='bold')
            ax.set_xlabel('Data Points')
            ax.set_ylabel(volume_col)
            ax.grid(True, alpha=0.3)
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating volume trends: {str(e)}"}
    
    def _plot_financial_ratios(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate financial ratios comparison"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            
            if len(numeric_cols) < 2:
                return {"error": "Need at least 2 numeric columns for ratio comparison"}
            
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.scatter(data[numeric_cols[0]], data[numeric_cols[1]], alpha=0.6)
            ax.set_title(f"Financial Ratios: {numeric_cols[0]} vs {numeric_cols[1]}", fontsize=16, fontweight='bold')
            ax.set_xlabel(numeric_cols[0])
            ax.set_ylabel(numeric_cols[1])
            ax.grid(True, alpha=0.3)
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating financial ratios plot: {str(e)}"}
    
    def _plot_time_series(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate time series analysis"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            
            if len(numeric_cols) == 0:
                return {"error": "No numeric columns found for time series"}
            
            # Use index as x-axis
            y_col = numeric_cols[0]
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(data.index, data[y_col], linewidth=2, color='green')
            ax.set_title(f"Time Series Analysis - {y_col}", fontsize=16, fontweight='bold')
            ax.set_xlabel('Data Points')
            ax.set_ylabel(y_col)
            ax.grid(True, alpha=0.3)
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating time series plot: {str(e)}"}