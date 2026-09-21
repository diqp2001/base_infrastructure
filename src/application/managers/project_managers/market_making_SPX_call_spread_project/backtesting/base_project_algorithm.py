"""
SPX call spread algorithm — project-specific subclass.

Generic lifecycle management, portfolio tracking, performance history,
state reporting, and dependency injection live in BaseProjectAlgorithm.
Only SPX-specific logic remains here.
"""

import json
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Any

import pandas as pd

from src.application.managers.project_managers.market_making_SPX_call_spread_project.config import get_config
from src.application.services.misbuffet.algorithm.base_project_algorithm import BaseProjectAlgorithm
from src.infrastructure.models.finance.strategy_position import StrategyPositionModel

from ..strategy.market_making_strategy import Strategy
from ..strategy.risk_manager import RiskManager
from ..models.pricing_model import PricingModel
from ..models.volatility_model import VolatilityModel

logger = logging.getLogger(__name__)


class Algorithm(BaseProjectAlgorithm):
    """
    SPX call spread market making algorithm.

    Implements the SPX-specific initialize() and on_data() logic.
    All reusable helpers are inherited from BaseProjectAlgorithm.
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        # SPX-specific components
        self.pricing_engine = None
        self.volatility_model = None

        # SPX portfolio name (resolved from config during initialize)
        self.spx_portfolio_name: Optional[str] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self):
        """SPX-specific algorithm setup, called after super().initialize()."""
        super().initialize()  # sets lookback_window, train_window, models, initialized=True

        # Load project configuration
        self.config = get_config()

        # Portfolio registration
        portfolio_config = self.config.get('Portfolio', {})
        self.spx_portfolio_name = portfolio_config.get('name', 'SPX_Call_Spread_Portfolio')

        if self._entity_service:
            portfolio_entity = self.register_portfolio(portfolio_config=portfolio_config)
            if portfolio_entity:
                self.portfolio_entity = portfolio_entity
                self.log("✅ SPX portfolio registered with EntityService system")
            else:
                self.warning("⚠️ Failed to register SPX portfolio")
        else:
            self.warning("⚠️ No EntityService available - portfolio tracking disabled")

        # Universe and data settings
        self.universe = self.config['universe']
        self.bar_size_setting = self.config['bar_size_setting']
        self.duration_str = self.config['duration_str']
        self.my_securities: Dict[str, Any] = {}

        # Ensure strategy_positions table exists
        self._ensure_strategy_positions_table()

    # ------------------------------------------------------------------
    # Strategy-position DB helpers
    # ------------------------------------------------------------------

    def _get_db_session(self):
        if self._unified_portfolio_manager:
            return self._unified_portfolio_manager.portfolio_repo.session
        return None

    def _ensure_strategy_positions_table(self):
        session = self._get_db_session()
        if not session:
            return
        try:
            StrategyPositionModel.__table__.create(session.bind, checkfirst=True)
        except Exception as e:
            self.logger.warning(f"strategy_positions table create: {e}")

    def _save_strategy_position(self, position_id: str, position: dict) -> None:
        session = self._get_db_session()
        if not session:
            return
        try:
            data = json.dumps(position, default=str)
            row = session.query(StrategyPositionModel).filter_by(position_id=position_id).first()
            if row:
                row.data_json = data
                row.updated_at = datetime.now()
            else:
                row = StrategyPositionModel(
                    position_id=position_id,
                    data_json=data,
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                session.add(row)
            session.commit()
        except Exception as e:
            try:
                session.rollback()
            except Exception:
                pass
            self.logger.warning(f"_save_strategy_position failed for {position_id}: {e}")

    def _load_strategy_positions(self) -> Dict[str, Any]:
        """Load active positions from the base portfolio holding tree.

        Follows the same pattern as PortfolioService.calculate_value:
          Main portfolio → HoldingModel → PositionModel.quantity
        Only returns holdings with non-zero quantity.

        Enriches each position dict with strategy metadata (greeks, entry_price,
        max_profit, max_loss) from the strategy_positions table where available —
        so positions opened via _execute_spread_trade carry their full metadata
        while positions opened via set_holdings carry a minimal dict built from
        the base asset data (symbol, quantity, strike, expiry).
        """
        session = self._get_db_session()
        upm = self._unified_portfolio_manager
        if not session or not upm or not upm._current_portfolio_entity:
            return self.positions
        try:
            # Build an index of strategy metadata keyed by symbol for enrichment
            strategy_meta: Dict[str, Any] = {}
            try:
                for row in session.query(StrategyPositionModel).filter_by(is_active=True).all():
                    data = json.loads(row.data_json)
                    sym = data.get('symbol') or data.get('id', '')
                    strategy_meta[row.position_id] = data
                    # Also index by symbol so set_holdings positions can be enriched
                    if sym:
                        strategy_meta.setdefault(sym, data)
            except Exception:
                pass

            positions: Dict[str, Any] = {}
            self._collect_option_positions(session, positions, strategy_meta)
            return positions if positions else self.positions
        except Exception as e:
            self.logger.warning(f"_load_strategy_positions failed, falling back to in-memory: {e}")
            return self.positions

    def _collect_option_positions(
        self, session,
        out: Dict[str, Any], strategy_meta: Dict[str, Any],
    ) -> None:
        """Collect non-zero option positions from CompanyShareOptionPortfolioHoldings.

        The CompanyShareOptionPortfolio sub-portfolios are NOT linked to the main
        portfolio via a holding row (no CompanyShareOptionPortfolioPortfolioHolding
        exists), so tree-traversal from the main portfolio never reaches them.
        Instead, query CompanyShareOptionPortfolioHoldingModel directly for all
        option holdings with a non-zero position quantity.
        """
        from src.infrastructure.models.finance.holding.company_share_option_portfolio_holding import (
            CompanyShareOptionPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.position import PositionModel
        from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import CompanyShareOptionModel
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel

        rows = session.query(CompanyShareOptionPortfolioHoldingModel).all()
        for h in rows:
            if not h.position_id:
                continue
            pos = session.query(PositionModel).filter_by(id=h.position_id).first()
            if not pos or (pos.quantity or 0) == 0:
                continue

            cso_id = h.company_share_option_id
            cso = session.query(CompanyShareOptionModel).filter_by(id=cso_id).first()
            if cso is None:
                continue
            asset = session.query(FinancialAssetModel).filter_by(id=cso_id).first()
            symbol = asset.symbol if asset else str(cso_id)

            # Compute time-to-expiry from stored expiry string (format: YYYYMMDD)
            dte, tau = 30, 0.1
            if cso.expiry:
                try:
                    exp = datetime.strptime(str(cso.expiry), '%Y%m%d')
                    dte = max(0, (exp - datetime.now()).days)
                    tau = dte / 365.25
                except Exception:
                    pass

            position_id = f"cso_holding_{h.id}"
            base: Dict[str, Any] = {
                'id': position_id,
                'symbol': symbol,
                'size': int(pos.quantity),
                'position_type': str(pos.position_type),
                'strikes': {'long': float(cso.strike_price) if cso.strike_price else None},
                'days_to_expiry': dte,
                'time_to_expiry': tau,
                'greeks': {},
                'entry_price': 0.0,
                'current_price': 0.0,
                'max_profit': 0.0,
                'max_loss': 0.0,
            }

            # Enrich with strategy metadata (greeks, entry_price, etc.) where available
            enrichment = strategy_meta.get(position_id) or strategy_meta.get(symbol, {})
            if enrichment:
                base.update({k: v for k, v in enrichment.items()
                              if k not in ('id', 'symbol', 'size', 'position_type')})

            out[position_id] = base

    def _load_position_market_data(
        self,
        positions: Dict[str, Any],
        current_date: datetime,
    ) -> Dict[str, Dict[str, Any]]:
        """Resolve live factor values for each option symbol in `positions`.

        Queries delta, gamma, vega, implied_vol, and mid_price via
        FactorValueResolutionService at `current_date`.  Results are keyed by
        option symbol so the caller can merge them back into position dicts.

        Returns:
            {symbol: {'greeks': {delta, gamma, vega, implied_vol}, 'current_price': float}}
        """
        from src.application.services.data.entities.factor import FactorValueResolutionService

        factory = self.repository_factory
        if not factory:
            return {}

        fvrs = FactorValueResolutionService(factory=factory)
        cso_repo = factory.get_local_repository('CompanyShareOption')
        if not cso_repo:
            return {}

        # Load one representative factor entity for each greek we care about.
        FACTOR_REPO_KEYS: Dict[str, str] = {
            'delta': 'CompanyShareOptionDeltaFactor',
            'gamma': 'CompanyShareOptionGammaFactor',
            'vega': 'CompanyShareOptionVegaFactor',
            'implied_vol': 'CompanyShareOptionImpliedVolFactor',
            'current_price': 'CompanyShareOptionMidPriceFactor',
        }
        factor_entities: Dict[str, Any] = {}
        for key, repo_key in FACTOR_REPO_KEYS.items():
            try:
                repo = factory.get_local_repository(repo_key)
                if repo:
                    all_factors = repo.get_all()
                    if all_factors:
                        factor_entities[key] = all_factors[0]
            except Exception as e:
                self.logger.debug("Could not load factor repo %s: %s", repo_key, e)

        if not factor_entities:
            return {}

        result: Dict[str, Dict[str, Any]] = {}
        seen_symbols: set = set()

        for pos in positions.values():
            symbol = pos.get('symbol')
            if not symbol or symbol in seen_symbols:
                continue
            seen_symbols.add(symbol)

            try:
                cso_entity = cso_repo.get_by_symbol(symbol)
            except Exception as e:
                self.logger.debug("CSO entity lookup failed for %s: %s", symbol, e)
                continue
            if cso_entity is None:
                continue

            greeks: Dict[str, float] = {}
            current_price: Optional[float] = None

            for key, factor_entity in factor_entities.items():
                try:
                    fv = fvrs.resolve_factor_value(
                        factor_entity=factor_entity,
                        entity=cso_entity,
                        time_date=current_date,
                    )
                    if fv is not None:
                        val = float(fv.value)
                        if key == 'current_price':
                            current_price = val
                        else:
                            greeks[key] = val
                except Exception as e:
                    self.logger.debug("Factor %s resolution failed for %s: %s", key, symbol, e)

            result[symbol] = {'greeks': greeks, 'current_price': current_price}

        return result

    def _close_strategy_position(self, position_id: str) -> None:
        session = self._get_db_session()
        if not session:
            return
        try:
            row = session.query(StrategyPositionModel).filter_by(position_id=position_id).first()
            if row:
                row.is_active = False
                row.updated_at = datetime.now()
                session.commit()
        except Exception as e:
            try:
                session.rollback()
            except Exception:
                pass
            self.logger.warning(f"_close_strategy_position failed for {position_id}: {e}")

    # ------------------------------------------------------------------
    # Trading logic
    # ------------------------------------------------------------------

    def on_data(self, data):
        """
        Main algorithm callback — SPX call spread market making logic.

        Args:
            data: Market data (Slice or dict) for the current bar
        """
        try:
            if not self.initialized:
                self.logger.warning("Algorithm not initialized")
                return

            # Run model training pipeline for data preparation
            if hasattr(self, 'trainer') and self.trainer:
                self.logger.info("🚀 Running model training pipeline for data preparation...")

                training_result = self.trainer.train_complete_pipeline(
                    tickers=self.universe,
                    model_type='pricing',
                    seeds=[42, 123],
                    data=data,
                )

                if training_result.get('error'):
                    self.logger.error(f"❌ Model training failed: {training_result['error']}")
                    return

                self._model_trained = True
                self.logger.info("✅ Model training pipeline completed successfully")
            if self._unified_portfolio_manager:#and if 'SPY  281215C00765000' position equal 0 or not existent
                            self._unified_portfolio_manager.set_holdings(
                                {'SPY   281215C00765000': -0.2},
                                data=data,
                            )
            # Manage open positions (P&L, exits, aggregate delta hedge) — load from DB
            db_positions = self._load_strategy_positions()

            # Enrich each position's greeks and price with resolved factor values
            current_time: datetime = data.get('time', datetime.now()) if isinstance(data, dict) else datetime.now()
            position_market_data = self._load_position_market_data(db_positions, current_time)
            for pos in db_positions.values():
                sym = pos.get('symbol')
                if sym and sym in position_market_data:
                    mdata = position_market_data[sym]
                    pos.setdefault('greeks', {}).update(mdata.get('greeks', {}))
                    if mdata.get('current_price') is not None:
                        pos['current_price'] = mdata['current_price']

            mgmt = self.strategy.manage_existing_positions(positions=db_positions, market_data=data, position_market_data=position_market_data)
            for pid in mgmt.get('exited_position_ids', []):
                self._close_strategy_position(pid)
                self.positions.pop(pid, None)

            # Execute SPY delta hedge when the aggregate portfolio delta is outside the band
            portfolio_hedge = mgmt.get('portfolio_hedge', {})
            if portfolio_hedge.get('should_hedge') and self._unified_portfolio_manager:
                # Get SPY spot from Slice.bars (Symbol keys; equity has no spaces, options do)
                _spy_bar = next(
                    (bar for sym, bar in getattr(data, 'bars', {}).items()
                     if str(getattr(sym, 'value', sym)) == 'SPY'),
                    None,
                )
                spy_price = float(_spy_bar.close) if _spy_bar is not None else 500.0
                pv = self.portfolio_value or 1.0
                target_hedge_delta = float(portfolio_hedge['target_hedge_delta'])
                # SPY shares needed = target_delta; weight = (shares × SPY_price) / portfolio_value
                spy_weight = (target_hedge_delta * spy_price) / pv
                self.logger.info(
                    "Delta hedge: target_delta=%.4f spy=%.2f pv=%.0f -> SPY weight=%.4f (%s)",
                    target_hedge_delta, spy_price, pv, spy_weight,
                    portfolio_hedge.get('hedge_direction', ''),
                )
                self._unified_portfolio_manager.set_holdings({'SPY': spy_weight}, data=data)
            random_pct = random.random()
            # if self._unified_portfolio_manager:
            #     self._unified_portfolio_manager.set_holdings(
            #         {'AAPL': random_pct, 'MSFT': 1.0 - random_pct},
            #         data=data,
            #     )

            self._update_portfolio_value(data)
            self._update_performance_tracking(data)

            if self._is_end_of_day(data):
                self._log_daily_summary()

        except Exception as e:
            self.logger.error(f"Error in on_data: {e}")

    # ------------------------------------------------------------------
    # SPX-specific helpers
    # ------------------------------------------------------------------

    def _setup_factor_data_for_ticker(self, ticker: str, current_time: datetime) -> pd.DataFrame:
        """Set up factor-based data for a specific ticker via the factor manager."""
        try:
            self.log(f"Setting up factor data for {ticker}...")

            if hasattr(self, 'factor_manager') and self.factor_manager:
                self.log(f"Using factor manager for {ticker} data...")

                try:
                    self.factor_manager._ensure_entities_exist([ticker])
                except Exception as e:
                    self.log(f"Warning: Could not ensure entities for {ticker}: {e}")

                try:
                    factor_data = self.factor_manager.get_factor_data_for_training(
                        tickers=[ticker],
                        factor_groups=['price', 'momentum', 'technical'],
                        lookback_days=self.train_window,
                        end_date=current_time,
                    )

                    if factor_data is not None and not factor_data.empty:
                        self.log(f"Retrieved {len(factor_data)} factor data points for {ticker}")
                        df = self._convert_factor_data_to_training_format(factor_data, ticker)
                        if not df.empty:
                            return df
                    else:
                        self.log(f"No factor data available for {ticker}, falling back to basic features")
                except Exception as e:
                    self.log(f"Error getting factor data for {ticker}: {e}")

        except Exception as e:
            self.log(f"Error setting up factor data for {ticker}: {str(e)}")
            return pd.DataFrame()

    def _verify_and_import_data(self) -> Dict[str, Any]:
        """Verify SPX data exists in the DB and import via IBKR if missing."""
        try:
            if hasattr(self, 'trainer') and hasattr(self.trainer, 'database_service'):
                data_loader = self.trainer.data_loader

                data_check = data_loader.check_spx_data_availability()
                has_data = data_check.get('has_spx_data', False)

                import_results = None

                if not has_data:
                    self.logger.info("💾 Importing SPX historical data via IBKR...")
                    import_results = data_loader.import_spx_historical_data()
                    has_data = import_results.get('success', False)

                return {
                    'success': has_data,
                    'data_check': data_check,
                    'import_results': import_results,
                    'data_available': has_data,
                }
            else:
                self.logger.warning("⚠️ No database service available for data verification")
                return {'success': False, 'error': 'No database service available'}

        except Exception as e:
            self.logger.error(f"Error verifying SPX data: {e}")
            return {'success': False, 'error': str(e)}

    def _generate_new_opportunities(
        self,
        data: Dict[str, Any],
        market_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate new call spread opportunities from the strategy."""
        try:
            spx_price = data.get('spx_price', 4500)

            option_chain = {
                'expiries': ['2024-01-19', '2024-01-26', '2024-02-02'],
                'strikes': list(range(int(spx_price - 100), int(spx_price + 100), 5)),
            }

            return self.strategy.generate_spread_opportunities(spx_price, option_chain, market_analysis)

        except Exception as e:
            self.logger.error(f"Error generating opportunities: {e}")
            return []

    def _evaluate_and_execute_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        data: Dict[str, Any],
    ):
        """Evaluate and execute the top-scored spread opportunities."""
        try:
            for opportunity in opportunities[:5]:
                entry_eval = self.strategy.evaluate_spread_entry(opportunity)

                if not entry_eval.get('should_enter', False):
                    continue

                risk_check = self.risk_manager.check_position_limits(opportunity, self.positions)

                if not risk_check.get('position_approved', False):
                    self.logger.info(f"Position rejected by risk manager: {risk_check.get('violations', [])}")
                    continue

                self._execute_spread_trade(opportunity, entry_eval, data)

        except Exception as e:
            self.logger.error(f"Error evaluating and executing opportunities: {e}")

    def _execute_spread_trade(
        self,
        opportunity: Dict[str, Any],
        entry_eval: Dict[str, Any],
        data: Dict[str, Any],
    ):
        """Execute a call spread trade and record it in positions."""
        try:
            position_size = entry_eval.get('recommended_position_size', 1)

            spread_pricing = entry_eval.get('spread_pricing', {})
            max_loss = spread_pricing.get('max_loss', 0)
            required_capital = max_loss * position_size * 100  # SPX multiplier

            if required_capital > self.cash * 0.1:
                position_size = max(1, int(self.cash * 0.1 / (max_loss * 100)))

            if self.cash < required_capital:
                self.logger.warning(f"Insufficient capital: need {required_capital}, have {self.cash}")
                return

            long_option_ticket = self.market_order(
                opportunity.get('long_option_symbol', 'SPX'),
                position_size,
                tag="SPX_SPREAD_LONG",
            )
            short_option_ticket = self.market_order(
                opportunity.get('short_option_symbol', 'SPX'),
                -position_size,
                tag="SPX_SPREAD_SHORT",
            )

            position_id = f"spread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            position = {
                'id': position_id,
                'type': opportunity.get('spread_type'),
                'strikes': {
                    'long': opportunity.get('long_strike'),
                    'short': opportunity.get('short_strike'),
                },
                'size': position_size,
                'entry_date': data.get('date', datetime.now()),
                'entry_price': spread_pricing.get('net_price', 0),
                'max_profit': spread_pricing.get('max_profit', 0),
                'max_loss': spread_pricing.get('max_loss', 0),
                'greeks': spread_pricing.get('greeks', {}),
                'underlying_price': data.get('spx_price', 4500),
                'expiry_date': opportunity.get('expiry_date'),
                'required_capital': required_capital,
                'current_value': 0,
                'long_order_id': long_option_ticket.order_id if long_option_ticket else None,
                'short_order_id': short_option_ticket.order_id if short_option_ticket else None,
            }

            self.positions[position_id] = position
            self._save_strategy_position(position_id, position)
            self.cash -= required_capital
            self.total_trades += 1

            self.logger.info(f"✅ Executed {position['type']} spread: {position['strikes']}, size: {position_size}")

        except Exception as e:
            self.logger.error(f"Error executing spread trade: {e}")

    def _calculate_position_value(self, position: Dict[str, Any], data: Dict[str, Any]) -> float:
        """Simplified P&L estimate for a spread position (time decay + directional factor)."""
        try:
            entry_date = position.get('entry_date', datetime.now())
            current_date = data.get('date', datetime.now())

            if isinstance(entry_date, str):
                entry_date = datetime.fromisoformat(entry_date)
            if isinstance(current_date, str):
                current_date = datetime.fromisoformat(current_date)

            days_held = (current_date - entry_date).days
            max_profit = position.get('max_profit', 0)
            max_loss = position.get('max_loss', 0)

            if position.get('type', '').startswith('bull'):
                spx_change = (data.get('spx_price', 4500) - position.get('underlying_price', 4500)) / position.get('underlying_price', 4500)
                pnl_factor = min(1, max(-1, spx_change * 5))
            else:
                spx_change = (position.get('underlying_price', 4500) - data.get('spx_price', 4500)) / position.get('underlying_price', 4500)
                pnl_factor = min(1, max(-1, spx_change * 5))

            time_decay_factor = max(0, 1 - (days_held / 30))

            if pnl_factor > 0:
                current_value = max_profit * pnl_factor * time_decay_factor
            else:
                current_value = max_loss * pnl_factor

            return current_value * position.get('size', 1)

        except Exception as e:
            self.logger.error(f"Error calculating position value: {e}")
            return 0.0
