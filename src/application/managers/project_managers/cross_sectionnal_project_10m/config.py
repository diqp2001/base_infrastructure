"""
Configuration of the INTRADAY cross-sectional momentum project: 10-minute bars, a new decision every 10 minutes,
the classifier retrained every day.

Same paper universe (48 US financials, data/paper_universe.py), the same LightGBM classifier with the feature subset
and the hyper-parameters chosen by an Optuna TPE study at every retraining, and the same reusable services
(.../factor/cross_sectional_momentum/) as cross_sectionnal_project, but the model is TRAINED on 10-minute bars
(owner's choice 2026-10-26, as for spatio_temporal_momentum_project_10m): every candidate factor's window is counted
in 10-minute BARS (the 20-bar return is 200 minutes, not 20 sessions), the label is the next bar's return above the
cross-sectional median, the rolling training window is 10 sessions (390 bars) and the metrics are annualised with
252 x 39 bars. Candidates whose series has too few 10-minute bars (e.g. year-to-date windows, an index without
intraday bars) are left out of the study by its coverage filter.

Results, models, signals, universe and portfolio are kept separate from the daily project. Data: IBKR 10-minute
TRADES bars (the account has no US-equity quote permission for MIDPOINT, BI-037), plus the series the candidates
read (OPTION_IMPLIED_VOLATILITY of the shares, SPY, IRX) at the same bar size.

Research parameters live in the ``csm`` section and are turned into a CSMConfiguration by
``build_csm_configuration``. Top-level keys keep the names the Misbuffet BaseBacktestRunner reads.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.managers.project_managers.cross_sectionnal_project_10m.data.paper_universe import (
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
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import (
    bars_per_session,
    frequency,
)
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.portfolio.portfolio import Portfolio

BASE_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
CONFIG_TEST = {
    'DB_TYPE': 'sql_server',
    'DB_PATH': BASE_PROJECT_ROOT / 'base_infrastructure.db',
    'CONNECTION_STRING': f'sqlite:///{BASE_PROJECT_ROOT}/base_infrastructure.db',
}

CSM_UNIVERSE_NAME = 'csm_paper_us_financials_10m'
CSM_TICKERS: List[str] = list(PAPER_UNIVERSE_TICKERS)
CSM_SIGNAL_FACTOR_NAME = 'cross_sectional_momentum_signal_10m'
CSM_ML_MODEL_PREFIX = 'csm10m_'

# ── 10-minute setup: every window in BARS ─────────────────────────────────────
BAR_MINUTES = 10
BAR_SIZE_SETTING = '10 mins'
BARS_PER_SESSION = bars_per_session(BAR_MINUTES)      # 39 bars in a 09:30-16:00 session
TRAINING_WINDOW = 10 * BARS_PER_SESSION               # rolling training window: 10 sessions = 390 bars


def _factor_configs():
    """Signal factor created through Misbuffet BaseModelTrainer.create_factors (10-minute rows)."""
    signal = dict(FACTOR_LIBRARY['company_share_library']['cross_sectional_momentum_signal'])
    signal['name'] = CSM_SIGNAL_FACTOR_NAME
    signal['subgroup'] = 'minutes'
    signal['frequency'] = frequency(BAR_MINUTES)
    return [signal]


DEFAULT_CONFIG: Dict[str, Any] = {
    'project_name': 'cross_sectional_momentum_10m',
    'version': '1.0.0',

    # Misbuffet engine keys (trading path)
    'universe': {CompanyShare: CSM_TICKERS},
    'bar_size_setting': BAR_SIZE_SETTING,
    'duration_str': '1 W',
    'max_import_ibkr': True,
    # Engine clock: a decision every 10 minutes. Each decision only sees bars closed at that time
    # (MarketDataHistoryService frontier): the bar stamped 10:00 is known from 10:10.
    'backtest_start': '2026-10-05 09:40:00',
    'backtest_end': '2026-10-09 16:00:00',
    # Clock limited to the regular session: 09:40 (first bar 09:30 closed) .. 16:00 (last bar 15:50 closed)
    'config_interval': {'custom_interval_minutes': BAR_MINUTES, 'session_start': '09:40', 'session_end': '16:00'},
    'initial_capital': 1_000_000,
    'model_type': 'lightgbm',

    # 10-minute bars imported through MarketDataService: training window (390 bars) + feature warm-up (128 bars) +
    # the label before the first bar = ~13.3 sessions; 15 sessions from 2026-09-14
    'price_history_start': '2026-09-14',

    # Load every series the run reads (shares' TRADES and implied vol, SPY, IRX) at 10 minutes BEFORE the first bar
    # (BacktestDataPreloadService): the engine and the cycle then read locally instead of calling IBKR at each step;
    # coverage report -> results_dir/preload.csv
    'preload_data': True,

    # Retraining (Optuna study + final model) every day, at the first bar of the session, on the labels known then
    'retrain_every_days': 1,

    'factors': _factor_configs(),

    # Live progress + final results of the latest run (read by the Flask /csm dashboard, ?project=csm_10m)
    'results_dir': str(BASE_PROJECT_ROOT / 'results' / 'cross_sectional_momentum_10m'),

    'csm': {
        'universe': {'name': CSM_UNIVERSE_NAME, 'entity_type': 'CompanyShare', 'tickers': None},
        # candidates: the 48 CSMFeatureDefinition factors of the daily project, each on 10-minute bars
        'features': {
            'cross_sectional_ranks': False,
            'vol_span': BARS_PER_SESSION,      # EWM span of the bar volatility used for position sizing: 1 session
            'exclude': (),
        },
        'label': {'horizon': 1},               # the next 10-minute bar
        'bar_minutes': BAR_MINUTES,
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
        'artifact_dir': str(BASE_PROJECT_ROOT / 'weights' / 'cross_sectional_momentum_10m'),
        'persist_signals': True,
    },

    'Portfolio': {
        'name': 'Cross_Sectional_Momentum_10m_Portfolio',
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
    """Translate the project config into the reusable CSMConfiguration (10-minute bars)."""
    config = config or DEFAULT_CONFIG
    csm = config['csm']
    universe = dict(csm['universe'])
    if universe.get('tickers') is None:
        universe['tickers'] = list(CSM_TICKERS)
    return CSMConfiguration(
        universe=CSMUniverseConfig(**universe),
        features=CSMFeatureConfig(**csm['features']),
        label=CSMLabelConfig(**csm['label']),
        bar_minutes=csm['bar_minutes'],
        optimization=CSMOptimizationConfig(**csm['optimization']),
        training=CSMTrainingConfig(**csm['training']),
        artifact_dir=csm.get('artifact_dir'),
        ml_model_name_prefix=CSM_ML_MODEL_PREFIX,
        signal_factor_name=CSM_SIGNAL_FACTOR_NAME,
        persist_signals=csm.get('persist_signals', True),
    )
