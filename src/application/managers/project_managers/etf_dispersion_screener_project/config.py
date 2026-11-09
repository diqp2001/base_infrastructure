"""
ETF dispersion-option screener (docs/dispersion_screening_progress.txt): settings of the screen and of its data
sources. Business logic reads them through DispersionScreenConfig, never as literals.
"""

import os
from pathlib import Path
from typing import Any, Dict

from dataclasses import replace

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
    min_option_coverage=1.0,                       # 100 %: every constituent and the ETF need options (owner)
    require_same_expiration=True,
    max_quote_age_seconds=60.0,
)

# Research override for a run after the close: frozen (last) quotes are accepted, whatever their age. The run manifest
# records the settings; never for a trading decision.
if os.getenv('DISPERSION_ALLOW_FROZEN', '').lower() in ('1', 'yes', 'true'):
    SCREEN = replace(SCREEN, allow_frozen_quotes=True, max_quote_age_seconds=86_400.0)

CONFIG: Dict[str, Any] = {
    'results_dir': str(RESULTS_DIR),
    # issuers' daily holdings files, archived as downloaded (the issuers serve the latest day only)
    'holdings_archive_dir': str(RESULTS_DIR / 'holdings_archive'),
    # daily closes of the 6M realized history, one file per symbol (refetched when they do not cover the date)
    'price_history_dir': str(RESULTS_DIR / 'price_history'),
    'issuers': ['ishares', 'ssga'],
    'download_interval_seconds': 1.0,      # one file at a time, at most one per second
    # option data (P.03): IBKR, READ-ONLY, its own client id (never an order connection). Unset host = universe only.
    # Free: streaming data covered by the account's subscriptions; no regulatory snapshots. D6: any login whose
    # subscriptions cover US equities + options (the paper login shares the live login's subscriptions).
    'ibkr': {
        'host': os.getenv('DISPERSION_IBKR_HOST', ''),
        'port': int(os.getenv('DISPERSION_IBKR_PORT', '7496')),
        'client_id': int(os.getenv('DISPERSION_IBKR_CLIENT_ID', '77')),
        'max_lines': int(os.getenv('DISPERSION_IBKR_MAX_LINES', '40')),   # the trader on the same login needs ~30
        'timeout_seconds': 12.0,
        # pause between two lookups / quote batches: the full screen froze the shared paper gateway (2026-11-05/06)
        'pause_seconds': float(os.getenv('DISPERSION_IBKR_PAUSE_SECONDS', '0.2')),
        'maturities_client_id': int(os.getenv('DISPERSION_MATURITIES_CLIENT_ID', '79')),   # the maturities job
        'history_client_id': int(os.getenv('DISPERSION_HISTORY_CLIENT_ID', '80')),         # the 6M history job
        'puts_client_id': int(os.getenv('DISPERSION_PUTS_CLIENT_ID', '81')),               # the put strategy job
        'history_pause_seconds': float(os.getenv('DISPERSION_HISTORY_PAUSE_SECONDS', '1.5')),
    },
    # the /dispersion page starts a maturities job through this launcher (the paper gateway publishes no port: the
    # job runs on its Docker network) - command prefix + script, then: <log file> <module> <args>
    'job_launcher': os.getenv('DISPERSION_JOB_LAUNCHER', 'wsl -d Ubuntu -- bash').split(),
    'job_script': str(BASE_PROJECT_ROOT / 'scripts' / 'dispersion_docker_job.sh'),
    # P.11 read-only paper validation: the best priced candidates' legs quoted again this many seconds after the
    # screen (would the screened prices still fill?). No orders (owner, 2026-11-06). Unset = no validation.
    'validate_after_seconds': (float(os.environ['DISPERSION_VALIDATE_AFTER_SECONDS'])
                               if os.getenv('DISPERSION_VALIDATE_AFTER_SECONDS') else None),
    'validate_top': int(os.getenv('DISPERSION_VALIDATE_TOP', '5')),
}


def get_config() -> Dict[str, Any]:
    return dict(CONFIG)
