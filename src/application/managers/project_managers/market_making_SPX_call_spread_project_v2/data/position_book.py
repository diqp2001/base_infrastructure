"""
PositionBook — open option positions of the book, with their greeks at a time.

Same reads as the original algorithm's _load_strategy_positions /
_collect_option_positions / _load_position_market_data, moved out of the
algorithm so the trading cycle can use them in backtest and live:

* ``load_positions(time)`` — every CompanyShareOptionPortfolioHolding whose
  position quantity is non-zero, as the position dicts the Strategy expects
  (signed ``size``, strike, days to expiry measured at ``time``);
* ``market_data(positions, time)`` — delta / gamma / vega / implied vol / mid
  price of each option symbol, resolved by FactorValueResolutionService at ``time``.

NB (kept from the original): option holdings are read for ALL portfolios,
because the option sub-portfolios are not linked to the main portfolio by a
holding row.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

# greek / price name -> factor repository key
FACTOR_REPO_KEYS: Dict[str, str] = {
    'delta': 'CompanyShareOptionDeltaFactor',
    'gamma': 'CompanyShareOptionGammaFactor',
    'vega': 'CompanyShareOptionVegaFactor',
    'implied_vol': 'CompanyShareOptionImpliedVolFactor',
    'current_price': 'CompanyShareOptionMidPriceFactor',
}


class PositionBook:

    # dependency trees built per run for missing greeks (each one re-walks the resolution chain)
    MAX_EXPLANATIONS = 200

    def __init__(self, factory, session_provider, report=None):
        """``session_provider()`` returns the SQLAlchemy session of the portfolio repositories.
        ``report`` (utils.data_report.DataReport) records every greek that does not resolve, with its
        dependency tree."""
        self.factory = factory
        self.session_provider = session_provider
        self.report = report
        self._explained = 0
        self.logger = logging.getLogger(self.__class__.__name__)

    def _record_miss(self, resolver, factor, option, symbol, key, time, cause=None):
        """Add a missing greek to the report: root cause + dependency tree (bounded per run)."""
        if self.report is None:
            return
        tree = ""
        if cause is None and factor is not None and option is not None and self._explained < self.MAX_EXPLANATIONS:
            from src.application.services.data.entities.factor.factor_dependency_explainer import (
                FactorDependencyExplainer,
            )
            self._explained += 1
            try:
                node = FactorDependencyExplainer(resolver, self.factory).explain(factor, option, time)
                causes = list(dict.fromkeys(f"{c.factor} [{c.entity}] {c.status}: {c.detail}"
                                            for c in node.root_causes()))      # distinct, walk order
                cause = " | ".join(causes[:4]) or node.detail or "calculate() returned no value"
                tree = node.render()
            except Exception as e:
                cause = f"could not be explained: {e}"
        self.report.greek_missing(time, symbol, key, cause or "not explained (explanation limit reached)", tree)

    # ------------------------------------------------------------------ positions
    def load_positions(self, time: Optional[datetime] = None) -> Dict[str, Dict[str, Any]]:
        session = self.session_provider()
        if session is None:
            return {}
        from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import (
            CompanyShareOptionModel,
        )
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
        from src.infrastructure.models.finance.holding.company_share_option_portfolio_holding import (
            CompanyShareOptionPortfolioHoldingModel,
        )
        from src.infrastructure.models.finance.position import PositionModel

        now = time or datetime.now()
        out: Dict[str, Dict[str, Any]] = {}
        for h in session.query(CompanyShareOptionPortfolioHoldingModel).all():
            if not h.position_id:
                continue
            pos = session.query(PositionModel).filter_by(id=h.position_id).first()
            if not pos or (pos.quantity or 0) == 0:
                continue
            cso = session.query(CompanyShareOptionModel).filter_by(id=h.company_share_option_id).first()
            if cso is None:
                continue
            asset = session.query(FinancialAssetModel).filter_by(id=h.company_share_option_id).first()
            symbol = asset.symbol if asset else str(h.company_share_option_id)
            dte, tau = 30, 0.1
            if cso.expiry:
                try:
                    expiry = datetime.strptime(str(cso.expiry), '%Y%m%d')
                    dte = max(0, (expiry - now).days)
                    tau = dte / 365.25
                except ValueError:
                    pass
            position_id = f"cso_holding_{h.id}"
            out[position_id] = {
                'id': position_id,
                'symbol': symbol,
                'size': int(pos.quantity),
                'position_type': str(pos.position_type),
                'strikes': {'long': float(cso.strike_price) if cso.strike_price else None},
                'days_to_expiry': dte,
                'time_to_expiry': tau,
                'greeks': {},
                'entry_price': 0.0,
                'current_price': 0.0,
                'max_profit': 0.0,
                'max_loss': 0.0,
            }
        return out

    # ------------------------------------------------------------------ greeks
    def market_data(self, positions: Dict[str, Dict[str, Any]], time: datetime) -> Dict[str, Dict[str, Any]]:
        """{symbol: {'greeks': {delta, gamma, vega, implied_vol}, 'current_price': float | None}}"""
        if not self.factory or not positions:
            return {}
        from src.application.services.data.entities.factor import FactorValueResolutionService

        # A greek that does not resolve leaves the position without it, and the hedge then counts
        # the position as delta / gamma 0 — every miss is logged at WARNING, with the reason.
        cso_repo = self.factory.get_local_repository('CompanyShareOption')
        if not cso_repo:
            self.logger.warning("No CompanyShareOption repository: no greeks for %d position(s) at %s",
                                len(positions), time)
            return {}
        factor_entities: Dict[str, Any] = {}
        for key, repo_key in FACTOR_REPO_KEYS.items():
            try:
                repo = self.factory.get_local_repository(repo_key)
                factors = repo.get_all() if repo else None
                if factors:
                    factor_entities[key] = factors[0]
                else:
                    self.logger.warning("No %s factor definition stored: '%s' cannot be resolved", repo_key, key)
                    for symbol in {p.get('symbol') for p in positions.values() if p.get('symbol')}:
                        self._record_miss(None, None, None, symbol, key, time,
                                          cause=f"no {repo_key} factor definition stored")
            except Exception as e:
                self.logger.warning("Could not load factor repo %s ('%s' not resolved): %s", repo_key, key, e)
        if not factor_entities:
            return {}

        resolver = FactorValueResolutionService(factory=self.factory)
        result: Dict[str, Dict[str, Any]] = {}
        for symbol in {p.get('symbol') for p in positions.values() if p.get('symbol')}:
            try:
                option = cso_repo.get_by_symbol(symbol)
            except Exception as e:
                self.logger.warning("Option %s: entity lookup failed (%s) — no greeks at %s", symbol, e, time)
                continue
            if option is None:
                self.logger.warning("Option %s: not found in CompanyShareOption — no greeks at %s", symbol, time)
                for key in FACTOR_REPO_KEYS:
                    self._record_miss(resolver, None, None, symbol, key, time,
                                      cause="option not found in CompanyShareOption")
                continue
            greeks: Dict[str, float] = {}
            current_price = None
            for key, factor in factor_entities.items():
                try:
                    fv = resolver.resolve_factor_value(factor_entity=factor, entity=option, time_date=time)
                except Exception as e:
                    self.logger.warning("Option %s: %s resolution raised at %s: %s", symbol, key, time, e)
                    self._record_miss(resolver, factor, option, symbol, key, time, cause=f"resolution raised: {e}")
                    continue
                if fv is None or fv.value is None:
                    self.logger.warning(
                        "Option %s: %s did not resolve at %s (check its dependency chain: underlying value, "
                        "risk-free rate / dated SOFR contract, option price, implied vol)", symbol, key, time)
                    self._record_miss(resolver, factor, option, symbol, key, time)
                    continue
                if key == 'current_price':
                    current_price = float(fv.value)
                else:
                    greeks[key] = float(fv.value)
            result[symbol] = {'greeks': greeks, 'current_price': current_price}
        return result

    @staticmethod
    def enrich(positions: Dict[str, Dict[str, Any]], market_data: Dict[str, Dict[str, Any]]) -> None:
        """Merge resolved greeks / prices into the position dicts (in place)."""
        for pos in positions.values():
            mdata = market_data.get(pos.get('symbol'))
            if not mdata:
                continue
            pos.setdefault('greeks', {}).update(mdata.get('greeks', {}))
            if mdata.get('current_price') is not None:
                pos['current_price'] = mdata['current_price']
