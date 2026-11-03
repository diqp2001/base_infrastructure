"""
Configuration for the LIVE deployment of the intraday Spatio-Temporal Momentum strategy (10-minute bars).

Same strategy, universe (26 US banks), features, model and windows as spatio_temporal_momentum_project_10m — a
copy wired to the broker through build_live_stack (P.06.01). The research parameters are identical; what differs:

* the engine clock follows the wall clock (LiveClock): one decision every 10 minutes, after the bar has closed;
* orders go to IBKR (InteractiveBrokersBroker) through the order ledger, start-up recovery, reconciliation and the
  pre-trade gate (``LIVE``: account, strategy, risk limits, paper price source);
* its own book, signals, models and results, so the live run never mixes with the 10m backtests: portfolio
  ``Spatio_Temporal_Momentum_10m_Live_Portfolio`` (resumed across restarts, never reset), signal factor
  ``spatio_temporal_momentum_signal_10m_banks_live``, feature / ML prefixes ``stm10mlive_``, universe
  ``stm_us_banks_10m_live``, results ``results/spatio_temporal_momentum_10m_live/``,
  models ``weights/spatio_temporal_momentum_10m_live/``;
* the history window is rolling (``history_calendar_days`` before today) instead of a fixed research start;
* the last decision of a session is 15:50 (bar 15:40 closed), so no market order is sent at the 16:00 close.

Research parameters live in the ``stm`` section and are turned into an STMConfiguration by
``build_stm_configuration``. Top-level keys keep the names the Misbuffet runner reads.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.data.bank_universe import (
    BANK_UNIVERSE_TICKERS,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
    STMFeatureConfig,
    STMModelConfig,
    STMTrainingConfig,
    STMUniverseConfig,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import (
    bars_per_session,
    frequency,
    periods_per_year,
)
from src.application.services.data.entities.factor.factor_library.factor_definition_config import FACTOR_LIBRARY
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.order.pre_trade_risk import RiskLimits
from src.domain.entities.finance.portfolio.portfolio import Portfolio

BASE_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
CONFIG_TEST = {
    'DB_TYPE': 'sql_server',
    'DB_PATH': BASE_PROJECT_ROOT / 'base_infrastructure.db',
    'CONNECTION_STRING': f'sqlite:///{BASE_PROJECT_ROOT}/base_infrastructure.db',
}

# ── Universe: 26 US banks (owner's list, 2026-10-26), the 10m project's research universe ─────────────────────
STM_UNIVERSE_NAME = 'stm_us_banks_10m_live'
STM_N_PER_SECTOR = None       # explicit list, no sampling
STM_UNIVERSE_SEED = None
STM_TICKERS: List[str] = list(BANK_UNIVERSE_TICKERS)
STM_SIGNAL_FACTOR_NAME = 'spatio_temporal_momentum_signal_10m_banks_live'
STM_ML_MODEL_PREFIX = 'stm10mlive_'
STM_FEATURE_FACTOR_PREFIX = 'stm10mlive_'     # apart from the 10m backtest's 'stm10m_*' (lookup is by name)

# ── 10-minute setup: every window in BARS (identical to spatio_temporal_momentum_project_10m) ─────────────────
BAR_MINUTES = 10
BARS_PER_SESSION = bars_per_session(BAR_MINUTES)      # 39 bars in a 09:30-16:00 session
TRAINING_WINDOW = 10 * BARS_PER_SESSION               # rolling training window: 10 sessions = 390 bars
STM_FEATURES = {
    'return_horizons': (1, 3, 6, BARS_PER_SESSION),   # 10 min, 30 min, 1 h, 1 session
    'vol_lookback': BARS_PER_SESSION,
    'vol_target': 0.15,
    'macd_combinations': ((3, 9), (6, 18), (12, 36)),
    'macd_price_std_window': BARS_PER_SESSION,
    'macd_signal_std_window': BARS_PER_SESSION,
    'winsorise_halflife': BARS_PER_SESSION,
    'winsorise_threshold': 5.0,
    'min_warmup_rows': 0,
    'annualisation': periods_per_year(BAR_MINUTES),   # 252 x 39 bars per year
}

# ── Live deployment (build_live_stack) ─────────────────────────────────────────────────────────────────────────
# PAPER by default: DUR314497 is the owner's paper account (approved for paper orders). The live account is never
# traded from here unless IBKR_ACCOUNT_MODE=live and IBKR_ALLOW_LIVE=yes are set AND `account` names it; for a live
# account `paper_bar_prices` must be False (build_live_stack refuses) and real-time quotes are required (B2).
TRADING_CAPITAL = 25_000.0          # cash of the strategy's book: set_holdings sizes the weights on it
LIVE: Dict[str, Any] = {
    'account': os.getenv('STM_LIVE_ACCOUNT', 'DUR314497'),
    'strategy': 'STM_10M_BANKS',                       # trading-controls scope (kill switch / reduce-only)
    # order connection; the data connection (historical bars) is the repository factory's own (client id 1)
    'host': '127.0.0.1',
    'port': 7497,
    'client_id': 31,
    # PAPER ONLY: the paper login gets no US-equity quotes through the API (B2), so the gate prices orders on the
    # last completed TRADES bar (~10-20 min old); the quote age limit below allows it
    'paper_bar_prices': True,
    'allow_delayed_prices': False,
    'limits': RiskLimits(
        max_order_quantity=1_000,
        max_order_notional=5_000.0,
        max_position_quantity=2_000,
        max_gross_exposure=1.25 * TRADING_CAPITAL,     # whole IBKR account, all positions
        # owner 2026-11-02: cap net exposure (the first paper decision was 100 % short); orders that would push
        # |net| beyond it are refused, orders that bring it back are always allowed
        max_net_exposure=0.5 * TRADING_CAPITAL,
        max_concentration=None,
        max_quote_age_seconds=1_800,                   # paper bars; use 60 with real-time quotes
        require_cash=True,
    ),
    'max_orders': 60,                  # per window: one rebalance can send an order per bank (26) plus liquidations
    'order_window_seconds': 60.0,
    'duplicate_seconds': 30.0,
    # wall clock
    'exchange_timezone': 'America/New_York',
    'bar_close_grace_seconds': 20,     # wait after the bar closes before deciding (IBKR publishes the bar)
    'max_step_lag_seconds': 300,       # a step reached later than this (e.g. after a long retraining) is skipped
    'cancel_working_on_shutdown': True,
    # IBKR short-stock file read once a day: short targets of names IBKR cannot lend are cut to 0
    'shortable_check': True,
}


def _feature_factor_configs():
    """Factor configs (BaseModelTrainer.create_factors) for the configured features + the signal."""
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_feature_factor import (
        CompanyShareSpatioTemporalFeatureFactor,
    )
    names = STMFeatureConfig(**STM_FEATURES).feature_names()
    signal = dict(FACTOR_LIBRARY['company_share_library']['spatio_temporal_momentum_signal'])
    signal['name'] = STM_SIGNAL_FACTOR_NAME
    signal['subgroup'] = 'minutes'
    signal['frequency'] = frequency(BAR_MINUTES)
    return [signal] + [
        {'class': CompanyShareSpatioTemporalFeatureFactor, 'name': f'{STM_FEATURE_FACTOR_PREFIX}{n}', 'group': 'momentum',
         'subgroup': 'minutes', 'frequency': frequency(BAR_MINUTES), 'data_type': 'numeric', 'source': 'calculated',
         'definition': f'Spatio-Temporal Momentum 10-minute input feature (live): {n}', 'dependencies': {}}
        for n in names
    ]


DEFAULT_CONFIG: Dict[str, Any] = {
    'project_name': 'spatio_temporal_momentum_10m_live',
    'version': '1.0.0',

    # Misbuffet engine keys (trading path)
    'universe': {CompanyShare: STM_TICKERS},
    'bar_size_setting': '10 mins',
    'duration_str': '1 W',
    'max_import_ibkr': True,
    # Engine clock: a decision every 10 minutes, each one only after its bar has closed (LiveClock), seeing only
    # bars closed at that time (MarketDataHistoryService frontier). backtest_start / backtest_end are set by the
    # live runner: the next decision time .. the session's last decision.
    'config_interval': {'custom_interval_minutes': BAR_MINUTES, 'session_start': '09:40', 'session_end': '15:50'},
    'initial_capital': TRADING_CAPITAL,
    'model_type': 'tft',

    # Rolling history the model is trained on and the system needs: 390 bars (10 sessions)
    'training_window': TRAINING_WINDOW,

    # 10-minute bars imported before the first decision: today minus this many calendar days (10 sessions + margin)
    'history_calendar_days': 28,

    # Import the history before the first decision (BacktestDataPreloadService); new bars are then imported by
    # BarHistoryUpdater after each bar closes
    'preload_data': True,

    # Model lifecycle (live): trained every morning before the first decision (pretrain_before_first_decision) on
    # the last training_window bars; artifacts store their validation END DATE, so with 1 day the cycle's own rule
    # would retrain again at 09:40 (session date - yesterday's date = 1 day). 2 = a safety net only.
    'retrain_every_days': 2,
    # Live: train once before the first decision (on the history known then), so the 09:40 decision trades with a
    # fresh model; a model asset missing its bar (IBKR bars arrive late) retrains only after 3 decisions in a row
    'pretrain_before_first_decision': True,
    'missing_asset_patience': 3,

    # Factors created through Misbuffet BaseModelTrainer.create_factors
    'factors': _feature_factor_configs(),

    # Live progress + decisions (read by the Flask /stm dashboard, project=10m_live)
    'results_dir': str(BASE_PROJECT_ROOT / 'results' / 'spatio_temporal_momentum_10m_live'),

    # Portfolio construction for the trading algorithm
    'gross_exposure_cap': 1.0,

    'live': LIVE,

    'stm': {
        'universe': {
            'name': STM_UNIVERSE_NAME,
            'entity_type': 'CompanyShare',
            'n_per_sector': STM_N_PER_SECTOR,
            'seed': STM_UNIVERSE_SEED,
            'tickers': None,           # None = STM_TICKERS
        },
        'features': STM_FEATURES,
        'model': {
            'model_type': 'tft',
            'lookback': 24,            # model input window: 24 bars = 4 hours (16 encoder + 8 decoder)
            'encoder_length': 16,
            'params': {'emb_dim': 16, 'prescale_dim': 16, 'hidden_dim': 32, 'n_heads': 4, 'dropout': 0.1},
        },
        'training': {
            'first_split_start': '2019-01-01',   # research walk-forward only (not used by the engine)
            'last_split_start': '2023-12-31',
            'split_frequency_days': 365,
            'val_days': 3,             # latest 3 calendar days of the rolling window are validation
            'test_days': 365,
            'batch_size': 64,
            'lr': 1e-3,
            'weight_decay': 1e-5,
            'lr_decay_steps': 10,
            'lr_decay_gamma': 0.75,
            'min_lr': 1e-5,
            'n_epochs': 100,
            'early_stopping_rounds': 10,
            'seed': 42,
            'scaling': None,
            'apply_l1_reg': False,
            'apply_turnover_reg': False,
            'target_vol': 0.15,
            'basis_points': (0, 1, 5, 10),
            'purge_days': 1,
            'rolling_window_rows': TRAINING_WINDOW,
            'device': 'cpu',
        },
        'prediction_horizon': 1,       # next bar (10 minutes)
        'bar_minutes': BAR_MINUTES,
        'artifact_selection': 'latest_before',   # newest model whose validation ended before the bar
        'artifact_dir': str(BASE_PROJECT_ROOT / 'weights' / 'spatio_temporal_momentum_10m_live'),
        'persist_features': True,
    },

    'Portfolio': {
        'name': 'Spatio_Temporal_Momentum_10m_Live_Portfolio',
        'initial_cash': TRADING_CAPITAL,
        'currency_code': 'USD',
        'portfolio_type': 'LIVE',
        'initial_cash_currency_code': 'USD',
        'class': Portfolio,
        'holding_class': PortfolioHolding,
    },
}


def get_config() -> Dict[str, Any]:
    return dict(DEFAULT_CONFIG)


def build_stm_configuration(config: Optional[Dict[str, Any]] = None) -> STMConfiguration:
    """Translate the project config into the reusable STMConfiguration."""
    config = config or DEFAULT_CONFIG
    stm = config['stm']
    model = dict(stm['model'])
    training = dict(stm['training'])
    training['rolling_window_rows'] = int(config['training_window'])
    universe = dict(stm['universe'])
    if universe.get('tickers') is None:
        universe['tickers'] = list(STM_TICKERS)
    return STMConfiguration(
        universe=STMUniverseConfig(**universe),
        features=STMFeatureConfig(**stm['features']),
        model=STMModelConfig(**model),
        training=STMTrainingConfig(**training),
        prediction_horizon=stm['prediction_horizon'],
        artifact_selection=stm['artifact_selection'],
        artifact_dir=stm.get('artifact_dir'),
        persist_features=stm.get('persist_features', True),
        ml_model_name_prefix=STM_ML_MODEL_PREFIX,
        signal_factor_name=STM_SIGNAL_FACTOR_NAME,
        feature_factor_prefix=STM_FEATURE_FACTOR_PREFIX,
        bar_minutes=stm['bar_minutes'],
    )
