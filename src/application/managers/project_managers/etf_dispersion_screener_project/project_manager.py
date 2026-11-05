"""
ETF dispersion-option screener. Orchestration only: the rules are in src/domain/entities/finance/dispersion, the
data behind ports (issuer adapters in src/infrastructure/repositories/issuer_repo).

P.02 (this stage): the ETF universe of a screening date -> results_dir/<date>/universe.json + universe.csv and the
run manifest. Options, sizing and premiums come with P.03 – P.07.

    python -m src.application.managers.project_managers.etf_dispersion_screener_project.project_manager [YYYY-MM-DD]
"""

import csv
import json
import os
import sys
from dataclasses import asdict
from datetime import date
from typing import Any, Dict, Optional

from src.application.managers.project_managers.etf_dispersion_screener_project import config as project_config
from src.application.managers.project_managers.project_manager import ProjectManager
from src.application.services.dispersion.etf_universe_service import EtfUniverseService, UniverseResult
from src.application.services.misbuffet import run_manifest
from src.infrastructure.repositories.issuer_repo.ishares_holdings_source import ISharesHoldingsSource
from src.infrastructure.repositories.issuer_repo.ssga_holdings_source import SSGAHoldingsSource

ISSUER_SOURCES = {'ishares': ISharesHoldingsSource, 'ssga': SSGAHoldingsSource}


class EtfDispersionScreenerProjectManager(ProjectManager):

    def __init__(self, config: Optional[Dict[str, Any]] = None, screen=None, sources=None):
        super().__init__()
        self.config = config or project_config.get_config()
        self.screen = screen or project_config.SCREEN
        if sources is None:
            sources = []
            for issuer in self.config['issuers']:
                source = ISSUER_SOURCES[issuer](self.config['holdings_archive_dir'],
                                                min_interval_seconds=self.config['download_interval_seconds'])
                sources.append((source, source))
        self.universe_service = EtfUniverseService(sources, self.screen)

    def run(self, screening_date: Optional[date] = None, tickers=None) -> UniverseResult:
        screening_date = screening_date or date.today()
        out_dir = os.path.join(self.config['results_dir'], screening_date.isoformat())
        manifest = run_manifest.build_manifest('screen', 'ETF dispersion screener',
                                               {**self.config, 'screen': asdict(self.screen)}, (screening_date,))
        run_manifest.write_manifest(out_dir, manifest)
        try:
            result = self.universe_service.build(screening_date, tickers, progress=lambda m: print(m, flush=True))
        except Exception as e:
            run_manifest.finish_manifest(out_dir, manifest, f"failed: {e!r}"[:300])
            raise
        write_universe(out_dir, result)
        run_manifest.finish_manifest(out_dir, manifest, "completed")
        print(f"{screening_date}: {result.counts()} -> {out_dir}", flush=True)
        return result


def write_universe(out_dir: str, result: UniverseResult) -> None:
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for e in result.entries:
        c = e.constituents
        rows.append({
            'ticker': e.listing.ticker, 'name': e.listing.name, 'issuer': e.listing.issuer,
            'asset_class': e.listing.asset_class, 'status': e.status, 'reasons': '; '.join(e.reasons),
            'constituents': c.count if c and c.ok else None, 'equity_share': round(c.equity_share, 6) if c else None,
            'holdings_as_of': str(c.as_of) if c else None, 'holdings_source': c.source if c else None,
            'weights': c.weights if c and c.ok else {},
        })
    with open(os.path.join(out_dir, 'universe.json'), 'w', encoding='utf-8') as f:
        json.dump({'screening_date': str(result.screening_date), 'counts': result.counts(), 'etfs': rows}, f,
                  indent=1)
    with open(os.path.join(out_dir, 'universe.csv'), 'w', encoding='utf-8', newline='') as f:
        fields = [k for k in rows[0] if k != 'weights'] if rows else []
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    EtfDispersionScreenerProjectManager().run(day)
