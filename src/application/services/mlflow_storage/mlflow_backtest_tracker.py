"""
MLflow-style backtest results tracking and storage service.
This service provides experiment tracking capabilities similar to MLflow
for storing and retrieving backtest results, metrics, and artifacts.
"""

import json
import os
import sqlite3
import pickle
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import uuid

@dataclass
class BacktestRun:
    """Represents a single backtest run with all associated data"""
    run_id: str
    experiment_name: str
    run_name: str
    timestamp: datetime
    status: str  # 'RUNNING', 'FINISHED', 'FAILED'
    start_time: datetime
    end_time: Optional[datetime] = None
    parameters: Dict[str, Any] = None
    metrics: Dict[str, float] = None
    tags: Dict[str, str] = None
    artifacts_path: str = None

class MLflowBacktestTracker:
    """
    MLflow-style tracking service for backtest experiments.
    Provides functionality to log parameters, metrics, and artifacts.
    """
    
    def __init__(self, tracking_uri: str = None):
        """
        Initialize the backtest tracker.
        
        Args:
            tracking_uri: Path to store tracking data (default: ./mlflow_tracking)
        """
        self.tracking_uri = tracking_uri or os.path.join(os.getcwd(), 'mlflow_tracking')
        self.db_path = os.path.join(self.tracking_uri, 'backtest_tracking.db')
        self.artifacts_root = os.path.join(self.tracking_uri, 'artifacts')
        
        # Create directories if they don't exist
        os.makedirs(self.tracking_uri, exist_ok=True)
        os.makedirs(self.artifacts_root, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize the SQLite database for tracking runs"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    creation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL,
                    run_name TEXT,
                    status TEXT DEFAULT 'RUNNING',
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    artifacts_path TEXT,
                    FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS run_metrics (
                    run_id TEXT,
                    key TEXT,
                    value REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    step INTEGER DEFAULT 0,
                    PRIMARY KEY (run_id, key, step),
                    FOREIGN KEY (run_id) REFERENCES runs (run_id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS run_parameters (
                    run_id TEXT,
                    key TEXT,
                    value TEXT,
                    PRIMARY KEY (run_id, key),
                    FOREIGN KEY (run_id) REFERENCES runs (run_id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS run_tags (
                    run_id TEXT,
                    key TEXT,
                    value TEXT,
                    PRIMARY KEY (run_id, key),
                    FOREIGN KEY (run_id) REFERENCES runs (run_id)
                )
            ''')
            
            conn.commit()
    
    def create_experiment(self, experiment_name: str) -> str:
        """
        Create a new experiment.
        
        Args:
            experiment_name: Name of the experiment
            
        Returns:
            experiment_id: Unique identifier for the experiment
        """
        experiment_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    'INSERT INTO experiments (experiment_id, name) VALUES (?, ?)',
                    (experiment_id, experiment_name)
                )
                conn.commit()
                return experiment_id
            except sqlite3.IntegrityError:
                # Experiment already exists, return existing ID
                cursor = conn.execute(
                    'SELECT experiment_id FROM experiments WHERE name = ?',
                    (experiment_name,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
    
    def get_experiment_by_name(self, experiment_name: str) -> Optional[str]:
        """Get experiment ID by name"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT experiment_id FROM experiments WHERE name = ?',
                (experiment_name,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    
    def start_run(self, experiment_name: str = 'default_backtest_experiment', run_name: str = None) -> str:
        """
        Start a new backtest run.
        
        Args:
            experiment_name: Name of the experiment
            run_name: Optional name for the run
            
        Returns:
            run_id: Unique identifier for the run
        """
        # Ensure experiment exists
        experiment_id = self.get_experiment_by_name(experiment_name)
        if not experiment_id:
            experiment_id = self.create_experiment(experiment_name)
        
        run_id = str(uuid.uuid4())
        if not run_name:
            run_name = f"backtest_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create artifacts directory for this run
        run_artifacts_path = os.path.join(self.artifacts_root, run_id)
        os.makedirs(run_artifacts_path, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT INTO runs (run_id, experiment_id, run_name, artifacts_path) VALUES (?, ?, ?, ?)',
                (run_id, experiment_id, run_name, run_artifacts_path)
            )
            conn.commit()
        
        return run_id
    
    def log_parameter(self, run_id: str, key: str, value: Any):
        """Log a parameter for a run"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO run_parameters (run_id, key, value) VALUES (?, ?, ?)',
                (run_id, key, str(value))
            )
            conn.commit()
    
    def log_parameters(self, run_id: str, parameters: Dict[str, Any]):
        """Log multiple parameters for a run"""
        for key, value in parameters.items():
            self.log_parameter(run_id, key, value)
    
    def log_metric(self, run_id: str, key: str, value: float, step: int = 0):
        """Log a metric for a run"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO run_metrics (run_id, key, value, step) VALUES (?, ?, ?, ?)',
                (run_id, key, value, step)
            )
            conn.commit()
    
    def log_metrics(self, run_id: str, metrics: Dict[str, float], step: int = 0):
        """Log multiple metrics for a run"""
        for key, value in metrics.items():
            self.log_metric(run_id, key, value, step)
    
    def set_tag(self, run_id: str, key: str, value: str):
        """Set a tag for a run"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO run_tags (run_id, key, value) VALUES (?, ?, ?)',
                (run_id, key, value)
            )
            conn.commit()
    
    def set_tags(self, run_id: str, tags: Dict[str, str]):
        """Set multiple tags for a run"""
        for key, value in tags.items():
            self.set_tag(run_id, key, value)
    
    def log_artifact(self, run_id: str, filename: str, data: Any, artifact_type: str = 'json'):
        """
        Log an artifact for a run.
        
        Args:
            run_id: Run identifier
            filename: Name of the artifact file
            data: Data to store
            artifact_type: Type of artifact ('json', 'pickle', 'text')
        """
        # Get artifacts path for run
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT artifacts_path FROM runs WHERE run_id = ?', (run_id,))
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Run {run_id} not found")
            
            artifacts_path = result[0]
        
        file_path = os.path.join(artifacts_path, filename)
        
        if artifact_type == 'json':
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        elif artifact_type == 'pickle':
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
        elif artifact_type == 'text':
            with open(file_path, 'w') as f:
                f.write(str(data))
        else:
            raise ValueError(f"Unsupported artifact type: {artifact_type}")
    
    def end_run(self, run_id: str, status: str = 'FINISHED'):
        """
        End a run with the specified status.
        
        Args:
            run_id: Run identifier
            status: Final status ('FINISHED', 'FAILED')
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'UPDATE runs SET status = ?, end_time = CURRENT_TIMESTAMP WHERE run_id = ?',
                (status, run_id)
            )
            conn.commit()
    
    def get_run(self, run_id: str) -> Optional[Dict]:
        """Get detailed information about a specific run"""
        with sqlite3.connect(self.db_path) as conn:
            # Get basic run info
            cursor = conn.execute('''
                SELECT r.run_id, r.run_name, r.status, r.start_time, r.end_time, r.artifacts_path, e.name as experiment_name
                FROM runs r 
                JOIN experiments e ON r.experiment_id = e.experiment_id 
                WHERE r.run_id = ?
            ''', (run_id,))
            
            run_info = cursor.fetchone()
            if not run_info:
                return None
            
            # Get parameters
            cursor = conn.execute('SELECT key, value FROM run_parameters WHERE run_id = ?', (run_id,))
            parameters = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get metrics
            cursor = conn.execute('SELECT key, value FROM run_metrics WHERE run_id = ? ORDER BY key, step', (run_id,))
            metrics = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get tags
            cursor = conn.execute('SELECT key, value FROM run_tags WHERE run_id = ?', (run_id,))
            tags = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                'run_id': run_info[0],
                'run_name': run_info[1],
                'status': run_info[2],
                'start_time': run_info[3],
                'end_time': run_info[4],
                'artifacts_path': run_info[5],
                'experiment_name': run_info[6],
                'parameters': parameters,
                'metrics': metrics,
                'tags': tags
            }
    
    def list_runs(self, experiment_name: str = None, limit: int = 100) -> List[Dict]:
        """
        List runs, optionally filtered by experiment.
        
        Args:
            experiment_name: Filter by experiment name
            limit: Maximum number of runs to return
            
        Returns:
            List of run dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            if experiment_name:
                query = '''
                    SELECT r.run_id, r.run_name, r.status, r.start_time, r.end_time, e.name as experiment_name
                    FROM runs r 
                    JOIN experiments e ON r.experiment_id = e.experiment_id 
                    WHERE e.name = ?
                    ORDER BY r.start_time DESC
                    LIMIT ?
                '''
                cursor = conn.execute(query, (experiment_name, limit))
            else:
                query = '''
                    SELECT r.run_id, r.run_name, r.status, r.start_time, r.end_time, e.name as experiment_name
                    FROM runs r 
                    JOIN experiments e ON r.experiment_id = e.experiment_id 
                    ORDER BY r.start_time DESC
                    LIMIT ?
                '''
                cursor = conn.execute(query, (limit,))
            
            runs = []
            for row in cursor.fetchall():
                runs.append({
                    'run_id': row[0],
                    'run_name': row[1],
                    'status': row[2],
                    'start_time': row[3],
                    'end_time': row[4],
                    'experiment_name': row[5]
                })
            
            return runs
    
    def compare_runs(self, run_ids: List[str]) -> Dict:
        """
        Compare multiple runs side by side.
        
        Args:
            run_ids: List of run IDs to compare
            
        Returns:
            Dictionary with comparison data
        """
        comparison_data = {
            'runs': {},
            'common_metrics': set(),
            'common_parameters': set()
        }
        
        for run_id in run_ids:
            run_data = self.get_run(run_id)
            if run_data:
                comparison_data['runs'][run_id] = run_data
                
                if comparison_data['common_metrics']:
                    comparison_data['common_metrics'] &= set(run_data['metrics'].keys())
                else:
                    comparison_data['common_metrics'] = set(run_data['metrics'].keys())
                
                if comparison_data['common_parameters']:
                    comparison_data['common_parameters'] &= set(run_data['parameters'].keys())
                else:
                    comparison_data['common_parameters'] = set(run_data['parameters'].keys())
        
        comparison_data['common_metrics'] = list(comparison_data['common_metrics'])
        comparison_data['common_parameters'] = list(comparison_data['common_parameters'])
        
        return comparison_data
    
    def get_experiments(self) -> List[Dict]:
        """Get list of all experiments"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT experiment_id, name, creation_time FROM experiments ORDER BY creation_time DESC')
            return [
                {
                    'experiment_id': row[0],
                    'name': row[1],
                    'creation_time': row[2]
                }
                for row in cursor.fetchall()
            ]
    
    def delete_run(self, run_id: str) -> bool:
        """Delete a run and all associated data"""
        with sqlite3.connect(self.db_path) as conn:
            # Get artifacts path first
            cursor = conn.execute('SELECT artifacts_path FROM runs WHERE run_id = ?', (run_id,))
            result = cursor.fetchone()
            if not result:
                return False
            
            artifacts_path = result[0]
            
            # Delete database records
            conn.execute('DELETE FROM run_metrics WHERE run_id = ?', (run_id,))
            conn.execute('DELETE FROM run_parameters WHERE run_id = ?', (run_id,))
            conn.execute('DELETE FROM run_tags WHERE run_id = ?', (run_id,))
            conn.execute('DELETE FROM runs WHERE run_id = ?', (run_id,))
            conn.commit()
            
            # Delete artifacts directory
            import shutil
            if os.path.exists(artifacts_path):
                shutil.rmtree(artifacts_path)
            
            return True

# Example usage and helper functions
class BacktestTrackingContext:
    """Context manager for backtest tracking"""
    
    def __init__(self, tracker: MLflowBacktestTracker, experiment_name: str, run_name: str = None):
        self.tracker = tracker
        self.experiment_name = experiment_name
        self.run_name = run_name
        self.run_id = None
    
    def __enter__(self):
        self.run_id = self.tracker.start_run(self.experiment_name, self.run_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.tracker.end_run(self.run_id, 'FINISHED')
        else:
            self.tracker.end_run(self.run_id, 'FAILED')
    
    def log_param(self, key: str, value: Any):
        """Log a parameter"""
        self.tracker.log_parameter(self.run_id, key, value)
    
    def log_params(self, params: Dict[str, Any]):
        """Log multiple parameters"""
        self.tracker.log_parameters(self.run_id, params)
    
    def log_metric(self, key: str, value: float, step: int = 0):
        """Log a metric"""
        self.tracker.log_metric(self.run_id, key, value, step)
    
    def log_metrics(self, metrics: Dict[str, float], step: int = 0):
        """Log multiple metrics"""
        self.tracker.log_metrics(self.run_id, metrics, step)
    
    def log_artifact(self, filename: str, data: Any, artifact_type: str = 'json'):
        """Log an artifact"""
        self.tracker.log_artifact(self.run_id, filename, data, artifact_type)
    
    def set_tag(self, key: str, value: str):
        """Set a tag"""
        self.tracker.set_tag(self.run_id, key, value)

# Global tracker instance
_tracker = None

def get_tracker(tracking_uri: str = None) -> MLflowBacktestTracker:
    """Get global tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = MLflowBacktestTracker(tracking_uri)
    return _tracker

def start_backtest_run(experiment_name: str = 'default_backtest_experiment', run_name: str = None) -> BacktestTrackingContext:
    """Start a backtest run with context manager"""
    tracker = get_tracker()
    return BacktestTrackingContext(tracker, experiment_name, run_name)