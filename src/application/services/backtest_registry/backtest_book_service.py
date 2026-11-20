"""
BacktestBookService — every backtest's book, drilled down (what /research/backtests shows). Read only.

    books()                      every backtest book: name, window, final value, return, the registry run and the
                                 strategy it belongs to when it has one (runs before 2026-11-18 only left their book)
    performance(id, metrics_fn)  daily value curve, drawdown, monthly returns, metrics
    holdings(id)                 positions after every trading day (quantity from the fills; value at the latest
                                 daily close known that day, else the last fill price), long / short / gross / net
                                 exposure, number of positions; holdings_at(date)
    trades(id, symbol, ...)      the share fills (cash legs left out)
    asset(id, symbol)            one instrument: quantity and value through time, its trades

Positions are rebuilt from the FILLED quantities of the book's orders (BUY +, SELL -); the engine's own position
rows only hold the last state.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from src.application.services.backtest_registry.research_result_service import daily_curve

CASH_TYPES = ("currency",)                      # asset types of the cash legs (left out of trades / holdings)


def _is_cash(fill: Dict[str, Any]) -> bool:
    kind = str(fill.get("asset_type") or "").replace("_", "").lower()
    return kind in CASH_TYPES or (fill.get("symbol") or "") in ("USD", "EUR", "CAD", "GBP")


def _signed(fill: Dict[str, Any]) -> float:
    qty = fill["filled"] if fill["filled"] else 0.0
    return qty if str(fill["side"]).upper() == "BUY" else -qty


def _naive_day(value) -> pd.Timestamp:
    """The calendar day of a stored timestamp (stored values carry a time zone; books do not): wall time kept."""
    ts = pd.Timestamp(value)
    return (ts.tz_localize(None) if ts.tzinfo is not None else ts).normalize()


def _points(series: pd.Series) -> List[List[Any]]:
    return [[pd.Timestamp(d).strftime("%Y-%m-%d"), None if pd.isna(v) else float(v)] for d, v in series.items()]


class BacktestBookService:

    def __init__(self, reader, runs=None, run_portfolios=None, experiments=None, strategies=None):
        self.reader = reader                        # BacktestBookReader
        self.runs, self.run_portfolios = runs, run_portfolios
        self.experiments, self.strategies = experiments, strategies

    # -- list -----------------------------------------------------------------------------------------------------
    def _run_of(self, portfolio_id: int):
        if self.run_portfolios is None:
            return None
        link = self.run_portfolios.get_by_portfolio(portfolio_id) if hasattr(
            self.run_portfolios, "get_by_portfolio") else None
        return self.runs.get_by_id(link.run_id) if link is not None and self.runs is not None else None

    def _strategy_of(self, run) -> Optional[Dict[str, Any]]:
        if run is None or not getattr(run, "strategy_experiment_id", None) or self.experiments is None:
            return None
        experiment = self.experiments.get_by_id(run.strategy_experiment_id)
        strategy = self.strategies.get_by_id(experiment.strategy_id) if experiment and self.strategies else None
        if strategy is None:
            return None
        return {"id": strategy.id, "name": strategy.name, "version": strategy.version,
                "experiment_id": experiment.id}

    def books(self) -> List[Dict[str, Any]]:
        out = []
        for b in self.reader.books():
            curve = daily_curve(self.reader_values(b["portfolio_id"]))
            run = self._run_of(b["portfolio_id"])
            first, last = (float(curve.iloc[0]), float(curve.iloc[-1])) if len(curve) else (None, None)
            out.append({**b, "start_value": first, "final_value": last,
                        "total_return": (last / first - 1) if first else None, "days": len(curve),
                        "run": run.to_dict() if run is not None else None, "strategy": self._strategy_of(run),
                        "live": "live" in (b["name"] or "").lower()})
        return sorted(out, key=lambda b: b["last"] or datetime.min, reverse=True)

    def reader_values(self, portfolio_id: int):
        from src.infrastructure.repositories.local_repo.backtest.research_result_repository import (
            PortfolioValueReader,
        )
        return PortfolioValueReader(self.reader.session).value_series(portfolio_id)

    def book(self, portfolio_id: int) -> Optional[Dict[str, Any]]:
        found = next((b for b in self.reader.books() if b["portfolio_id"] == portfolio_id), None)
        if found is None:
            return None
        run = self._run_of(portfolio_id)
        return {**found, "sub_portfolios": self.reader.sub_portfolios(portfolio_id),
                "run": run.to_dict() if run is not None else None, "strategy": self._strategy_of(run),
                "live": "live" in (found["name"] or "").lower()}

    # -- performance ------------------------------------------------------------------------------------------------
    def performance(self, portfolio_id: int, metrics_fn: Optional[Callable] = None) -> Dict[str, Any]:
        curve = daily_curve(self.reader_values(portfolio_id))
        if curve.empty:
            return {"equity": [], "drawdown": [], "monthly": [], "metrics": {}}
        returns = curve.pct_change().dropna()
        drawdown = curve / curve.cummax() - 1
        monthly = (curve.resample("ME").last().pct_change() if len(curve) > 1 else pd.Series(dtype=float))
        if len(monthly):                                             # first month: from the first value
            first_month = curve.resample("ME").last().iloc[0] / curve.iloc[0] - 1
            monthly.iloc[0] = first_month
        metrics: Dict[str, Any] = {}
        if metrics_fn is not None and len(returns):
            try:
                metrics = dict(metrics_fn(returns.tolist(), float(curve.iloc[0]), float(curve.iloc[-1])))
            except Exception as e:                                   # never break the page on a metric
                metrics = {"error": str(e)}
        metrics.setdefault("max_drawdown", float(drawdown.min()))
        return {"equity": _points(curve), "drawdown": _points(drawdown), "returns": _points(returns),
                "monthly": [{"month": d.strftime("%Y-%m"), "return": float(v)} for d, v in monthly.dropna().items()],
                "metrics": metrics, "start": curve.index[0], "end": curve.index[-1]}

    # -- holdings ---------------------------------------------------------------------------------------------------
    def _share_fills(self, portfolio_id: int, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        ids = [portfolio_id] + [p["portfolio_id"] for p in self.reader.sub_portfolios(portfolio_id)]
        return [f for f in self.reader.fills(ids, symbol=symbol) if not _is_cash(f) and f["filled"]]

    def _positions(self, portfolio_id: int, symbol: Optional[str] = None):
        """(quantity frame [day x symbol], value frame, book value series)."""
        fills = self._share_fills(portfolio_id, symbol)
        curve = daily_curve(self.reader_values(portfolio_id))
        if not fills:
            return pd.DataFrame(), pd.DataFrame(), curve
        frame = pd.DataFrame(fills)
        frame["day"] = [_naive_day(x) for x in frame["time"]]
        frame["signed"] = frame.apply(_signed, axis=1)
        days = sorted(set(frame["day"]) | set(curve.index))
        qty = (frame.pivot_table(index="day", columns="symbol", values="signed", aggfunc="sum")
               .reindex(days).fillna(0.0).cumsum())
        qty = qty.loc[:, (qty.abs() > 1e-9).any()]
        assets = frame.drop_duplicates("symbol").set_index("symbol")["asset_id"].to_dict()
        start, end = days[0] - timedelta(days=10), days[-1] + timedelta(days=1)
        closes = self.reader.closes([int(a) for a in assets.values() if a is not None], start, end)
        last_fill = frame.dropna(subset=["price"]).groupby(["day", "symbol"])["price"].last().unstack()
        prices = pd.DataFrame(index=days)
        for sym, asset_id in assets.items():
            series = pd.Series({_naive_day(d): v for d, v in closes.get(asset_id, [])}, dtype=float)
            series = series[~series.index.duplicated(keep="last")].sort_index()
            # the close known on a day: that day's close is stamped at the bar's start, so <= day is the latest one
            marked = series.reindex(sorted(set(series.index) | set(days))).ffill().reindex(days)
            fill_px = last_fill[sym].reindex(days).ffill() if sym in last_fill else None
            prices[sym] = marked.fillna(fill_px) if fill_px is not None else marked
        values = qty * prices.reindex(columns=qty.columns)
        return qty, values, curve

    def holdings(self, portfolio_id: int) -> Dict[str, Any]:
        qty, values, curve = self._positions(portfolio_id)
        if qty.empty:
            return {"dates": [], "exposure": {}, "positions": {}, "symbols": [], "history": []}
        long_ = values.where(values > 0, 0).sum(axis=1)
        short = values.where(values < 0, 0).sum(axis=1)
        book = curve.reindex(values.index).ffill()
        count = (qty.abs() > 1e-9).sum(axis=1)
        exposure = {"long": _points(long_), "short": _points(short), "gross": _points(long_ - short),
                    "net": _points(long_ + short),
                    "gross_pct": _points(((long_ - short) / book).where(book > 0)) if len(book) else []}
        # holding history table: every symbol ever held, at up to 12 dates spread over the window
        idx = values.index
        picks = sorted({idx[int(round(i * (len(idx) - 1) / 11))] for i in range(min(12, len(idx)))})
        order = qty.abs().sum().sort_values(ascending=False).index.tolist()
        history = [{"symbol": s, "cells": [float(qty.at[d, s]) for d in picks]} for s in order]
        return {"dates": [d.strftime("%Y-%m-%d") for d in idx], "exposure": exposure,
                "positions": _points(count), "symbols": order,
                "history_dates": [d.strftime("%Y-%m-%d") for d in picks], "history": history}

    def holdings_at(self, portfolio_id: int, day: Optional[str] = None) -> Dict[str, Any]:
        qty, values, curve = self._positions(portfolio_id)
        if qty.empty:
            return {"date": None, "rows": [], "book_value": None}
        target = pd.Timestamp(day).normalize() if day else qty.index[-1]
        known = qty.index[qty.index <= target]
        if not len(known):
            return {"date": target.strftime("%Y-%m-%d"), "rows": [], "book_value": None}
        at = known[-1]
        book = curve[curve.index <= at]
        book_value = float(book.iloc[-1]) if len(book) else None
        rows = []
        for sym in qty.columns:
            q = float(qty.at[at, sym])
            if abs(q) < 1e-9:
                continue
            v = values.at[at, sym]
            value = None if pd.isna(v) else float(v)
            rows.append({"symbol": sym, "quantity": q, "price": None if value is None else value / q,
                         "value": value, "weight": (value / book_value) if value is not None and book_value else None,
                         "side": "long" if q > 0 else "short"})
        rows.sort(key=lambda r: -abs(r["value"] or 0))
        return {"date": at.strftime("%Y-%m-%d"), "rows": rows, "book_value": book_value,
                "dates": [d.strftime("%Y-%m-%d") for d in qty.index]}

    # -- trades / one asset -----------------------------------------------------------------------------------------
    def trades(self, portfolio_id: int, symbol: Optional[str] = None, page: int = 1,
               per_page: int = 200) -> Dict[str, Any]:
        fills = list(reversed(self._share_fills(portfolio_id, symbol)))
        total = len(fills)
        page = max(1, int(page))
        rows = fills[(page - 1) * per_page: page * per_page]
        for r in rows:
            r["notional"] = r["filled"] * r["price"] if r["price"] is not None else None
        return {"rows": rows, "total": total, "page": page, "pages": max(1, -(-total // per_page)),
                "symbols": sorted({f["symbol"] for f in self._share_fills(portfolio_id) if f["symbol"]})}

    def asset(self, portfolio_id: int, symbol: str) -> Dict[str, Any]:
        qty, values, _ = self._positions(portfolio_id, symbol=symbol)
        if qty.empty or symbol not in qty.columns:
            return {"symbol": symbol, "quantity": [], "value": [], "trades": []}
        return {"symbol": symbol, "quantity": _points(qty[symbol]), "value": _points(values[symbol].dropna()),
                "trades": self.trades(portfolio_id, symbol=symbol, per_page=10_000)["rows"]}
