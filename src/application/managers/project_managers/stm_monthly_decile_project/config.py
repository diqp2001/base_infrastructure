"""
Configuration of the MONTHLY cross-sectional decile strategy of the spatio-temporal momentum (STM) model on the
Dow Jones Industrial Average members (DIA's point-in-time constituents).

Owner's choices (2026-11-16):
- the existing STM model (the 10m_live pipeline: features, TFT, Sharpe loss, walk-forward trainer) on MONTHLY bars:
  one row = one month-end close, target = the next month's return (prediction_horizon 1 row), retrained every month;
- universe: the Dow members in force at each rebalance (src/application/services/universe/djia_membership.py);
- every month the members are ranked by the model's score into 10 deciles (D1 lowest, D10 highest), each held one
  month equal-weighted; the Misbuffet engine trades D10 - D1 (long D10, short D1), every decile is reported;
- model A = price features only, model B = + Eulerpool point-in-time fundamentals (``use_eulerpool_fundamentals``):
  same members, dates, target, deciles and weighting.

Top-level keys keep the names the Misbuffet BaseBacktestRunner reads (backtest_start, universe, ...); the research
parameters live in the 'deciles' / 'stm' sections and become objects through the build_* functions below.
"""

from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
    STMFeatureConfig,
    STMModelConfig,
    STMTrainingConfig,
    STMUniverseConfig,
)
from src.application.services.portfolio_research.decile_portfolios import DecileConfig
from src.application.services.portfolio_research.stm_decile_cycle import PERIODS, PERIODS_PER_YEAR
from src.application.services.universe.djia_membership import BASE_MEMBERS, CHANGES, build_membership
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.portfolio.portfolio import Portfolio

BASE_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
CONFIG_TEST = {
    'DB_TYPE': 'sql_server',
    'DB_PATH': BASE_PROJECT_ROOT / 'base_infrastructure.db',
    'CONNECTION_STRING': f'sqlite:///{BASE_PROJECT_ROOT}/base_infrastructure.db',
}
RESULTS_DIR = BASE_PROJECT_ROOT / 'results' / 'stm_monthly_deciles'

# every share that was a Dow member since the membership's base date (the engine imports their daily bars)
ALL_MEMBERS = list(dict.fromkeys(list(BASE_MEMBERS) + [s for c in CHANGES for s in c.added]))
MONTHS_PER_YEAR = 12

# Eulerpool point-in-time fundamentals of model B (csm_fundamentals: only factors the statements serve; valuation
# ratios read a daily close and are not candidates; market capitalisation is not served)
FUNDAMENTAL_FEATURES = (
    'fund_roe_ttm_1q', 'fund_roa_ttm_1q',                                         # profitability
    'fund_gross_margin_ttm_1q', 'fund_operating_margin_ttm_1q', 'fund_net_margin_ttm_1q',
    'fund_revenue_growth_yoy_1q', 'fund_net_income_growth_yoy_1q', 'fund_total_assets_growth_yoy_1q',   # growth
    'fund_eps_growth_1y', 'fund_free_cash_flow_growth_1y',
    'fund_debt_to_equity_1q',                                                     # quality / leverage
)

DEFAULT_CONFIG: Dict[str, Any] = {
    'project_name': 'stm_monthly_deciles',
    'version': '1.0.0',

    # Misbuffet engine keys (trading path): a slice of the members' daily bars at every step
    'universe': {CompanyShare: ALL_MEMBERS},
    'bar_size_setting': '1 day',
    'duration_str': '1 Y',
    'max_import_ibkr': True,
    # Engine clock: one step a day at 16:00; a close dated D is known from D+1 00:00, so the first step of a new
    # month knows every close of the previous one and rebalances at its last trading day
    'backtest_start': '2021-01-04 16:00:00',
    'backtest_end': '2026-10-30 16:00:00',
    'config_interval': {'custom_interval_days': 1},
    'initial_capital': 1_000_000,
    'model_type': 'tft',
    # Monthly closes before the first rebalance: the feature warm-up (36 months) + the rolling training window
    # (120 months)
    'price_history_start': '2007-01-01',
    'preload_data': True,
    # members IBKR no longer lists (WBA, delisted 2025): file caches (src/.../backtest_preload/daily_price_sources.py)
    'price_history_dir': str(BASE_PROJECT_ROOT / 'results' / 'etf_dispersion_stm' / 'price_history'),
    'file_price_sources': ('ibkr', 'eulerpool'),
    'results_dir': str(RESULTS_DIR),

    'deciles': {
        'n_deciles': 10,
        'weighting': 'equal_weight',          # reserved: market_cap_weight, volatility_weight, model_score_weight
        'transaction_cost_bps': 5.0,          # research net returns: traded notional x bps (gross reported too)
        'long_short_gross': 1.0,              # engine book: +0.5 over D10, -0.5 over D1
        'traded_variant': 'A',
        # how often the deciles are re-formed: 'Nd' trading days, 'Nw' weeks, 'Nmo' months (one model row = one
        # period-end close; the annualisation follows the period). Default: every month (the project's design).
        'rebalance_every': '1mo',
        'retrain_every_rebalances': 1,        # retrain at every rebalance
        'use_eulerpool_fundamentals': True,   # also run model B (needs the Eulerpool key)
        'fundamentals': FUNDAMENTAL_FEATURES,
        # model B's fundamentals: z-scored within each GICS sector (djia_membership.SECTORS; a name alone in its
        # sector keeps the z-score across all members) - 'cross_sectional' = across all members
        'fundamental_scaling': 'sector_neutral',
        # the closes the model and the decile returns read: IBKR ADJUSTED_LAST = dividend-adjusted (total return).
        # The engine trades and values at TRADES (both series are imported). 'TRADES' = price returns.
        'research_price_series': 'ADJUSTED_LAST',
    },

    # the existing STM pipeline, rows = months
    'stm': {
        'universe': {'name': 'djia_members_monthly', 'entity_type': 'CompanyShare', 'tickers': None},
        'features': {
            'return_horizons': (1, 3, 6, 12),             # months
            'vol_lookback': 12,
            'vol_target': 0.15,
            'macd_combinations': ((3, 6), (6, 12)),
            'macd_price_std_window': 12,
            'macd_signal_std_window': 24,
            'winsorise_halflife': 24,
            'winsorise_threshold': 5.0,
            'min_warmup_rows': 36,
            'annualisation': MONTHS_PER_YEAR,
        },
        'model': {
            'model_type': 'tft',
            'lookback': 12,                               # one year of months: 11 encoder + 1 decoder (the target)
            'encoder_length': 11,
            'params': {'emb_dim': 8, 'prescale_dim': 8, 'hidden_dim': 16, 'n_heads': 2, 'dropout': 0.1},
        },
        'training': {
            'val_days': 730,                              # the last 24 months of the window are validation
            'n_epochs': 100,
            'early_stopping_rounds': 10,
            'batch_size': 16,
            'rolling_window_rows': 120,                   # 10 years of months (also the history a member needs)
            'purge_days': 1,
            'device': 'cpu',
        },
        'prediction_horizon': 1,                          # the next month
    },

    'Portfolio': {
        'name': 'STM_Monthly_Decile_DJIA_Portfolio',
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


def backtest_window(config: Optional[Dict[str, Any]] = None):
    config = config or DEFAULT_CONFIG
    return (date.fromisoformat(str(config['backtest_start'])[:10]), date.fromisoformat(str(config['backtest_end'])[:10]))


def rebalance_schedule(config: Optional[Dict[str, Any]] = None):
    """(pandas period alias, every N periods) of deciles.rebalance_every ('1mo' when the config has none)."""
    from src.domain.entities.strategy.frequency import Frequency
    token = (config or DEFAULT_CONFIG)['deciles'].get('rebalance_every') or '1mo'
    frequency = Frequency.parse(token)
    if frequency is None or frequency.unit not in PERIODS:
        raise ValueError(f"deciles.rebalance_every must be days, weeks or months ('5d', '1w', '1mo'), got {token!r}")
    return PERIODS[frequency.unit], frequency.count


def rebalance_labels(config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """How often the deciles are re-formed and the model retrained, in words ('every month', 'every 2 weeks')."""
    from src.domain.entities.strategy.frequency import Frequency
    d = (config or DEFAULT_CONFIG)['deciles']
    rebalance = Frequency.parse(d.get('rebalance_every') or '1mo')
    n = int(d.get('retrain_every_rebalances') or 1)
    retrain = Frequency(rebalance.unit, rebalance.count * n)
    return {'rebalance': rebalance.label, 'holding_period': rebalance.label.replace('every ', ''),
            'retraining': retrain.label, 'token': rebalance.token}


def periods_per_year(config: Optional[Dict[str, Any]] = None) -> float:
    """Rebalances a year: 12 monthly, 52 weekly, 252 daily, divided by the count (every 2 weeks -> 26)."""
    period, every = rebalance_schedule(config)
    return PERIODS_PER_YEAR[period] / every


def build_decile_config(config: Optional[Dict[str, Any]] = None) -> DecileConfig:
    d = (config or DEFAULT_CONFIG)['deciles']
    return DecileConfig(n_deciles=d['n_deciles'], weighting=d['weighting'],
                        transaction_cost_bps=d['transaction_cost_bps'], periods_per_year=periods_per_year(config))


def build_stm_configuration(config: Optional[Dict[str, Any]] = None) -> STMConfiguration:
    """The project config as the reusable STMConfiguration (rows = months; in-memory model, nothing persisted)."""
    stm = (config or DEFAULT_CONFIG)['stm']
    # one row = one rebalance period: the features annualise with the rebalances a year (12 when monthly)
    features = {**stm['features'], 'annualisation': max(1, round(periods_per_year(config)))}
    return STMConfiguration(
        universe=STMUniverseConfig(**stm['universe']),
        features=STMFeatureConfig(**features),
        model=STMModelConfig(**stm['model']),
        training=STMTrainingConfig(**stm['training']),
        prediction_horizon=stm['prediction_horizon'],
        ml_model_name_prefix='stmdecile_',
        signal_factor_name='stm_monthly_decile_signal',
        feature_factor_prefix='stmdecile_',
        persist_features=False,
    )


def variants(config: Optional[Dict[str, Any]] = None):
    """['A'] or ['A', 'B'] (B = A + the Eulerpool fundamentals)."""
    d = (config or DEFAULT_CONFIG)['deciles']
    return ['A', 'B'] if d['use_eulerpool_fundamentals'] else ['A']


def settings(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config = config or DEFAULT_CONFIG
    m = build_membership()
    return {'deciles': config['deciles'], 'stm': build_stm_configuration(config).to_dict(),
            'window': [config['backtest_start'], config['backtest_end']],
            'membership': {'base_date': m.base_date, 'members': m.all_constituents()},
            'variants': variants(config)}
