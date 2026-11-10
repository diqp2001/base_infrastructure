"""
ETF dispersion-option screener. Orchestration only: the option rules are in ShareOptionFactor, the pricing in
src/application/services/dispersion (moving to the ETF share option factors), the data behind ports (issuer adapters in src/infrastructure/repositories/issuer_repo, IBKR option data in
src/infrastructure/repositories/ibkr_repo/finance/dispersion).

A run for a screening date:
  1. the ETF universe (P.02)            -> results_dir/<date>/universe.json + universe.csv
  2. the option screen (P.03 – P.07)    -> results_dir/<date>/candidates.json + candidates.csv (ranked)
     only when an IBKR host is configured (DISPERSION_IBKR_HOST ...), READ-ONLY on its own client id
  + the run manifest.

    python -m src.application.managers.project_managers.etf_dispersion_screener_project.project_manager [YYYY-MM-DD]
"""

import csv
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import date
from typing import Any, Dict, List, Optional

from src.application.managers.project_managers.etf_dispersion_screener_project import config as project_config
from src.application.managers.project_managers.project_manager import ProjectManager
from src.application.services.dispersion.dispersion_screening_service import Candidate, DispersionScreeningService
from src.application.services.dispersion.etf_universe_service import EtfUniverseService, UniverseResult
from src.application.services.dispersion.paper_validation_service import (
    PaperValidationService, Validation, priced,
)
from src.application.services.misbuffet import run_manifest
from src.infrastructure.repositories.issuer_repo.ishares_holdings_source import ISharesHoldingsSource
from src.infrastructure.repositories.issuer_repo.ssga_holdings_source import SSGAHoldingsSource

ISSUER_SOURCES = {'ishares': ISharesHoldingsSource, 'ssga': SSGAHoldingsSource}


class EtfDispersionScreenerProjectManager(ProjectManager):

    def __init__(self, config: Optional[Dict[str, Any]] = None, screen=None, sources=None, market_data=None):
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
        self.market_data = market_data
        self._client = None
        self._sleep = time.sleep

    def _connect_market_data(self):
        ib = self.config.get('ibkr') or {}
        if self.market_data is not None or not ib.get('host'):
            return self.market_data
        from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
        from src.infrastructure.repositories.ibkr_repo.finance.dispersion.ibkr_option_market_data import (
            IBKROptionMarketData,
        )
        self._client = IBTWSClient(ib['host'], int(ib['port']), int(ib['client_id']))
        if not self._client.connect_to_tws():
            raise ConnectionError(f"IBKR {ib['host']}:{ib['port']} not available")
        time.sleep(2)
        self.market_data = IBKROptionMarketData(self._client, max_lines=int(ib.get('max_lines', 40)),
                                                timeout_seconds=float(ib.get('timeout_seconds', 12.0)),
                                                pause_seconds=float(ib.get('pause_seconds', 0.2)))
        return self.market_data

    def _validate(self, market_data, candidates: List[Candidate], screening_date: date, out_dir: str) -> None:
        """P.11 read-only: re-quote the best priced candidates after validate_after_seconds (no orders)."""
        delay = self.config.get('validate_after_seconds')
        if delay is None or not priced(candidates):
            return
        print(f"validation: re-quoting in {delay:g} s", flush=True)
        self._sleep(delay)
        validations = PaperValidationService(market_data, require_live=not self.screen.allow_frozen_quotes).validate(
            candidates, screening_date, top=int(self.config.get('validate_top', 5)))
        write_validation(out_dir, validations)
        for v in validations:
            print(f"validation {v.etf}: {v.check.legs_filled}/{len(v.check.legs)} legs would fill, net premium "
                  f"{v.screened_net_premium:,.2f} -> {v.requoted_net_premium}", flush=True)

    def run(self, screening_date: Optional[date] = None, tickers=None):
        screening_date = screening_date or date.today()
        out_dir = os.path.join(self.config['results_dir'], screening_date.isoformat())
        manifest = run_manifest.build_manifest('screen', 'ETF dispersion screener',
                                               {**self.config, 'screen': asdict(self.screen)}, (screening_date,))
        run_manifest.write_manifest(out_dir, manifest)
        candidates: List[Candidate] = []
        try:
            result = self.universe_service.build(screening_date, tickers, progress=lambda m: print(m, flush=True))
            write_universe(out_dir, result)
            print(f"{screening_date} universe: {result.counts()}", flush=True)
            market_data = self._connect_market_data()
            if market_data is not None:
                service = DispersionScreeningService(market_data, self.screen)
                lookups = os.path.join(out_dir, 'lookups.json')
                if os.path.exists(lookups):
                    with open(lookups, encoding='utf-8') as f:
                        if service.import_lookups(json.load(f), screening_date):
                            print(f"lookups reused from {lookups} (quotes only)", flush=True)
                etfs = [(e.listing.ticker, e.listing.name, e.constituents) for e in result.eligible]
                candidates = service.screen(etfs, screening_date, progress=lambda m: print(m, flush=True))
                with open(lookups, 'w', encoding='utf-8') as f:
                    json.dump(service.export_lookups(screening_date), f)
                write_candidates(out_dir, candidates)
                counts: Dict[str, int] = {}
                for c in candidates:
                    counts[c.status] = counts.get(c.status, 0) + 1
                print(f"{screening_date} screen: {counts} -> {out_dir}", flush=True)
                self._validate(market_data, candidates, screening_date, out_dir)
        except Exception as e:
            run_manifest.finish_manifest(out_dir, manifest, f"failed: {e!r}"[:300])
            raise
        finally:
            if self._client is not None:
                self._client.disconnect()
        run_manifest.finish_manifest(out_dir, manifest, "completed")
        return result, candidates


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
    _write_csv(os.path.join(out_dir, 'universe.csv'), [{k: v for k, v in r.items() if k != 'weights'} for r in rows])


def _round(x, n=6):
    return None if x is None else round(float(x), n)


def candidate_row(c: Candidate) -> Dict[str, Any]:
    """Section 15 results table (+ the fields behind it)."""
    o, p, s = c.etf_option, c.premium, c.sizing
    return {
        'etf': c.etf, 'name': c.name, 'status': c.status, 'reasons': '; '.join(c.reasons),
        'constituents': len(c.constituents), 'coverage': _round(c.coverage, 4),
        'weight_coverage': _round(c.weight_coverage, 4), 'expiry': str(c.expiry) if c.expiry else None, 'dte': c.dte,
        'etf_spot': _round(c.etf_spot, 4), 'etf_strike': o.contract.strike if o else None,
        'etf_call_bid': o.quote.bid if o else None, 'etf_call_ask': o.quote.ask if o else None,
        'etf_iv': _round(c.etf_iv, 4), 'weighted_constituent_iv': _round(c.weighted_iv, 4),
        'implied_correlation': _round(c.implied_correlation, 4),
        'implied_correlation_etf_bid': _round(c.implied_correlation_etf_bid, 4),
        'implied_correlation_etf_ask': _round(c.implied_correlation_etf_ask, 4),
        'etf_bid_iv': _round(o.greeks.bid_implied_vol, 4) if o else None,
        'etf_ask_iv': _round(o.greeks.ask_implied_vol, 4) if o else None,
        'etf_contracts': s.etf_contracts if s else None,
        'whole_contract_etf_calls': s.whole_contract_etf_calls if s else None,
        'etf_call_proceeds': _round(p.short_proceeds, 2) if p else None,
        'constituent_call_cost': _round(p.long_cost, 2) if p else None,
        'net_premium': _round(p.net_premium, 2) if p else None,
        'net_premium_pct': _round(p.net_premium_pct, 4) if p else None,
        'mid_net_premium': _round(p.mid_net_premium, 2) if p else None,
        'transaction_cost': _round(p.transaction_cost, 2) if p else None,
        'reverse_etf_call_cost': _round(c.reverse.etf_call_cost, 2) if c.reverse else None,
        'reverse_constituent_proceeds': _round(c.reverse.constituent_proceeds, 2) if c.reverse else None,
        'reverse_net_premium': _round(c.reverse.net_premium, 2) if c.reverse else None,
        'reverse_net_premium_pct': _round(c.reverse.net_premium_pct, 4) if c.reverse else None,
        'etf_dollar_delta': _round(-s.short_dollar_delta, 2) if s and s.short_dollar_delta is not None else None,
        'basket_dollar_delta': _round(s.long_dollar_delta, 2) if s else None,
        'net_dollar_delta': _round(s.net_dollar_delta, 2) if s else None,
        'net_delta_pct': _round(s.relative_net_delta, 4) if s else None,
        'vega_etf': _round(c.vega_etf, 2), 'vega_basket': _round(c.vega_basket, 2),
        'gamma_etf': _round(c.gamma_etf, 4), 'gamma_basket': _round(c.gamma_basket, 4),
        'theta_etf': _round(c.theta_etf, 2), 'theta_basket': _round(c.theta_basket, 2),
        'notional': _round(c.notional, 2), 'capital_requirement': _round(c.capital_requirement, 2),
        'liquidity_avg_spread': _round(c.liquidity_score, 4),
        'holdings_as_of': str(c.holdings_as_of) if c.holdings_as_of else None,
        'holdings_source': c.holdings_source,
        'etf_quote_time': str(o.quote.quote_time) if o else None, 'greeks_source': o.greeks.source if o else None,
        'screened_at': str(c.screened_at) if c.screened_at else None,
    }


def constituent_rows(c: Candidate) -> List[Dict[str, Any]]:
    """Section 16 detail table."""
    rows = []
    for r in c.constituents:
        o = r.option
        rows.append({
            'ticker': r.symbol, 'weight': _round(r.weight), 'status': r.status, 'price': _round(r.spot, 4),
            'expiry': str(r.expiry) if r.expiry else None, 'strike': r.strike, 'multiplier': r.multiplier,
            'call_bid': o.quote.bid if o else None, 'call_ask': o.quote.ask if o else None,
            'iv': _round(o.greeks.implied_vol, 4) if o else None,
            'bid_iv': _round(o.greeks.bid_implied_vol, 4) if o else None,
            'ask_iv': _round(o.greeks.ask_implied_vol, 4) if o else None,
            'call_proceeds_at_bid': _round(r.contracts * r.multiplier * o.quote.bid, 2)
            if o and r.contracts is not None and o.quote.bid else None, 'delta': _round(o.greeks.delta, 4) if o else None,
            'contracts': _round(r.contracts, 4), 'dollar_delta': _round(r.dollar_delta, 2), 'call_cost': _round(r.call_cost, 2),
            'spread_pct': _round(o.quote.spread_pct, 4) if o else None, 'volume': o.quote.volume if o else None,
            'open_interest': o.open_interest if o else None,
            'quote_time': str(o.quote.quote_time) if o and o.quote.quote_time else None,
            'exceptions': '; '.join(r.exceptions), 'liquidity': '; '.join(r.liquidity),
        })
    return rows


def write_candidates(out_dir: str, candidates: List[Candidate]) -> None:
    os.makedirs(out_dir, exist_ok=True)
    rows = [candidate_row(c) for c in candidates]
    with open(os.path.join(out_dir, 'candidates.json'), 'w', encoding='utf-8') as f:
        json.dump([{**row, 'constituent_legs': constituent_rows(c),
                    'scenarios': [{k: (_round(v, 2) if isinstance(v, float) else v) for k, v in sc.items()}
                                  for sc in c.scenarios]}
                   for row, c in zip(rows, candidates)], f, indent=1)
    _write_csv(os.path.join(out_dir, 'candidates.csv'), rows)


def write_validation(out_dir: str, validations: List[Validation]) -> None:
    os.makedirs(out_dir, exist_ok=True)
    rows = [v.row() for v in validations]
    with open(os.path.join(out_dir, 'validation.json'), 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=1)
    _write_csv(os.path.join(out_dir, 'validation.csv'), [{k: v for k, v in r.items() if k != 'leg_checks'}
                                                        for r in rows])


def _write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, 'w', encoding='utf-8', newline='') as f:
        if not rows:
            return
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    EtfDispersionScreenerProjectManager().run(day)
