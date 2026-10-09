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


class STMPriceHistoryReader:

    def __init__(self, factory, close_factor_name: str = "close",
                 factor_type: str = "company_share_factor", frequency: Optional[str] = "1d"):
        self.factory = factory
        self.close_factor_name = close_factor_name
        self.factor_type = factor_type
        self.frequency = frequency

    def _close_factor_ids(self, session) -> List[int]:
        from src.infrastructure.models.factor.factor import FactorModel
        q = session.query(FactorModel.id).filter(
            FactorModel.name == self.close_factor_name,
            FactorModel.factor_type == self.factor_type,
        )
        if self.frequency is not None:
            q = q.filter(FactorModel.frequency == self.frequency)
        return [row[0] for row in q.all()]

    def load_close_panel(self, assets: Dict[int, str], start=None, end=None) -> pd.DataFrame:
        """
        Return a DataFrame (index = session date, columns = tickers) of closes
        for ``assets`` = {entity_id: ticker}, restricted to start <= date <= end.
        Missing observations stay NaN (alignment is the dataset builder's job).
        """
        from src.infrastructure.models.factor.factor_value import FactorValueModel

        session = self.factory.session
        factor_ids = self._close_factor_ids(session)
        columns = list(assets.values())
        if not factor_ids or not assets:
            return pd.DataFrame(columns=columns, dtype=float)

        q = session.query(FactorValueModel.entity_id, FactorValueModel.date, FactorValueModel.value).filter(
            FactorValueModel.factor_id.in_(factor_ids),
            FactorValueModel.entity_id.in_(list(assets.keys())),
        )
        if start is not None:
            q = q.filter(FactorValueModel.date >= pd.Timestamp(start).to_pydatetime())
        if end is not None:
            # inclusive of the whole end session
            q = q.filter(FactorValueModel.date < (pd.Timestamp(end).normalize() + pd.Timedelta(days=1)).to_pydatetime())

        records = []
        for entity_id, dt, value in q.all():
            try:
                px = float(str(value))
            except (TypeError, ValueError):
                continue
            ts = pd.Timestamp(dt)
            if ts.tzinfo is not None:
                ts = ts.tz_localize(None)
            records.append((ts.normalize(), assets[entity_id], px))

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
                 factor_type: str = "company_share_factor", frequency: Optional[str] = "1d"):
        self.history_service = history_service
        self.close_factor_name = close_factor_name
        self.factor_type = factor_type
        self.frequency = frequency

    def load_close_panel(self, assets: Dict[int, str], start=None, end=None) -> pd.DataFrame:
        panel = self.history_service.get_factor_value_panel(
            assets, factor_name=self.close_factor_name, factor_type=self.factor_type,
            frequency=self.frequency,
            start=pd.Timestamp(start).to_pydatetime() if start is not None else None,
            end=(pd.Timestamp(end).normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)).to_pydatetime()
            if end is not None else None,
        )
        if len(panel):
            panel.index = pd.DatetimeIndex(panel.index).normalize()
            panel = panel.groupby(level=0).last()
        return panel
