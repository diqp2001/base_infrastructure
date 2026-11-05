"""
ETF dispersion-option screener (docs/dispersion_screening_progress.txt): settings of the screen and of its data
sources. Business logic reads them through DispersionScreenConfig, never as literals.
"""

from pathlib import Path
from typing import Any, Dict

from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig

BASE_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
RESULTS_DIR = BASE_PROJECT_ROOT / 'results' / 'etf_dispersion_screener'

SCREEN = DispersionScreenConfig(
    max_constituents=49,
    min_constituents=2,
    max_holdings_age_days=7,
    min_equity_weight=0.90,
    target_dte=30,
    min_dte=20,
    max_dte=60,
    min_option_coverage=0.95,
    max_etf_option_spread=0.05,
    max_stock_option_spread=0.10,
    delta_tolerance=0.01,
    require_same_expiration=True,
    max_quote_age_seconds=60.0,
)

CONFIG: Dict[str, Any] = {
    'results_dir': str(RESULTS_DIR),
    # issuers' daily holdings files, archived as downloaded (the issuers serve the latest day only)
    'holdings_archive_dir': str(RESULTS_DIR / 'holdings_archive'),
    'issuers': ['ishares', 'ssga'],
    'download_interval_seconds': 1.0,      # one file at a time, at most one per second
}


def get_config() -> Dict[str, Any]:
    return dict(CONFIG)
