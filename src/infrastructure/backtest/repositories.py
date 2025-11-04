"""
Repository implementations for backtest tracking system.

Concrete implementations of domain repositories using SQLAlchemy
for data persistence and retrieval operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, and_, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError
import json
import logging
from decimal import Decimal

from src.domain.backtest.config import BacktestConfig
from src.domain.backtest.result import BacktestResult, TradeRecord, PerformanceMetrics, EquityCurve
from src.domain.backtest.dataset import BacktestDataset
from .models import (
    Base, BacktestExperimentModel, BacktestConfigModel, BacktestResultModel,
    TradeRecordModel, EquityCurvePointModel, BacktestDatasetModel,
    BacktestArtifactModel, BacktestComparisonModel
)

logger = logging.getLogger(__name__)


class BacktestRepository:
    """
    Repository for managing backtest experiments, configurations, and results.
    
    Provides high-level operations for storing and retrieving backtest data
    while abstracting the underlying SQLAlchemy implementation details.
    """
    
    def __init__(self, database_url: str = "sqlite:///backtest_tracking.db"):
        """Initialize repository with database connection."""
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    # Experiment Management
    
    def create_experiment(self, name: str, description: str = "", 
                         created_by: str = "system", tags: Dict[str, str] = None) -> str:
        """Create a new experiment and return experiment_id."""
        from uuid import uuid4
        
        experiment_id = str(uuid4())
        
        with self.get_session() as session:
            try:
                experiment = BacktestExperimentModel(
                    experiment_id=experiment_id,
                    name=name,
                    description=description,
                    created_by=created_by,
                    tags=tags or {}
                )
                session.add(experiment)
                session.commit()
                logger.info(f"Created experiment: {name} ({experiment_id})")
                return experiment_id
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error creating experiment: {e}")
                raise
    
    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment by ID."""
        with self.get_session() as session:
            experiment = session.query(BacktestExperimentModel).filter(
                BacktestExperimentModel.experiment_id == experiment_id
            ).first()
            
            if experiment:
                return {
                    'experiment_id': experiment.experiment_id,
                    'name': experiment.name,
                    'description': experiment.description,
                    'created_at': experiment.created_at,
                    'created_by': experiment.created_by,
                    'tags': experiment.tags or {}
                }
        return None
    
    def list_experiments(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all experiments."""
        with self.get_session() as session:
            experiments = session.query(BacktestExperimentModel).order_by(
                desc(BacktestExperimentModel.created_at)
            ).limit(limit).all()
            
            return [
                {
                    'experiment_id': exp.experiment_id,
                    'name': exp.name,
                    'description': exp.description,
                    'created_at': exp.created_at,
                    'created_by': exp.created_by,
                    'tags': exp.tags or {}
                }
                for exp in experiments
            ]
    
    # Configuration Management
    
    def store_config(self, config: BacktestConfig) -> str:
        """Store backtest configuration and return config_id."""
        with self.get_session() as session:
            try:
                config_model = BacktestConfigModel(
                    config_id=config.config_id,
                    experiment_id=config.experiment_name,  # Using experiment_name as ID
                    run_name=config.run_name,
                    algorithm_name=config.algorithm_name,
                    algorithm_version=config.algorithm_version,
                    strategy_params=config.strategy_params,
                    start_date=config.start_date,
                    end_date=config.end_date,
                    benchmark_period=config.benchmark_period,
                    universe=config.universe,
                    universe_filter=config.universe_filter,
                    initial_capital=str(config.initial_capital),
                    position_sizing=config.position_sizing,
                    max_positions=config.max_positions,
                    max_position_size=str(config.max_position_size),
                    stop_loss=str(config.stop_loss) if config.stop_loss else None,
                    take_profit=str(config.take_profit) if config.take_profit else None,
                    var_limit=str(config.var_limit) if config.var_limit else None,
                    commission_rate=str(config.commission_rate),
                    slippage_model=config.slippage_model,
                    market_impact_factor=str(config.market_impact_factor),
                    data_frequency=config.data_frequency,
                    lookback_window=config.lookback_window,
                    warmup_period=config.warmup_period,
                    factors=config.factors,
                    feature_selection=config.feature_selection,
                    model_type=config.model_type,
                    model_params=config.model_params,
                    training_frequency=config.training_frequency,
                    random_seed=config.random_seed,
                    parallel_processing=config.parallel_processing,
                    num_cores=config.num_cores,
                    created_at=config.created_at,
                    created_by=config.created_by,
                    tags=config.tags,
                    description=config.description
                )
                session.add(config_model)
                session.commit()
                logger.info(f"Stored config: {config.config_id}")
                return config.config_id
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error storing config: {e}")
                raise
    
    def get_config(self, config_id: str) -> Optional[BacktestConfig]:
        """Get configuration by ID."""
        with self.get_session() as session:
            config_model = session.query(BacktestConfigModel).filter(
                BacktestConfigModel.config_id == config_id
            ).first()
            
            if config_model:
                return self._model_to_config(config_model)
        return None
    
    def _model_to_config(self, model: BacktestConfigModel) -> BacktestConfig:
        """Convert SQLAlchemy model to domain object."""
        return BacktestConfig(
            config_id=model.config_id,
            experiment_name=model.experiment_id,
            run_name=model.run_name,
            algorithm_name=model.algorithm_name,
            algorithm_version=model.algorithm_version,
            strategy_params=model.strategy_params or {},
            start_date=model.start_date,
            end_date=model.end_date,
            benchmark_period=model.benchmark_period,
            universe=model.universe or [],
            universe_filter=model.universe_filter,
            initial_capital=Decimal(model.initial_capital) if model.initial_capital else Decimal("100000"),
            position_sizing=model.position_sizing,
            max_positions=model.max_positions,
            max_position_size=Decimal(model.max_position_size) if model.max_position_size else Decimal("0.2"),
            stop_loss=Decimal(model.stop_loss) if model.stop_loss else None,
            take_profit=Decimal(model.take_profit) if model.take_profit else None,
            var_limit=Decimal(model.var_limit) if model.var_limit else None,
            commission_rate=Decimal(model.commission_rate) if model.commission_rate else Decimal("0.001"),
            slippage_model=model.slippage_model,
            market_impact_factor=Decimal(model.market_impact_factor) if model.market_impact_factor else Decimal("0.0001"),
            data_frequency=model.data_frequency,
            lookback_window=model.lookback_window,
            warmup_period=model.warmup_period,
            factors=model.factors or [],
            feature_selection=model.feature_selection,
            model_type=model.model_type,
            model_params=model.model_params or {},
            training_frequency=model.training_frequency,
            random_seed=model.random_seed,
            parallel_processing=model.parallel_processing,
            num_cores=model.num_cores,
            created_at=model.created_at,
            created_by=model.created_by,
            tags=model.tags or {},
            description=model.description or ""
        )
    
    # Result Management
    
    def store_result(self, result: BacktestResult) -> str:
        """Store backtest result and return result_id."""
        with self.get_session() as session:
            try:
                # Store main result
                result_model = BacktestResultModel(
                    result_id=result.result_id,
                    config_id=result.config_id,
                    experiment_id=result.experiment_name,
                    run_name=result.run_name,
                    start_time=result.start_time,
                    end_time=result.end_time,
                    execution_duration_seconds=result.execution_duration_seconds,
                    status=result.status,
                    error_message=result.error_message,
                    created_by=result.created_by,
                    tags=result.tags,
                    notes=result.notes
                )
                
                # Add performance metrics if available
                if result.performance_metrics:
                    pm = result.performance_metrics
                    result_model.total_return = str(pm.total_return)
                    result_model.total_return_pct = str(pm.total_return_pct)
                    result_model.annualized_return = str(pm.annualized_return)
                    result_model.volatility = str(pm.volatility)
                    result_model.sharpe_ratio = str(pm.sharpe_ratio)
                    result_model.sortino_ratio = str(pm.sortino_ratio)
                    result_model.max_drawdown = str(pm.max_drawdown)
                    result_model.max_drawdown_pct = str(pm.max_drawdown_pct)
                    result_model.total_trades = pm.total_trades
                    result_model.winning_trades = pm.winning_trades
                    result_model.losing_trades = pm.losing_trades
                    result_model.win_rate = str(pm.win_rate)
                    result_model.profit_factor = str(pm.profit_factor)
                    result_model.var_95 = str(pm.var_95)
                    result_model.cvar_95 = str(pm.cvar_95)
                    result_model.calmar_ratio = str(pm.calmar_ratio)
                    
                    # Benchmark metrics
                    if pm.benchmark_return:
                        result_model.benchmark_return = str(pm.benchmark_return)
                    if pm.alpha:
                        result_model.alpha = str(pm.alpha)
                    if pm.beta:
                        result_model.beta = str(pm.beta)
                    if pm.information_ratio:
                        result_model.information_ratio = str(pm.information_ratio)
                
                # Store complex data as JSON
                result_model.factor_exposures = result.factor_exposures
                result_model.sector_attribution = result.sector_attribution
                result_model.monthly_returns = result.monthly_returns
                result_model.risk_metrics = result.risk_metrics
                result_model.model_metrics = result.model_metrics
                result_model.feature_importance = result.feature_importance
                result_model.system_info = result.system_info
                result_model.resource_usage = result.resource_usage
                
                session.add(result_model)
                
                # Store trades
                for trade in result.trades:
                    trade_model = TradeRecordModel(
                        trade_id=trade.trade_id,
                        result_id=result.result_id,
                        symbol=trade.symbol,
                        entry_time=trade.entry_time,
                        exit_time=trade.exit_time,
                        side=trade.side,
                        quantity=trade.quantity,
                        entry_price=str(trade.entry_price),
                        exit_price=str(trade.exit_price) if trade.exit_price else None,
                        pnl=str(trade.pnl) if trade.pnl else None,
                        pnl_pct=str(trade.pnl_pct) if trade.pnl_pct else None,
                        entry_commission=str(trade.entry_commission),
                        exit_commission=str(trade.exit_commission),
                        slippage=str(trade.slippage),
                        entry_signal=trade.entry_signal,
                        exit_signal=trade.exit_signal,
                        tags=trade.tags
                    )
                    session.add(trade_model)
                
                # Store equity curve
                if result.equity_curve:
                    ec = result.equity_curve
                    for i, timestamp in enumerate(ec.timestamps):
                        curve_point = EquityCurvePointModel(
                            result_id=result.result_id,
                            timestamp=timestamp,
                            portfolio_value=str(ec.portfolio_values[i]),
                            daily_return=str(ec.daily_returns[i]) if i < len(ec.daily_returns) else None,
                            drawdown=str(ec.drawdowns[i]) if i < len(ec.drawdowns) else None,
                            gross_exposure=str(ec.gross_exposure[i]) if i < len(ec.gross_exposure) else None,
                            net_exposure=str(ec.net_exposure[i]) if i < len(ec.net_exposure) else None,
                            num_positions=ec.num_positions[i] if i < len(ec.num_positions) else None
                        )
                        session.add(curve_point)
                
                session.commit()
                logger.info(f"Stored result: {result.result_id}")
                return result.result_id
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error storing result: {e}")
                raise
    
    def get_result(self, result_id: str) -> Optional[BacktestResult]:
        """Get result by ID."""
        with self.get_session() as session:
            result_model = session.query(BacktestResultModel).filter(
                BacktestResultModel.result_id == result_id
            ).first()
            
            if result_model:
                return self._model_to_result(result_model, session)
        return None
    
    def _model_to_result(self, model: BacktestResultModel, session: Session) -> BacktestResult:
        """Convert SQLAlchemy model to domain object."""
        result = BacktestResult(
            result_id=model.result_id,
            config_id=model.config_id,
            experiment_name=model.experiment_id,
            run_name=model.run_name,
            start_time=model.start_time,
            end_time=model.end_time,
            execution_duration_seconds=model.execution_duration_seconds or 0.0,
            status=model.status,
            error_message=model.error_message,
            created_by=model.created_by,
            tags=model.tags or {},
            notes=model.notes or ""
        )
        
        # Load performance metrics if available
        if model.total_return:
            result.performance_metrics = PerformanceMetrics(
                total_return=Decimal(model.total_return),
                total_return_pct=Decimal(model.total_return_pct or "0"),
                annualized_return=Decimal(model.annualized_return or "0"),
                volatility=Decimal(model.volatility or "0"),
                sharpe_ratio=Decimal(model.sharpe_ratio or "0"),
                sortino_ratio=Decimal(model.sortino_ratio or "0"),
                max_drawdown=Decimal(model.max_drawdown or "0"),
                max_drawdown_pct=Decimal(model.max_drawdown_pct or "0"),
                total_trades=model.total_trades or 0,
                winning_trades=model.winning_trades or 0,
                losing_trades=model.losing_trades or 0,
                win_rate=Decimal(model.win_rate or "0"),
                profit_factor=Decimal(model.profit_factor or "0"),
                average_trade=Decimal("0"),  # Would be calculated
                average_win=Decimal("0"),    # Would be calculated
                average_loss=Decimal("0"),   # Would be calculated
                largest_win=Decimal("0"),    # Would be calculated
                largest_loss=Decimal("0"),   # Would be calculated
                calmar_ratio=Decimal(model.calmar_ratio or "0"),
                var_95=Decimal(model.var_95 or "0"),
                cvar_95=Decimal(model.cvar_95 or "0"),
                benchmark_return=Decimal(model.benchmark_return) if model.benchmark_return else None,
                alpha=Decimal(model.alpha) if model.alpha else None,
                beta=Decimal(model.beta) if model.beta else None,
                information_ratio=Decimal(model.information_ratio) if model.information_ratio else None
            )
        
        # Load complex data
        result.factor_exposures = model.factor_exposures or {}
        result.sector_attribution = model.sector_attribution or {}
        result.monthly_returns = model.monthly_returns or {}
        result.risk_metrics = model.risk_metrics or {}
        result.model_metrics = model.model_metrics or {}
        result.feature_importance = model.feature_importance or {}
        result.system_info = model.system_info or {}
        result.resource_usage = model.resource_usage or {}
        
        # Load trades
        trades = session.query(TradeRecordModel).filter(
            TradeRecordModel.result_id == result.result_id
        ).all()
        
        for trade_model in trades:
            trade = TradeRecord(
                trade_id=trade_model.trade_id,
                symbol=trade_model.symbol,
                entry_time=trade_model.entry_time,
                exit_time=trade_model.exit_time,
                side=trade_model.side,
                quantity=trade_model.quantity,
                entry_price=Decimal(trade_model.entry_price),
                exit_price=Decimal(trade_model.exit_price) if trade_model.exit_price else None,
                pnl=Decimal(trade_model.pnl) if trade_model.pnl else None,
                pnl_pct=Decimal(trade_model.pnl_pct) if trade_model.pnl_pct else None,
                entry_commission=Decimal(trade_model.entry_commission),
                exit_commission=Decimal(trade_model.exit_commission),
                slippage=Decimal(trade_model.slippage),
                entry_signal=trade_model.entry_signal or "",
                exit_signal=trade_model.exit_signal or "",
                tags=trade_model.tags or {}
            )
            result.trades.append(trade)
        
        # Load equity curve
        curve_points = session.query(EquityCurvePointModel).filter(
            EquityCurvePointModel.result_id == result.result_id
        ).order_by(EquityCurvePointModel.timestamp).all()
        
        if curve_points:
            timestamps = [cp.timestamp for cp in curve_points]
            portfolio_values = [Decimal(cp.portfolio_value) for cp in curve_points]
            daily_returns = [Decimal(cp.daily_return) if cp.daily_return else Decimal("0") for cp in curve_points]
            drawdowns = [Decimal(cp.drawdown) if cp.drawdown else Decimal("0") for cp in curve_points]
            
            result.equity_curve = EquityCurve(
                timestamps=timestamps,
                portfolio_values=portfolio_values,
                daily_returns=daily_returns,
                drawdowns=drawdowns
            )
            
            # Add optional fields if available
            if curve_points[0].gross_exposure:
                result.equity_curve.gross_exposure = [
                    Decimal(cp.gross_exposure) if cp.gross_exposure else Decimal("0") 
                    for cp in curve_points
                ]
            if curve_points[0].net_exposure:
                result.equity_curve.net_exposure = [
                    Decimal(cp.net_exposure) if cp.net_exposure else Decimal("0") 
                    for cp in curve_points
                ]
            if curve_points[0].num_positions is not None:
                result.equity_curve.num_positions = [
                    cp.num_positions if cp.num_positions is not None else 0 
                    for cp in curve_points
                ]
        
        return result
    
    def list_results(self, experiment_name: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List results, optionally filtered by experiment."""
        with self.get_session() as session:
            query = session.query(BacktestResultModel)
            
            if experiment_name:
                query = query.filter(BacktestResultModel.experiment_id == experiment_name)
            
            results = query.order_by(desc(BacktestResultModel.start_time)).limit(limit).all()
            
            return [
                {
                    'result_id': r.result_id,
                    'experiment_name': r.experiment_id,
                    'run_name': r.run_name,
                    'config_id': r.config_id,
                    'start_time': r.start_time,
                    'end_time': r.end_time,
                    'duration_seconds': r.execution_duration_seconds,
                    'status': r.status,
                    'total_return_pct': r.total_return_pct,
                    'sharpe_ratio': r.sharpe_ratio,
                    'max_drawdown_pct': r.max_drawdown_pct,
                    'total_trades': r.total_trades,
                    'created_by': r.created_by,
                    'tags': r.tags
                }
                for r in results
            ]
    
    def delete_result(self, result_id: str) -> bool:
        """Delete a result and all associated data."""
        with self.get_session() as session:
            try:
                # Delete in order: equity curve, trades, then result
                session.query(EquityCurvePointModel).filter(
                    EquityCurvePointModel.result_id == result_id
                ).delete()
                
                session.query(TradeRecordModel).filter(
                    TradeRecordModel.result_id == result_id
                ).delete()
                
                deleted_count = session.query(BacktestResultModel).filter(
                    BacktestResultModel.result_id == result_id
                ).delete()
                
                session.commit()
                logger.info(f"Deleted result: {result_id}")
                return deleted_count > 0
                
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Error deleting result: {e}")
                raise
    
    def compare_results(self, result_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple results and return comparative analysis."""
        with self.get_session() as session:
            results = session.query(BacktestResultModel).filter(
                BacktestResultModel.result_id.in_(result_ids)
            ).all()
            
            if len(results) < 2:
                return {"error": "At least 2 results required for comparison"}
            
            comparison_data = {
                'result_ids': result_ids,
                'results_found': len(results),
                'metrics_comparison': {},
                'performance_ranking': []
            }
            
            # Compare key metrics
            metrics = ['total_return_pct', 'sharpe_ratio', 'max_drawdown_pct', 'win_rate']
            
            for metric in metrics:
                comparison_data['metrics_comparison'][metric] = {}
                for result in results:
                    value = getattr(result, metric)
                    if value:
                        comparison_data['metrics_comparison'][metric][result.result_id] = value
            
            # Simple ranking by Sharpe ratio
            ranked_results = sorted(results, 
                                  key=lambda r: float(r.sharpe_ratio) if r.sharpe_ratio else 0, 
                                  reverse=True)
            
            comparison_data['performance_ranking'] = [
                {
                    'result_id': r.result_id,
                    'run_name': r.run_name,
                    'sharpe_ratio': r.sharpe_ratio,
                    'total_return_pct': r.total_return_pct
                }
                for r in ranked_results
            ]
            
            return comparison_data
    
    def get_result_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics across all results."""
        with self.get_session() as session:
            total_results = session.query(BacktestResultModel).count()
            successful_results = session.query(BacktestResultModel).filter(
                BacktestResultModel.status == 'completed'
            ).count()
            
            # Get latest results
            recent_results = session.query(BacktestResultModel).order_by(
                desc(BacktestResultModel.start_time)
            ).limit(10).all()
            
            return {
                'total_results': total_results,
                'successful_results': successful_results,
                'success_rate': successful_results / total_results if total_results > 0 else 0,
                'recent_results': [
                    {
                        'result_id': r.result_id,
                        'experiment_name': r.experiment_id,
                        'run_name': r.run_name,
                        'start_time': r.start_time,
                        'status': r.status,
                        'total_return_pct': r.total_return_pct
                    }
                    for r in recent_results
                ]
            }