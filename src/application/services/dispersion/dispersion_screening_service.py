"""
Dispersion screener P.03 – P.07: from the eligible ETF universe (P.02) to ranked candidates.

Per ETF: resolve the ETF and its constituents as tradeable US shares, pick the ETF's standard option class, its
expiry (nearest TARGET_DTE in [MIN_DTE, MAX_DTE]) and ATM call; the same expiry and the ATM call of every
constituent (exceptions recorded); quote every option (IBKR model greeks); apply data quality, liquidity and
MIN_OPTION_COVERAGE; size the long calls to dollar-delta neutrality in whole contracts; compare the ETF call bid with
the constituent calls' ask cost. A candidate is an OPPORTUNITY when net premium >= 0 and the whole-contract sizing is
within DELTA_TOLERANCE; every other outcome is kept with its reason.

Market data comes through OptionMarketDataPort only; nothing here knows IBKR.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from src.domain.entities.finance.dispersion.dispersion_trade import (
    Leg, Premium, Sizing, WeightedComparison, implied_correlation, premium, scenarios, size_fractional,
    size_whole_contracts, weighted_comparison, weighted_implied_vol,
)
from src.domain.entities.finance.dispersion.etf_holdings import ConstituentWeights
from src.domain.entities.finance.dispersion.option_data import (
    OptionChain, OptionContractSpec, OptionQuote, Underlying, UnderlyingQuote,
)
from src.domain.entities.finance.dispersion.option_selection import (
    constituent_expiry, select_atm_strike, select_common_expiry, standard_chain,
)
from src.domain.entities.finance.dispersion.quote_checks import (
    freshness_problems, option_liquidity_problems, option_quality_problems,
)
from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig
from src.domain.ports.finance.dispersion.option_market_data_port import MarketDataUnavailable, OptionMarketDataPort

logger = logging.getLogger(__name__)

OPPORTUNITY = "opportunity"
DATA_UNAVAILABLE = "data unavailable"          # the source did not answer: no verdict on the ETF
MAX_CONSECUTIVE_UNAVAILABLE = 3               # then the source is down: the screen stops asking
SHARE_TYPES = {"COMMON", "ADR", "REIT", "ETF", "MLP", "NY REG SHRS", "GDR", "TRACKING STK", "ROYALTY TRST", ""}


@dataclass
class ConstituentResult:
    symbol: str
    weight: float                                  # ETF weight (normalised over all equity constituents)
    status: str                                    # "ok" | the reason it is not usable
    spot: Optional[float] = None
    expiry: Optional[date] = None
    strike: Optional[float] = None
    multiplier: Optional[float] = None
    option: Optional[OptionQuote] = None
    exceptions: List[str] = field(default_factory=list)
    liquidity: List[str] = field(default_factory=list)
    contracts: Optional[float] = None
    dollar_delta: Optional[float] = None
    call_cost: Optional[float] = None


@dataclass
class Candidate:
    etf: str
    name: str
    status: str                                    # OPPORTUNITY | "rejected" | "not screenable" | DATA_UNAVAILABLE
    reasons: List[str] = field(default_factory=list)
    constituents: List[ConstituentResult] = field(default_factory=list)
    holdings_as_of: Optional[date] = None
    holdings_source: str = ""
    etf_spot: Optional[float] = None
    etf_option: Optional[OptionQuote] = None
    expiry: Optional[date] = None
    dte: Optional[int] = None
    coverage: Optional[float] = None               # usable constituents / constituents
    weight_coverage: Optional[float] = None        # weight of the usable constituents
    sizing: Optional[Sizing] = None                # whole contracts (executable)
    fractional: Optional[Sizing] = None            # exact neutrality (reference)
    premium: Optional[Premium] = None
    comparison: Optional[WeightedComparison] = None
    etf_iv: Optional[float] = None
    weighted_iv: Optional[float] = None
    implied_correlation: Optional[float] = None
    vega_etf: Optional[float] = None               # dollar vega per 1 vol point of the short ETF calls (positive)
    vega_basket: Optional[float] = None
    gamma_etf: Optional[float] = None
    gamma_basket: Optional[float] = None
    theta_etf: Optional[float] = None
    theta_basket: Optional[float] = None
    notional: Optional[float] = None               # ETF shares under the short calls x ETF price
    capital_requirement: Optional[float] = None    # premium paid for the long calls (short call margin excluded)
    liquidity_score: Optional[float] = None        # average bid/ask spread % of every leg (lower = better)
    screened_at: Optional[datetime] = None
    scenarios: List[dict] = field(default_factory=list)   # payoff at maturity (section 18)

    @property
    def rank_key(self):
        """Transparent ranking (section 14): net premium, net premium %, liquidity, coverage, transaction cost,
        ETF IV - weighted constituent IV."""
        p = self.premium
        return (self.status != OPPORTUNITY,
                -(p.net_premium if p else float("-inf")), -(p.net_premium_pct if p else float("-inf")),
                self.liquidity_score if self.liquidity_score is not None else float("inf"),
                -(self.coverage or 0.0), p.transaction_cost if p else float("inf"),
                -((self.etf_iv or 0.0) - (self.weighted_iv or 0.0)))


class DispersionScreeningService:

    def __init__(self, market_data: OptionMarketDataPort, config: DispersionScreenConfig,
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.md = market_data
        self.config = config
        self.now = now
        self._underlyings: Dict[str, Optional[Underlying]] = {}
        self._chains: Dict[str, List[OptionChain]] = {}
        self._strikes: Dict[tuple, Sequence[float]] = {}

    # ---- cached lookups ----
    def _resolve(self, symbols: Sequence[str], screening_date: date) -> Dict[str, Optional[Underlying]]:
        missing = [s for s in symbols if s not in self._underlyings]
        if missing:
            self._underlyings.update(self.md.resolve_underlyings(missing, screening_date))
        return {s: self._underlyings.get(s) for s in symbols}

    def _chain(self, underlying: Underlying, screening_date: date) -> Tuple[Optional[OptionChain], List[str]]:
        if underlying.symbol not in self._chains:
            self._chains[underlying.symbol] = self.md.option_chains(underlying, screening_date)
        return standard_chain(self._chains[underlying.symbol])

    def _listed_strikes(self, chain: OptionChain, expiry: date, screening_date: date) -> Sequence[float]:
        key = (chain.underlying, chain.trading_class, expiry)
        if key not in self._strikes:
            self._strikes[key] = self.md.listed_strikes(chain, expiry, "C", screening_date)
        return self._strikes[key]

    # ---- screen ----
    def screen(self, etfs: Sequence[Tuple[str, str, ConstituentWeights]], screening_date: date,
               progress: Callable[[str], None] = lambda m: None) -> List[Candidate]:
        out = []
        unavailable = 0
        for ticker, name, weights in etfs:
            if unavailable >= MAX_CONSECUTIVE_UNAVAILABLE:
                candidate = Candidate(ticker, name, DATA_UNAVAILABLE,
                                      [f"not screened: market data stopped answering ({unavailable} ETFs in a row)"])
                out.append(candidate)
                continue
            try:
                candidate = self.screen_etf(ticker, name, weights, screening_date)
                unavailable = 0
            except MarketDataUnavailable as e:
                unavailable += 1
                candidate = Candidate(ticker, name, DATA_UNAVAILABLE, [f"market data unavailable: {e}"[:200]])
            except Exception as e:                      # one ETF's failure never stops the screen
                logger.exception("screening %s failed", ticker)
                candidate = Candidate(ticker, name, "not screenable", [f"error: {e!r}"[:200]])
            progress(f"{ticker}: {candidate.status} {'; '.join(candidate.reasons)[:120]}")
            out.append(candidate)
        return sorted(out, key=lambda c: c.rank_key)

    def screen_etf(self, ticker: str, name: str, weights: ConstituentWeights, screening_date: date) -> Candidate:
        cfg = self.config
        c = Candidate(ticker, name, "not screenable", holdings_as_of=weights.as_of, holdings_source=weights.source,
                      screened_at=self.now())
        resolved = self._resolve([ticker] + list(weights.weights), screening_date)
        etf_u = resolved[ticker]
        if etf_u is None:
            c.reasons.append("ETF not found as a US-listed share at the broker")
            return c
        results = {s: ConstituentResult(s, w, "ok") for s, w in weights.weights.items()}
        for s, r in results.items():
            u = resolved[s]
            if u is None:
                r.status = "not a US-listed share at the broker"
            elif (u.stock_type or "").upper() not in SHARE_TYPES:
                r.status = f"not a share ({u.stock_type})"
        c.constituents = list(results.values())
        if not self._coverage_possible(c):
            return c

        # ETF leg
        etf_chain, notes = self._chain(etf_u, screening_date)
        if etf_chain is None:
            c.reasons.append("the ETF has no listed options")
            return c
        # constituent chains, then the expiry most of them share with the ETF
        chains: Dict[str, OptionChain] = {}
        for r in c.constituents:
            if r.status != "ok":
                continue
            chain, chain_notes = self._chain(resolved[r.symbol], screening_date)
            r.exceptions += [n for n in chain_notes if n != "no listed options"]
            if chain is None:
                r.status = "no listed options"
                continue
            chains[r.symbol] = chain
        c.expiry = select_common_expiry(etf_chain.expirations, [ch.expirations for ch in chains.values()],
                                        screening_date, cfg)
        if c.expiry is None:
            c.reasons.append(f"no ETF expiry within {cfg.min_dte}-{cfg.max_dte} days")
            return c
        c.dte = (c.expiry - screening_date).days
        for r in c.constituents:
            if r.status != "ok":
                continue
            chain = chains[r.symbol]
            choice = constituent_expiry(chain.expirations, c.expiry, screening_date, cfg)
            if choice.exception:
                r.exceptions.append(choice.exception)
            if choice.expiry is None:
                r.status = choice.exception
                continue
            r.expiry, r.multiplier = choice.expiry, chain.multiplier  # strikes picked once the spot is known
        if not self._coverage_possible(c):
            return c

        # underlying quotes -> ATM strikes
        legs_u = [etf_u] + [resolved[r.symbol] for r in c.constituents if r.status == "ok"]
        spots = self.md.underlying_quotes(legs_u, screening_date)
        etf_quote = spots.get(ticker)
        if etf_quote is None or etf_quote.price is None:
            c.reasons.append("no ETF price")
            return c
        stale = freshness_problems(etf_quote.quote, self.now(), cfg)
        if stale:
            c.reasons.append("ETF price: " + "; ".join(stale))
            return c
        c.etf_spot = etf_quote.price
        etf_strike = select_atm_strike(self._listed_strikes(etf_chain, c.expiry, screening_date), c.etf_spot)
        if etf_strike is None:
            c.reasons.append(f"no ETF call listed for {c.expiry}")
            return c
        specs = {ticker: OptionContractSpec(ticker, c.expiry, etf_strike, "C", etf_chain.multiplier,
                                            etf_chain.trading_class)}
        for r in c.constituents:
            if r.status != "ok":
                continue
            q: Optional[UnderlyingQuote] = spots.get(r.symbol)
            problems = freshness_problems(q.quote, self.now(), cfg) if q and q.price else ["no price"]
            if problems:
                r.status = "price: " + "; ".join(problems)
                continue
            r.spot = q.price
            r.strike = select_atm_strike(self._listed_strikes(chains[r.symbol], r.expiry, screening_date), r.spot)
            if r.strike is None:
                r.status = f"no call listed for {r.expiry}"
                continue
            specs[r.symbol] = OptionContractSpec(r.symbol, r.expiry, r.strike, "C", r.multiplier,
                                                 chains[r.symbol].trading_class)
        if not self._coverage_possible(c):
            return c

        # option quotes
        quotes = self.md.option_quotes(list(specs.values()), screening_date)
        etf_option = quotes.get(specs[ticker].key)
        if etf_option is None:
            c.reasons.append("no ETF option quote")
            return c
        c.etf_option = etf_option
        problems = option_quality_problems(etf_option, self.now(), cfg)
        problems += option_liquidity_problems(etf_option, cfg, is_etf=True)
        if problems:
            c.reasons.append("ETF call: " + "; ".join(problems))
            return c
        illiquid = []
        for r in c.constituents:
            if r.status != "ok":
                continue
            r.option = quotes.get(specs[r.symbol].key)
            if r.option is None:
                r.status = "no option quote"
                continue
            quality = option_quality_problems(r.option, self.now(), cfg)
            if quality:
                r.status = "; ".join(quality)
                continue
            r.liquidity = option_liquidity_problems(r.option, cfg, is_etf=False)
            if r.liquidity:
                illiquid.append(r.symbol)
        if illiquid and not cfg.allow_illiquid_constituents:
            c.status = "rejected"
            c.reasons.append(f"illiquid constituent options: {', '.join(illiquid[:8])}")
        if not self._coverage_possible(c):
            return c
        self._price_trade(c, etf_chain)
        return c

    def _coverage_possible(self, c: Candidate) -> bool:
        usable = [r for r in c.constituents if r.status == "ok"]
        c.coverage = len(usable) / len(c.constituents) if c.constituents else 0.0
        c.weight_coverage = sum(r.weight for r in usable)
        if c.coverage < self.config.min_option_coverage:
            c.reasons.append(f"option coverage {c.coverage:.0%} < {self.config.min_option_coverage:.0%} "
                             f"({len(c.constituents) - len(usable)} of {len(c.constituents)} constituents unusable)")
            return False
        return True

    def _price_trade(self, c: Candidate, etf_chain: OptionChain) -> None:
        cfg = self.config
        o = c.etf_option
        etf = Leg(c.etf, c.etf_spot, o.contract.strike, etf_chain.multiplier, o.greeks.delta, o.quote.bid,
                  o.quote.ask, 1.0, o.greeks.implied_vol, o.greeks.gamma, o.greeks.vega, o.greeks.theta)
        usable = [r for r in c.constituents if r.status == "ok"]
        covered = sum(r.weight for r in usable)
        legs = [Leg(r.symbol, r.spot, r.strike, r.multiplier, r.option.greeks.delta, r.option.quote.bid,
                    r.option.quote.ask, r.weight / covered, r.option.greeks.implied_vol, r.option.greeks.gamma,
                    r.option.greeks.vega, r.option.greeks.theta) for r in usable]
        if covered < 0.999:
            c.reasons.append(f"weights renormalised over the usable constituents ({covered:.1%} of the ETF)")
        c.fractional = size_fractional(etf, legs)
        c.sizing = size_whole_contracts(etf, legs, cfg)
        c.premium = premium(etf, legs, c.sizing)
        c.comparison = weighted_comparison(etf, legs)
        c.etf_iv, c.weighted_iv = etf.implied_vol, weighted_implied_vol(legs)
        c.implied_correlation = implied_correlation(etf.implied_vol, legs)
        by_symbol = {leg.symbol: leg for leg in legs}
        for r in usable:
            leg, q = by_symbol[r.symbol], c.sizing.positions[r.symbol]
            r.contracts, r.dollar_delta, r.call_cost = q, leg.dollar_delta(q), q * leg.multiplier * leg.ask
        n = c.sizing.etf_contracts

        def total(attr, items):
            values = [(qty, mult, getattr(leg, attr)) for qty, mult, leg in items]
            return None if any(v is None for _, _, v in values) else sum(q * m * v for q, m, v in values)

        c.vega_etf = total("vega", [(n, etf.multiplier, etf)])
        c.gamma_etf = total("gamma", [(n, etf.multiplier, etf)])
        c.theta_etf = total("theta", [(n, etf.multiplier, etf)])
        basket = [(c.sizing.positions[l.symbol], l.multiplier, l) for l in legs]
        c.vega_basket, c.gamma_basket, c.theta_basket = total("vega", basket), total("gamma", basket), total("theta", basket)
        c.notional = n * etf.multiplier * etf.spot
        c.capital_requirement = c.premium.long_cost
        spreads = [o.quote.spread_pct] + [r.option.quote.spread_pct for r in usable]
        c.liquidity_score = sum(spreads) / len(spreads)
        c.scenarios = scenarios(etf, legs, c.sizing, c.premium.net_premium)

        if c.status == "rejected":
            return                                       # illiquid constituents: priced for information only
        if abs(c.sizing.relative_net_delta) > cfg.delta_tolerance or (
                c.sizing.zero_positions and cfg.require_every_constituent):
            c.status = "rejected"
            c.reasons.append(f"no whole-contract sizing within the delta tolerance up to {cfg.max_etf_contracts} "
                             f"ETF calls (best {c.sizing.relative_net_delta:+.1%}, zero: "
                             f"{', '.join(c.sizing.zero_positions[:5]) or '-'})")
        elif c.premium.net_premium < 0:
            c.status = "rejected"
            c.reasons.append(f"net premium {c.premium.net_premium:,.0f} < 0 (ETF call bid below the constituent "
                             f"calls' ask cost)")
        else:
            c.status = OPPORTUNITY
