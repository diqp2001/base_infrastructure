"""
Configuration of the cross-sectional momentum project: a LightGBM CLASSIFIER predicting, for every asset of the
paper universe (48 US financials, data/paper_universe.py), whether its next-session return beats the
cross-sectional median, with the feature subset and the LightGBM hyper-parameters chosen at every retraining by
an Optuna study using the Tree-structured Parzen Estimator (TPE) sampler.

Same structure as spatio_temporal_momentum_project_full: the Misbuffet engine runs bar by bar; the algorithm
calls CSMTradingCycle.step (reusable services in .../factor/cross_sectional_momentum/); every read goes through
the MarketDataHistoryService frontier. Results, models, signals, universe and portfolio are kept separate from
the other projects.

Research parameters live in the ``csm`` section and are turned into a CSMConfiguration by
``build_csm_configuration``. Top-level keys keep the names the Misbuffet BaseBacktestRunner reads.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.managers.project_managers.cross_sectionnal_project.data.paper_universe import (
    PAPER_UNIVERSE_TICKERS,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
    CSMFeatureConfig,
    CSMLabelConfig,
    CSMOptimizationConfig,
    CSMTrainingConfig,
    CSMUniverseConfig,
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

CSM_UNIVERSE_NAME = 'csm_paper_us_financials'
CSM_TICKERS: List[str] = list(PAPER_UNIVERSE_TICKERS)
CSM_SIGNAL_FACTOR_NAME = 'cross_sectional_momentum_signal'
CSM_ML_MODEL_PREFIX = 'csm_'

# Rolling window the classifier is trained on: 252 sessions (~1 year) of (date, asset) rows, ~12 000 rows
TRAINING_WINDOW = 252


def _factor_configs():
    """Signal factor created through Misbuffet BaseModelTrainer.create_factors."""
    signal = dict(FACTOR_LIBRARY['company_share_library']['cross_sectional_momentum_signal'])
    signal['name'] = CSM_SIGNAL_FACTOR_NAME
    return [signal]


DEFAULT_CONFIG: Dict[str, Any] = {
    'project_name': 'cross_sectional_momentum',
    'version': '2.0.0',

    # Misbuffet engine keys (trading path)
    'universe': {CompanyShare: CSM_TICKERS},
    'bar_size_setting': '1 day',
    'duration_str': '1 Y',
    'max_import_ibkr': True,
    # Engine clock: one decision per day. A daily bar dated D is known from D+1 00:00 (frontier), so the
    # 16:00 decision of D+1 uses the close of D.
    'backtest_start': '2026-06-01 16:00:00',
    'backtest_end': '2026-09-30 16:00:00',
    'config_interval': {'custom_interval_days': 1},
    'initial_capital': 1_000_000,
    'model_type': 'lightgbm',

    # Daily closes imported through MarketDataService: training window (252) + feature warm-up (106-session
    # lookback of the 5-month factors) before the first bar
    'price_history_start': '2024-11-01',

    # Retraining (Optuna study + final model) every 21 calendar days, on the labels known at the bar
    'retrain_every_days': 21,

    'factors': _factor_configs(),

    # Live progress + final results of the latest run (read by the Flask /csm dashboard)
    'results_dir': str(BASE_PROJECT_ROOT / 'results' / 'cross_sectional_momentum'),

    'csm': {
        'universe': {'name': CSM_UNIVERSE_NAME, 'entity_type': 'CompanyShare', 'tickers': None},
        # candidates: CSMFeatureDefinition = 24 momentum factors + share turnover (1-6 months, daily), 16-week VPT
        # (20-day lag), 1-month high - low, max daily return 6m, min return 120d, return relative to SPY
        # (1d/5d/20d/3m/6m), each computed by its own domain factor; Optuna TPE selects the subset of each model.
        # Ranks off: the factor path scores one entity.
        'features': {
            'cross_sectional_ranks': False,
            'vol_span': 20,
            'exclude': (),
        },
        'label': {'horizon': 1},
        'optimization': {
            'n_trials': 40,
            'n_startup_trials': 10,
            'multivariate': True,
            'n_folds': 3,
            'metric': 'auc',
            'min_features': 3,
            'seed': 42,
            'timeout_seconds': 600,
            'top_trial_fraction': 0.2,
        },
        'training': {
            'training_window_rows': TRAINING_WINDOW,
            'long_short_quantile': 0.2,
            'gross_exposure': 1.0,
        },
        'artifact_dir': str(BASE_PROJECT_ROOT / 'weights' / 'cross_sectional_momentum'),
        'persist_signals': True,
    },

    'Portfolio': {
        'name': 'Cross_Sectional_Momentum_Portfolio',
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


def build_csm_configuration(config: Optional[Dict[str, Any]] = None) -> CSMConfiguration:
    """Translate the project config into the reusable CSMConfiguration."""
    config = config or DEFAULT_CONFIG
    csm = config['csm']
    universe = dict(csm['universe'])
    if universe.get('tickers') is None:
        universe['tickers'] = list(CSM_TICKERS)
    return CSMConfiguration(
        universe=CSMUniverseConfig(**universe),
        features=CSMFeatureConfig(**csm['features']),
        label=CSMLabelConfig(**csm['label']),
        optimization=CSMOptimizationConfig(**csm['optimization']),
        training=CSMTrainingConfig(**csm['training']),
        artifact_dir=csm.get('artifact_dir'),
        ml_model_name_prefix=CSM_ML_MODEL_PREFIX,
        signal_factor_name=CSM_SIGNAL_FACTOR_NAME,
        persist_signals=csm.get('persist_signals', True),
    )
