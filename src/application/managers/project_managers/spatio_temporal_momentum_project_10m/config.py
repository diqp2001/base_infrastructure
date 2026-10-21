"""
Configuration for the INTRADAY Spatio-Temporal Momentum project: 10-minute bars, a new decision every 10 minutes.

Same paper universe (Tan, Roberts & Zohren 2023, Appendix B: 48 US financials, data/paper_universe.py) and the
same reusable STM services as spatio_temporal_momentum_project_full, but every window is counted in 10-minute
BARS (39 per regular session): returns over 1 / 3 / 6 / 39 bars (10 min, 30 min, 1 h, 1 session), volatility and
MACD spans in bars, a 24-bar (4 h) model input window, a rolling training window of 10 sessions, label = the next
bar's return, annualisation 252 x 39. The model is TRAINED on 10-minute bars (option A, owner's choice
2026-10-21): it is not the daily model re-scored intraday.

Results, models, signals, universe and portfolio are kept separate from the daily projects. Data: IBKR TRADES
10-minute bars (the account has no US-equity quote permission for MIDPOINT, BI-037).

Research parameters live in the ``stm`` section and are turned into an
STMConfiguration by ``build_stm_configuration`` — no research constant is
hard-coded elsewhere in the project.  Top-level keys keep the names the
Misbuffet BaseBacktestRunner reads (backtest_start, universe, ...).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.data.paper_universe import (
    PAPER_UNIVERSE_TICKERS,
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
from src.domain.entities.finance.portfolio.portfolio import Portfolio

BASE_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
CONFIG_TEST = {
    'DB_TYPE': 'sql_server',
    'DB_PATH': BASE_PROJECT_ROOT / 'base_infrastructure.db',
    'CONNECTION_STRING': f'sqlite:///{BASE_PROJECT_ROOT}/base_infrastructure.db',
}

# ── Research universe: the paper's 46 US financials (+ comparables) ──────────
STM_UNIVERSE_NAME = 'stm_paper_us_financials_10m'
STM_N_PER_SECTOR = None       # explicit list, no sampling
STM_UNIVERSE_SEED = None
STM_TICKERS: List[str] = list(PAPER_UNIVERSE_TICKERS)
STM_SIGNAL_FACTOR_NAME = 'spatio_temporal_momentum_signal_10m'
STM_ML_MODEL_PREFIX = 'stm10m_'
STM_FEATURE_FACTOR_PREFIX = 'stm10m_'     # feature factors apart from the daily 'stm_*' ones (lookup is by name)

# ── 10-minute setup: every window in BARS ─────────────────────────────────────
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
         'definition': f'Spatio-Temporal Momentum 10-minute input feature: {n}', 'dependencies': {}}
        for n in names
    ]


DEFAULT_CONFIG: Dict[str, Any] = {
    'project_name': 'spatio_temporal_momentum_10m',
    'version': '1.0.0',

    # Misbuffet engine keys (trading path)
    'universe': {CompanyShare: STM_TICKERS},
    'bar_size_setting': '10 mins',
    'duration_str': '1 W',
    'max_import_ibkr': True,
    # Engine clock: a decision every 10 minutes. Each decision only sees bars closed at that time
    # (MarketDataHistoryService frontier): the bar stamped 10:00 is known from 10:10.
    'backtest_start': '2026-10-05 09:40:00',
    'backtest_end': '2026-10-09 16:00:00',
    # Clock limited to the regular session: 09:40 (first bar 09:30 closed) .. 16:00 (last bar 15:50 closed)
    'config_interval': {'custom_interval_minutes': BAR_MINUTES, 'session_start': '09:40', 'session_end': '16:00'},
    'initial_capital': 1_000_000,
    'model_type': 'tft',

    # Rolling history the model is trained on and the system needs: 390 bars (10 sessions)
    'training_window': TRAINING_WINDOW,

    # 10-minute bars imported through MarketDataService: the training window before the first bar + margin
    'price_history_start': '2026-09-15',

    # Model lifecycle inside the engine: retrain every day on the last training_window bars known at the bar,
    # validation = latest val_days, model used from the next bar
    'retrain_every_days': 1,

    # Factors created through Misbuffet BaseModelTrainer.create_factors
    'factors': _feature_factor_configs(),

    # Live progress + final results of the latest run (read by the Flask /stm dashboard)
    'results_dir': str(BASE_PROJECT_ROOT / 'results' / 'spatio_temporal_momentum_10m'),

    # Portfolio construction for the trading algorithm
    'gross_exposure_cap': 1.0,

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
        'artifact_dir': str(BASE_PROJECT_ROOT / 'weights' / 'spatio_temporal_momentum_10m'),
        'persist_features': True,
    },

    'Portfolio': {
        'name': 'Spatio_Temporal_Momentum_10m_Portfolio',
        'initial_cash': 1_000_000,
        'currency_code': 'USD',
        'portfolio_type': 'BACKTEST',
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
