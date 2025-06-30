"""
QuantConnect Lean Optimizer.Launcher Result Coordinator

Coordinates optimization results from multiple workers including collection,
aggregation, storage, and real-time reporting.
"""

import asyncio
import json
import csv
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from pathlib import Path
import threading
from collections import defaultdict
import statistics

from .interfaces import (
    IResultCoordinator,
    ResultCoordinationException,
    IOptimizationProgressReporter
)
from ..optimizer.result_management import OptimizationResult, OptimizationStatistics, PerformanceMetrics
from ..optimizer.parameter_management import OptimizationParameterSet


class OptimizationCampaignResult:
    """Results for an entire optimization campaign."""
    
    def __init__(self, campaign_id: str):
        self.campaign_id = campaign_id
        self.start_time = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        self.results: List[OptimizationResult] = []
        self.statistics: Optional[OptimizationStatistics] = None
        self.best_result: Optional[OptimizationResult] = None
        self.metadata: Dict[str, Any] = {}
    
    @property
    def duration(self) -> Optional[float]:
        """Campaign duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def is_complete(self) -> bool:
        """Check if campaign is complete."""
        return self.end_time is not None
    
    def add_result(self, result: OptimizationResult) -> None:
        """Add a result to the campaign."""
        self.results.append(result)
        
        # Update best result
        if (self.best_result is None or 
            (result.fitness_score > self.best_result.fitness_score and result.success)):
            self.best_result = result
    
    def complete(self) -> None:
        """Mark campaign as complete."""
        self.end_time = datetime.now(timezone.utc)
        self.statistics = self._calculate_statistics()
    
    def _calculate_statistics(self) -> OptimizationStatistics:
        """Calculate campaign statistics."""
        successful_results = [r for r in self.results if r.success]
        
        if not successful_results:
            return OptimizationStatistics(
                total_evaluations=len(self.results),
                successful_evaluations=0,
                best_fitness=float('-inf'),
                average_fitness=0.0,
                fitness_std=0.0,
                total_execution_time=sum(r.execution_time for r in self.results),
                average_execution_time=0.0
            )
        
        fitness_scores = [r.fitness_score for r in successful_results]
        execution_times = [r.execution_time for r in successful_results]
        
        return OptimizationStatistics(
            total_evaluations=len(self.results),
            successful_evaluations=len(successful_results),
            best_fitness=max(fitness_scores),
            average_fitness=statistics.mean(fitness_scores),
            fitness_std=statistics.stdev(fitness_scores) if len(fitness_scores) > 1 else 0.0,
            total_execution_time=sum(r.execution_time for r in self.results),
            average_execution_time=statistics.mean(execution_times)
        )


class ResultCoordinator(IResultCoordinator):
    """
    Coordinates optimization results from multiple workers.
    Provides real-time result collection, aggregation, and reporting.
    """
    
    def __init__(self, 
                 campaign_id: str,
                 output_folder: str = "output",
                 logger: Optional[logging.Logger] = None):
        self.campaign_id = campaign_id
        self.output_folder = Path(output_folder)
        self.logger = logger or logging.getLogger(__name__)
        
        self._campaign_result = OptimizationCampaignResult(campaign_id)
        self._result_callbacks: List[Callable[[OptimizationResult], None]] = []
        self._progress_reporters: List[IOptimizationProgressReporter] = []
        self._lock = threading.Lock()
        
        # Create output folder
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Result caching
        self._result_cache: Dict[str, OptimizationResult] = {}
        self._best_results_cache: Optional[List[OptimizationResult]] = None
        self._cache_dirty = True
    
    async def register_result(self, result: OptimizationResult) -> None:
        """Register a new optimization result."""
        try:
            with self._lock:
                # Add to campaign
                self._campaign_result.add_result(result)
                
                # Update cache
                param_key = self._get_parameter_key(result.parameter_set)
                self._result_cache[param_key] = result
                self._cache_dirty = True
                
                # Clear best results cache
                self._best_results_cache = None
            
            # Call registered callbacks
            for callback in self._result_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    self.logger.error(f"Error in result callback: {e}")
            
            # Notify progress reporters
            for reporter in self._progress_reporters:
                try:
                    reporter.report_result_received(result)
                except Exception as e:
                    self.logger.error(f"Error in progress reporter: {e}")
            
            # Auto-save periodically
            if len(self._campaign_result.results) % 10 == 0:
                await self._auto_save_results()
            
            self.logger.debug(f"Registered result with fitness {result.fitness_score}")
        
        except Exception as e:
            self.logger.error(f"Failed to register result: {e}")
            raise ResultCoordinationException(f"Failed to register result: {e}")
    
    async def get_best_results(self, count: int = 10) -> List[OptimizationResult]:
        """Get the best optimization results."""
        with self._lock:
            if self._best_results_cache is None or self._cache_dirty:
                # Get successful results and sort by fitness
                successful_results = [r for r in self._campaign_result.results if r.success]
                successful_results.sort(key=lambda x: x.fitness_score, reverse=True)
                self._best_results_cache = successful_results
                self._cache_dirty = False
            
            return self._best_results_cache[:count]
    
    async def get_all_results(self) -> List[OptimizationResult]:
        """Get all optimization results."""
        with self._lock:
            return self._campaign_result.results.copy()
    
    async def export_results(self, file_path: str, format: str = "json") -> bool:
        """Export results to file."""
        try:
            export_path = Path(file_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "json":
                return await self._export_json(export_path)
            elif format.lower() == "csv":
                return await self._export_csv(export_path)
            elif format.lower() == "excel":
                return await self._export_excel(export_path)
            else:
                raise ValueError(f"Unsupported export format: {format}")
        
        except Exception as e:
            self.logger.error(f"Failed to export results: {e}")
            return False
    
    def get_statistics(self) -> OptimizationStatistics:
        """Get optimization statistics."""
        with self._lock:
            if self._campaign_result.statistics:
                return self._campaign_result.statistics
            else:
                # Calculate real-time statistics
                return self._campaign_result._calculate_statistics()
    
    def get_campaign_result(self) -> OptimizationCampaignResult:
        """Get the complete campaign result."""
        with self._lock:
            return self._campaign_result
    
    def add_result_callback(self, callback: Callable[[OptimizationResult], None]) -> None:
        """Add a callback for new results."""
        self._result_callbacks.append(callback)
    
    def add_progress_reporter(self, reporter: IOptimizationProgressReporter) -> None:
        """Add a progress reporter."""
        self._progress_reporters.append(reporter)
    
    def complete_campaign(self) -> None:
        """Mark the campaign as complete."""
        with self._lock:
            self._campaign_result.complete()
        
        # Notify progress reporters
        for reporter in self._progress_reporters:
            try:
                reporter.report_campaign_completion(self._campaign_result.statistics)
            except Exception as e:
                self.logger.error(f"Error in progress reporter: {e}")
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time optimization metrics."""
        with self._lock:
            total_results = len(self._campaign_result.results)
            successful_results = [r for r in self._campaign_result.results if r.success]
            
            if not successful_results:
                return {
                    'total_evaluations': total_results,
                    'successful_evaluations': 0,
                    'success_rate': 0.0,
                    'best_fitness': float('-inf'),
                    'average_fitness': 0.0,
                    'elapsed_time': (datetime.now(timezone.utc) - self._campaign_result.start_time).total_seconds()
                }
            
            fitness_scores = [r.fitness_score for r in successful_results]
            
            return {
                'total_evaluations': total_results,
                'successful_evaluations': len(successful_results),
                'success_rate': len(successful_results) / total_results if total_results > 0 else 0.0,
                'best_fitness': max(fitness_scores),
                'average_fitness': statistics.mean(fitness_scores),
                'fitness_std': statistics.stdev(fitness_scores) if len(fitness_scores) > 1 else 0.0,
                'elapsed_time': (datetime.now(timezone.utc) - self._campaign_result.start_time).total_seconds(),
                'results_per_minute': len(successful_results) / max(1, (datetime.now(timezone.utc) - self._campaign_result.start_time).total_seconds() / 60)
            }
    
    def get_parameter_analysis(self) -> Dict[str, Any]:
        """Analyze parameter importance and correlations."""
        successful_results = [r for r in self._campaign_result.results if r.success]
        
        if len(successful_results) < 2:
            return {}
        
        # Group results by parameter values
        parameter_impact = defaultdict(list)
        
        for result in successful_results:
            for param_name, param_value in result.parameter_set.parameters.items():
                parameter_impact[param_name].append((param_value, result.fitness_score))
        
        # Calculate parameter statistics
        analysis = {}
        for param_name, values_and_scores in parameter_impact.items():
            if len(values_and_scores) < 2:
                continue
            
            values = [v[0] for v in values_and_scores]
            scores = [v[1] for v in values_and_scores]
            
            # Calculate correlation (simplified)
            if len(set(values)) > 1:  # Only for parameters with varying values
                try:
                    # Simple correlation calculation
                    correlation = self._calculate_correlation(values, scores)
                    analysis[param_name] = {
                        'correlation': correlation,
                        'value_range': [min(values), max(values)],
                        'best_value': values[scores.index(max(scores))],
                        'sample_count': len(values)
                    }
                except Exception as e:
                    self.logger.warning(f"Could not calculate correlation for {param_name}: {e}")
        
        return analysis
    
    async def _export_json(self, file_path: Path) -> bool:
        """Export results to JSON format."""
        try:
            export_data = {
                'campaign_id': self.campaign_id,
                'start_time': self._campaign_result.start_time.isoformat(),
                'end_time': self._campaign_result.end_time.isoformat() if self._campaign_result.end_time else None,
                'statistics': self._campaign_result.statistics.to_dict() if self._campaign_result.statistics else None,
                'results': [result.to_dict() for result in self._campaign_result.results],
                'metadata': self._campaign_result.metadata
            }
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            self.logger.info(f"Exported {len(self._campaign_result.results)} results to {file_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to export JSON: {e}")
            return False
    
    async def _export_csv(self, file_path: Path) -> bool:
        """Export results to CSV format."""
        try:
            if not self._campaign_result.results:
                return False
            
            # Get all parameter names
            all_param_names = set()
            for result in self._campaign_result.results:
                all_param_names.update(result.parameter_set.parameters.keys())
            
            # Get all metric names
            sample_metrics = self._campaign_result.results[0].performance_metrics
            metric_names = [attr for attr in dir(sample_metrics) if not attr.startswith('_')]
            
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Write header
                header = ['timestamp', 'success', 'fitness_score', 'execution_time', 'error_message']
                header.extend(sorted(all_param_names))
                header.extend(metric_names)
                writer.writerow(header)
                
                # Write data
                for result in self._campaign_result.results:
                    row = [
                        result.timestamp.isoformat(),
                        result.success,
                        result.fitness_score,
                        result.execution_time,
                        result.error_message or ''
                    ]
                    
                    # Add parameter values
                    for param_name in sorted(all_param_names):
                        row.append(result.parameter_set.parameters.get(param_name, ''))
                    
                    # Add metric values
                    for metric_name in metric_names:
                        row.append(getattr(result.performance_metrics, metric_name, ''))
                    
                    writer.writerow(row)
            
            self.logger.info(f"Exported {len(self._campaign_result.results)} results to CSV: {file_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to export CSV: {e}")
            return False
    
    async def _export_excel(self, file_path: Path) -> bool:
        """Export results to Excel format."""
        try:
            # First export to CSV, then mention Excel would require additional dependencies
            csv_path = file_path.with_suffix('.csv')
            success = await self._export_csv(csv_path)
            
            if success:
                self.logger.info(f"Exported to CSV format: {csv_path}")
                self.logger.info("Note: Excel export requires 'openpyxl' or 'xlsxwriter' package")
            
            return success
        
        except Exception as e:
            self.logger.error(f"Failed to export Excel: {e}")
            return False
    
    async def _auto_save_results(self) -> None:
        """Auto-save results periodically."""
        try:
            auto_save_path = self.output_folder / f"{self.campaign_id}_autosave.json"
            await self._export_json(auto_save_path)
        except Exception as e:
            self.logger.warning(f"Auto-save failed: {e}")
    
    def _get_parameter_key(self, parameter_set: OptimizationParameterSet) -> str:
        """Generate a unique key for a parameter set."""
        sorted_params = sorted(parameter_set.parameters.items())
        return str(hash(tuple(sorted_params)))
    
    def _calculate_correlation(self, values: List[float], scores: List[float]) -> float:
        """Calculate simple correlation coefficient."""
        if len(values) != len(scores) or len(values) < 2:
            return 0.0
        
        n = len(values)
        sum_x = sum(values)
        sum_y = sum(scores)
        sum_xy = sum(x * y for x, y in zip(values, scores))
        sum_x2 = sum(x * x for x in values)
        sum_y2 = sum(y * y for y in scores)
        
        denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5
        
        if denominator == 0:
            return 0.0
        
        correlation = (n * sum_xy - sum_x * sum_y) / denominator
        return correlation


class ProgressReporter(IOptimizationProgressReporter):
    """Default progress reporter implementation."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.start_time: Optional[datetime] = None
    
    def report_campaign_start(self, config) -> None:
        """Report optimization campaign start."""
        self.start_time = datetime.now(timezone.utc)
        self.logger.info(f"Started optimization campaign: {config.optimization_target}")
    
    def report_progress_update(self, completed: int, total: int, best_fitness: float, 
                              elapsed_time: float, estimated_completion: Optional[datetime] = None) -> None:
        """Report progress update."""
        progress_pct = (completed / total * 100) if total > 0 else 0
        
        msg = (f"Progress: {completed}/{total} ({progress_pct:.1f}%) - "
               f"Best fitness: {best_fitness:.4f} - "
               f"Elapsed: {elapsed_time:.1f}s")
        
        if estimated_completion:
            msg += f" - ETA: {estimated_completion.strftime('%H:%M:%S')}"
        
        self.logger.info(msg)
    
    def report_result_received(self, result: OptimizationResult) -> None:
        """Report new result received."""
        status = "SUCCESS" if result.success else "FAILED"
        self.logger.debug(f"Result received: {status} - Fitness: {result.fitness_score:.4f}")
    
    def report_worker_status_change(self, worker_id: str, status) -> None:
        """Report worker status change."""
        self.logger.debug(f"Worker {worker_id} status: {status}")
    
    def report_campaign_completion(self, statistics: OptimizationStatistics) -> None:
        """Report campaign completion."""
        self.logger.info(f"Optimization completed - Best fitness: {statistics.best_fitness:.4f} - "
                        f"Success rate: {statistics.successful_evaluations}/{statistics.total_evaluations}")
    
    def report_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Report error during optimization."""
        self.logger.error(f"Optimization error: {error} - Context: {context}")