"""
Configuration for the Spatio-Temporal Momentum project — PAPER universe.

Same strategy as spatio_temporal_momentum_project, but the universe is the one
of the paper (Tan, Roberts & Zohren 2023, Appendix B): 46 actively-traded US
financial equities, delisted names replaced by comparables and uncertain names
kept with a comparable added (data/paper_universe.py) -> 48 tickers.
(The folder keeps its `_full` name; it no longer uses all S&P constituents,
which was too slow to train.)  Results, models, signals, universe and
portfolio are kept separate from the other STM projects.

Research parameters live in the ``stm`` section and are turned into an
STMConfiguration by ``build_stm_configuration`` — no research constant is
hard-coded elsewhere in the project.  Top-level keys keep the names the
Misbuffet BaseBacktestRunner reads (backtest_start, universe, ...).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.managers.project_managers.spatio_temporal_momentum_project_full.data.paper_universe import (
    PAPER_UNIVERSE_TICKERS,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
    STMFeatureConfig,
    STMModelConfig,
    STMTrainingConfig,
    STMUniverseConfig,
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
STM_UNIVERSE_NAME = 'stm_paper_us_financials'
STM_N_PER_SECTOR = None       # explicit list, no sampling
STM_UNIVERSE_SEED = None
STM_TICKERS: List[str] = list(PAPER_UNIVERSE_TICKERS)
STM_SIGNAL_FACTOR_NAME = 'spatio_temporal_momentum_signal_full'
STM_ML_MODEL_PREFIX = 'stmfull_'

# ── 4-month setup ─────────────────────────────────────────────────────────────
# The whole strategy needs only TRAINING_WINDOW daily sessions (4 x 21 = 84):
# features, model input window and training samples all fit inside it.
# The reference windows (252-day returns, 252-day MACD normalisation) cannot be
# computed from 4 months, so every window below is scaled down accordingly.
TRAINING_WINDOW = 84
STM_FEATURES = {
    'return_horizons': (1, 5, 10, 21),
    'vol_lookback': 20,
    'vol_target': 0.15,
    'macd_combinations': ((2, 6), (4, 12), (8, 24)),
    'macd_price_std_window': 10,
    'macd_signal_std_window': 10,
    'winsorise_halflife': 21,
    'winsorise_threshold': 5.0,
    'min_warmup_rows': 0,
}


def _feature_factor_configs():
    """Factor configs (BaseModelTrainer.create_factors) for the configured features + the signal."""
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_feature_factor import (
        CompanyShareSpatioTemporalFeatureFactor,
    )
    names = STMFeatureConfig(**STM_FEATURES).feature_names()
    signal = dict(FACTOR_LIBRARY['company_share_library']['spatio_temporal_momentum_signal'])
    signal['name'] = STM_SIGNAL_FACTOR_NAME
    return [signal] + [
        {'class': CompanyShareSpatioTemporalFeatureFactor, 'name': f'stm_{n}', 'group': 'momentum',
         'subgroup': 'daily', 'frequency': '1d', 'data_type': 'numeric', 'source': 'calculated',
         'definition': f'Spatio-Temporal Momentum input feature: {n}', 'dependencies': {}}
        for n in names
    ]


DEFAULT_CONFIG: Dict[str, Any] = {
    'project_name': 'spatio_temporal_momentum_full',
    'version': '1.0.0',

    # Misbuffet engine keys (trading path)
    'universe': {CompanyShare: STM_TICKERS},
    'bar_size_setting': '1 day',
    'duration_str': '1 Y',
    'max_import_ibkr': True,
    # Engine clock. Decisions at each bar only see bars closed at that time
    # (MarketDataHistoryService frontier): a daily bar dated D is known from D+1 00:00.
    'backtest_start': '2026-06-01 16:00:00',
    'backtest_end': '2026-09-30 16:00:00',
    'config_interval': {'custom_interval_days': 1},
    'initial_capital': 1_000_000,
    'model_type': 'tft',

    # Rolling history the model is trained on and the system needs: 84 sessions (~4 months)
    'training_window': TRAINING_WINDOW,

    # Daily closes imported through MarketDataService: ~4 months before the first bar
    'price_history_start': '2025-08-25',

    # Model lifecycle inside the engine: retrain on the last training_window sessions
    # known at the bar, validation = latest val_days, model used from the next session
    'retrain_every_days': 30,

    # Factors created through Misbuffet BaseModelTrainer.create_factors
    'factors': _feature_factor_configs(),

    # Live progress + final results of the latest run (read by the Flask /stm dashboard)
    'results_dir': str(BASE_PROJECT_ROOT / 'results' / 'spatio_temporal_momentum_full'),

    # Portfolio construction for the trading algorithm
    'gross_exposure_cap': 1.0,

    'stm': {
        'universe': {
            'name': STM_UNIVERSE_NAME,
            'entity_type': 'CompanyShare',
            'n_per_sector': STM_N_PER_SECTOR,
            'seed': STM_UNIVERSE_SEED,
            'tickers': None,           # None = reference sector sample (STM_TICKERS)
        },
        'features': STM_FEATURES,
        'model': {
            'model_type': 'tft',
            'lookback': 21,            # model input window: 1 month (14 encoder + 7 decoder)
            'encoder_length': 14,
            'params': {'emb_dim': 16, 'prescale_dim': 16, 'hidden_dim': 32, 'n_heads': 4, 'dropout': 0.1},
        },
        'training': {
            'first_split_start': '2019-01-01',   # research walk-forward only (not used by the engine)
            'last_split_start': '2023-12-31',
            'split_frequency_days': 365,
            'val_days': 14,            # latest 2 weeks of the rolling window are validation
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
        'prediction_horizon': 1,
        'artifact_selection': 'latest_before',   # newest model whose validation ended before the session
        'artifact_dir': str(BASE_PROJECT_ROOT / 'weights' / 'spatio_temporal_momentum_full'),
        'persist_features': True,
    },

    'Portfolio': {
        'name': 'Spatio_Temporal_Momentum_Full_Portfolio',
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
    )
