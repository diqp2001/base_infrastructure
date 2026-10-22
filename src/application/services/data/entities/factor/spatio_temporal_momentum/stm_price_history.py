"""
STMPriceHistoryReader — daily close panel from the existing factor_values
table (raw CompanyShare 'close' factor, daily frequency).

No separate price store is introduced: closes are the IBKR bars persisted by
the existing market-data pipeline.  A daily bar dated D is treated as known
after the close of D, so ``end`` is inclusive and callers must pass the last
COMPLETED session as the decision date.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Iterable, List, Optional

import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import bar_key, next_key


class STMPriceHistoryReader:

    def __init__(self, factory, close_factor_name: str = "close",
                 factor_type: str = "company_share_factor", frequency: Optional[str] = "1d",
                 bar_minutes: Optional[int] = None, subgroup: Optional[str] = None):
        self.subgroup = subgroup                 # one named series (e.g. OPTION_IMPLIED_VOLATILITY); None = prices
        self.factory = factory
        self.close_factor_name = close_factor_name
        self.factor_type = factor_type
        self.frequency = frequency
        self.bar_minutes = bar_minutes           # None: one row per session; e.g. 10: one row per 10-minute bar

    def _close_factor_ids(self, session) -> List[int]:
        return [fid for fid, _ in self._close_factors(session)]

    def _close_factors(self, session):
        """(factor id, rank) of every stored close series: rank = position in the reading order (BI-036: one
        series per IBKR whatToShow, MIDPOINT before TRADES), other whatToShow series next, legacy subgroups last."""
        from src.domain.entities.factor.source_policy import is_what_to_show, reading_order
        from src.infrastructure.models.factor.factor import FactorModel
        order = list(reading_order("CompanyShare", "price", self.close_factor_name))
        q = session.query(FactorModel.id, FactorModel.subgroup).filter(
            FactorModel.name == self.close_factor_name,
            FactorModel.factor_type == self.factor_type,
        )
        if self.frequency is not None:
            q = q.filter(FactorModel.frequency == self.frequency)
        if self.subgroup is not None:
            q = q.filter(FactorModel.subgroup == self.subgroup)
        else:                                    # never a volatility / rate series in place of a price
            from src.domain.entities.factor.source_policy import NON_PRICE_WHAT_TO_SHOW
            q = q.filter(~FactorModel.subgroup.in_(list(NON_PRICE_WHAT_TO_SHOW)))
        ranked = []
        for factor_id, subgroup in q.all():
            rank = (order.index(subgroup) if subgroup in order else
                    len(order) if is_what_to_show(subgroup) else len(order) + 1)
            ranked.append((factor_id, rank))
        return ranked

    def load_close_panel(self, assets: Dict[int, str], start=None, end=None) -> pd.DataFrame:
        """
        Return a DataFrame (index = session date, columns = tickers) of closes
        for ``assets`` = {entity_id: ticker}, restricted to start <= date <= end.
        Missing observations stay NaN (alignment is the dataset builder's job).
        """
        from src.infrastructure.models.factor.factor_value import FactorValueModel

        session = self.factory.session
        ranks = dict(self._close_factors(session))
        factor_ids = list(ranks)
        columns = list(assets.values())
        if not factor_ids or not assets:
            return pd.DataFrame(columns=columns, dtype=float)

        q = session.query(FactorValueModel.entity_id, FactorValueModel.date, FactorValueModel.value,
                          FactorValueModel.factor_id).filter(
            FactorValueModel.factor_id.in_(factor_ids),
            FactorValueModel.entity_id.in_(list(assets.keys())),
        )
        if start is not None:
            q = q.filter(FactorValueModel.date >= pd.Timestamp(start).to_pydatetime())
        if end is not None:
            # inclusive of the whole end session
            q = q.filter(FactorValueModel.date < next_key(end, self.bar_minutes).to_pydatetime())

        rows = q.all()
        # one series per asset: the best-ranked series that has data in the window (never a mix of types)
        best = {}
        for entity_id, _, _, factor_id in rows:
            rank = ranks.get(factor_id, 99)
            best[entity_id] = min(best.get(entity_id, rank), rank)
        records = []
        for entity_id, dt, value, factor_id in rows:
            if ranks.get(factor_id, 99) != best[entity_id]:
                continue
            try:
                px = float(str(value))
            except (TypeError, ValueError):
                continue
            ts = pd.Timestamp(dt)
            if ts.tzinfo is not None:
                ts = ts.tz_localize(None)
            records.append((bar_key(ts, self.bar_minutes), assets[entity_id], px))

        if not records:
            return pd.DataFrame(columns=columns, dtype=float)
        frame = pd.DataFrame(records, columns=["date", "asset", "close"])
        # One value per session: keep the last stored bar of the day
        panel = frame.groupby(["date", "asset"])["close"].last().unstack("asset")
        return panel.reindex(columns=columns).sort_index()

    def history_counts(self, assets: Dict[int, str], end=None) -> Dict[str, int]:
        panel = self.load_close_panel(assets, end=end)
        return {a: int(panel[a].notna().sum()) if a in panel else 0 for a in assets.values()}


class STMFrontierPriceReader:
    """
    Same interface as STMPriceHistoryReader, but every read goes through the
    Misbuffet MarketDataHistoryService frontier: nothing that was not known
    at the current simulation time can be returned, whatever ``end`` the
    caller passes.  This is the reader used by the trading cycle (backtest
    and live).
    """

    def __init__(self, history_service, close_factor_name: str = "close",
                 factor_type: str = "company_share_factor", frequency: Optional[str] = "1d",
                 bar_minutes: Optional[int] = None, subgroup: Optional[str] = None):
        self.subgroup = subgroup                 # one named series; None = prices (non-price series excluded)
        self.history_service = history_service
        self.close_factor_name = close_factor_name
        self.factor_type = factor_type
        self.frequency = frequency
        self.bar_minutes = bar_minutes

    def load_close_panel(self, assets: Dict[int, str], start=None, end=None) -> pd.DataFrame:
        from src.domain.entities.factor.source_policy import NON_PRICE_WHAT_TO_SHOW
        panel = self.history_service.get_factor_value_panel(
            assets, factor_name=self.close_factor_name, factor_type=self.factor_type,
            frequency=self.frequency, subgroup=self.subgroup,
            exclude_subgroups=() if self.subgroup is not None else tuple(NON_PRICE_WHAT_TO_SHOW),
            start=pd.Timestamp(start).to_pydatetime() if start is not None else None,
            end=(next_key(end, self.bar_minutes) - pd.Timedelta(microseconds=1)).to_pydatetime()
            if end is not None else None,
        )
        if len(panel):
            panel.index = pd.DatetimeIndex([bar_key(t, self.bar_minutes) for t in panel.index])
            panel = panel.groupby(level=0).last()
        return panel
