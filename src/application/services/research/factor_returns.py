"""
FactorReturnService — the factor RETURN series a regression can use (never security characteristics).

Sources:
* imported files (FactorReturnFileStore): Kenneth R. French daily 3 / 5 factors, user CSVs, saved
  factor-mimicking portfolios of the factor research;
* ``local_market``: a CAPM market proxy built from stored daily closes —
      MKT_RF(t) = SPY close(t) / SPY close(t-1) - 1 - RF(t)
      RF(t)     = IRX(t-1) / 10 / 100 / 252      (CBOE IRX = 10 x the 13-week T-bill yield in percent, known at the
                                                  previous close, spread over 252 sessions)
  It is labelled a proxy: it is not the academic Mkt-RF (value-weighted CRSP market minus the one-month bill).
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from src.domain.entities.research.factor_models import MARKET_PROXY, MKT_RF, RF

LOCAL_MARKET = "local_market"


def market_proxy_from_closes(spy: pd.Series, irx: pd.Series) -> pd.DataFrame:
    """Daily MKT_RF and RF from SPY and IRX daily closes (index = session date). Nothing is filled: a session
    without both closes has no value."""
    spy = pd.Series(spy, dtype=float).sort_index()
    irx = pd.Series(irx, dtype=float).sort_index()
    sessions = spy.index.intersection(irx.index)
    spy, irx = spy.loc[sessions], irx.loc[sessions]
    rf = irx.shift(1) / 10.0 / 100.0 / 252.0
    mkt = spy / spy.shift(1) - 1.0
    frame = pd.DataFrame({MKT_RF: mkt - rf, RF: rf}).replace([np.inf, -np.inf], np.nan).dropna()
    frame.index.name = "date"
    return frame


class FactorReturnService:

    def __init__(self, store, market_closes: Optional[Callable[[], Dict[str, pd.Series]]] = None):
        """``market_closes()`` -> {'SPY': daily closes, 'IRX': daily closes} (read from the database)."""
        self.store = store
        self.market_closes = market_closes

    def available(self) -> List[Dict]:
        out = list(self.store.list())
        if self.market_closes is not None:
            out.append({"name": LOCAL_MARKET, "kind": MARKET_PROXY, "frequency": "D", "factors": [MKT_RF, RF],
                        "source": "stored daily closes: SPY return minus the IRX T-bill rate (a CAPM proxy, not the "
                                  "academic Mkt-RF)", "unit": "decimal"})
        return out

    def load(self, name: str, start=None, end=None) -> pd.DataFrame:
        if name == LOCAL_MARKET:
            if self.market_closes is None:
                raise LookupError("no database: the local market proxy is unavailable")
            closes = self.market_closes()
            if closes.get("SPY") is None or closes.get("IRX") is None or closes["SPY"].empty or closes["IRX"].empty:
                raise LookupError("the local market proxy needs stored daily SPY and IRX closes")
            frame = market_proxy_from_closes(closes["SPY"], closes["IRX"])
        else:
            frame = self.store.load(name)
        if start is not None:
            frame = frame[frame.index >= pd.Timestamp(start).normalize()]
        if end is not None:
            frame = frame[frame.index <= pd.Timestamp(end)]
        return frame


def database_market_closes(factory) -> Dict[str, pd.Series]:
    """SPY (CompanyShare) and IRX (Index) daily TRADES closes through the repositories."""
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
        STMPriceHistoryReader,
    )
    out: Dict[str, pd.Series] = {}
    for symbol, repo_key, factor_type in (("SPY", "CompanyShare", "company_share_factor"),
                                          ("IRX", "Index", "index_factor")):
        repo = factory.get_local_repository(repo_key)
        entity = repo.get_by_symbol(symbol) if repo is not None and hasattr(repo, "get_by_symbol") else None
        if entity is None:
            continue
        reader = STMPriceHistoryReader(factory, close_factor_name="close", factor_type=factor_type, frequency="1d")
        panel = reader.load_close_panel({int(entity.id): symbol}, start=pd.Timestamp("1990-01-01"))
        if symbol in panel:
            out[symbol] = panel[symbol].dropna()
    return out
