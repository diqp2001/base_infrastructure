"""
Configuration of the monthly, model-filtered ETF dispersion on DIA (SPDR Dow Jones Industrial Average ETF).

Owner's choices (2026-11-16):
- sizing: the screener's replication (ETFShareOptionFactor.replicate) - the constituent calls copy the ETF's
  weights; N = the fewest DIA calls at which every leg is a whole contract, FIXED on the full basket before the
  model filter;
- premiums MODELLED (Black-Scholes on realised vol: no option history exists);
- the existing STM model refit on DIA's constituents;
- everything MONTHLY: roll at each monthly expiry (the screener's ~30 DTE rule), retraining at every roll,
  21-session prediction horizon.

The project runs inside the Misbuffet engine, one daily bar at a time (backtesting/base_project_algorithm.py ->
DispersionTradingCycle.step). Top-level keys keep the names the Misbuffet BaseBacktestRunner reads (backtest_start,
universe, ...); the research parameters live in their sections and are turned into objects by the build_* functions
below - no research constant is hard-coded elsewhere in the project.
"""

from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

from src.application.managers.project_managers.etf_dispersion_stm_project.data.dia_universe import (
    BASE_MEMBERS,
    CHANGES,
    ETF,
    build_membership,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
    STMFeatureConfig,
    STMModelConfig,
    STMTrainingConfig,
    STMUniverseConfig,
)
from src.application.services.dispersion.model_selection import ModelFilterConfig
from src.application.services.dispersion.modelled_option_pricing import OptionModelConfig
from src.application.services.dispersion.screen_config import DispersionScreenConfig
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.share.etf_share.etf_share import ETFShare
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.portfolio.portfolio import Portfolio

BASE_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
CONFIG_TEST = {
    'DB_TYPE': 'sql_server',
    'DB_PATH': BASE_PROJECT_ROOT / 'base_infrastructure.db',
    'CONNECTION_STRING': f'sqlite:///{BASE_PROJECT_ROOT}/base_infrastructure.db',
}
RESULTS_DIR = BASE_PROJECT_ROOT / 'results' / 'etf_dispersion_stm'

# every constituent the index ever had since the base date (the engine imports their daily bars)
ALL_MEMBERS = list(dict.fromkeys(list(BASE_MEMBERS) + [s for c in CHANGES for s in c.added]))
HORIZON_SESSIONS = 21                 # STM prediction horizon: one month of sessions

DEFAULT_CONFIG: Dict[str, Any] = {
    'project_name': 'etf_dispersion_stm',
    'version': '2.0.0',

    # Misbuffet engine keys (trading path). The engine builds a slice of the members' and the ETF's daily bars at
    # every step (IBKR: IBKRCompanyShareRepository / IBKRETFShareRepository).
    'universe': {CompanyShare: ALL_MEMBERS, ETFShare: [ETF]},
    'bar_size_setting': '1 day',
    'duration_str': '1 Y',
    'max_import_ibkr': True,
    # Engine clock: one step a day at 16:00. A daily close dated D is known from D+1 00:00 (frontier), so the
    # Monday step sees Friday's close: a monthly expiry is settled, and the next trade opened at that close, at the
    # first step after it.
    'backtest_start': '2021-01-04 16:00:00',
    'backtest_end': '2026-10-30 16:00:00',
    'config_interval': {'custom_interval_days': 1},
    'initial_capital': 1_000_000,
    'model_type': 'tft',

    # Daily closes needed before the first trade: the STM features' warm-up and the 6-year rolling training window
    'price_history_start': '2007-01-01',
    # Every member's and the ETF's daily bars loaded BEFORE the first bar (BacktestDataPreloadService, IBKR): coverage report
    # -> results_dir/preload.csv
    'preload_data': True,

    # Members IBKR no longer lists (WBA): file caches per source, in preference order (data/price_ingestion.py)
    'price_history_dir': str(RESULTS_DIR / 'price_history'),
    'file_price_sources': ('ibkr', 'eulerpool'),

    # Live progress + final results of the latest run (read by the /dispersion-stm page)
    'results_dir': str(RESULTS_DIR),

    'dispersion': {
        'etf': ETF,
        'traded': 'model_filtered',       # the strategy the engine trades: 'model_filtered' (B) or 'original' (A)
        'contracts': 'whole',             # whole contracts (the engine trades integers)
        'retrain_every_rebalances': 1,    # monthly
        # the screener's expiry rule on the monthly expiries (third Fridays), held to expiry
        'screen': {'target_dte': 30, 'min_dte': 20, 'max_dte': 60},
        'option_model': {
            'vol_window': 63,             # 3 months of daily returns
            'vol_multiplier': 1.0,        # implied = realised (no volatility premium modelled)
            'etf_vol_multiplier': 1.0,
            'risk_free_rate': 0.0,        # research assumption (both legs)
            'dividend_yield': 0.0,
            'multiplier': 100.0,
        },
        'model_filter': {
            'minimum_model_score': 0.0,   # buy calls only on constituents the STM model would hold long
            'top_n': None,
            'bottom_n_excluded': None,
            'percentile_threshold': None,
            'unscored': 'keep',           # no score (e.g. too little history): bought as in the full basket
        },
    },

    'stm': {
        'universe': {'name': 'dia_constituents_monthly', 'entity_type': 'CompanyShare', 'tickers': None},
        'features': {},                   # the reference daily features (returns 1..252 d, MACD)
        'model': {
            'model_type': 'tft',
            'lookback': 84,
            'encoder_length': 84 - HORIZON_SESSIONS,   # decoder steps = the 21-session horizon
            'params': {'emb_dim': 16, 'prescale_dim': 16, 'hidden_dim': 32, 'n_heads': 4, 'dropout': 0.1},
        },
        'training': {
            'val_days': 365,
            'n_epochs': 100,
            'early_stopping_rounds': 10,
            'batch_size': 64,
            'rolling_window_rows': 252 * 6,   # last 6 years of sessions (also the history a member needs)
            'purge_days': 1,
            'device': 'cpu',
        },
        'prediction_horizon': HORIZON_SESSIONS,
    },

    'Portfolio': {
        'name': 'ETF_Dispersion_STM_DIA_Portfolio',
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


def _section(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return (config or DEFAULT_CONFIG)['dispersion']


def backtest_window(config: Optional[Dict[str, Any]] = None):
    """(first, last) day on which a trade may open: the engine's start and end dates."""
    config = config or DEFAULT_CONFIG
    return (date.fromisoformat(str(config['backtest_start'])[:10]), date.fromisoformat(str(config['backtest_end'])[:10]))


def build_screen(config=None) -> DispersionScreenConfig:
    return DispersionScreenConfig(**_section(config)['screen'])


def build_option_model(config=None) -> OptionModelConfig:
    return OptionModelConfig(**_section(config)['option_model'])


def build_model_filter(config=None) -> ModelFilterConfig:
    return ModelFilterConfig(**_section(config)['model_filter'])


def build_stm_configuration(config: Optional[Dict[str, Any]] = None) -> STMConfiguration:
    """Translate the project config into the reusable STMConfiguration (in-memory model: nothing persisted)."""
    stm = (config or DEFAULT_CONFIG)['stm']
    return STMConfiguration(
        universe=STMUniverseConfig(**stm['universe']),
        features=STMFeatureConfig(**stm['features']),
        model=STMModelConfig(**stm['model']),
        training=STMTrainingConfig(**stm['training']),
        prediction_horizon=stm['prediction_horizon'],
        ml_model_name_prefix='dispstm_',
        signal_factor_name='etf_dispersion_stm_signal',
        feature_factor_prefix='dispstm_',
        persist_features=False,
    )


def settings(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The run's research settings (summary.json)."""
    config = config or DEFAULT_CONFIG
    m = build_membership()
    return {
        'dispersion': _section(config),
        'stm': build_stm_configuration(config).to_dict(),
        'membership': {'base_date': m.base_date, 'members': m.all_constituents(),
                       'changes': [asdict(c) for c in CHANGES], 'splits': [asdict(s) for s in m.splits]},
        'window': [config['backtest_start'], config['backtest_end']],
        'file_price_sources': config['file_price_sources'],
    }
