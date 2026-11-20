"""
BacktestBookReader — read-only queries on the Misbuffet engine's books (one book = the main portfolio of a backtest).

A book is a main portfolio with a daily value series (PortfolioValueFactor on 'PortfolioModel') and sub-portfolios
held through ``*PortfolioPortfolioHoldings`` (``<name>_CS`` company shares, ``<name>_cash``); its trades are the
orders of the holdings of those sub-portfolios. Every backtest has one, registered in the run registry or not (the
runs before 2026-11-18 only left their book).
"""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

PORTFOLIO_VALUE_FACTOR_TYPE = "portfolio_value_factor"
PORTFOLIO_ENTITY_TYPE = "PortfolioModel"


def _number(value) -> Optional[float]:
    try:
        v = float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return v if math.isfinite(v) else None


class BacktestBookReader:

    def __init__(self, session: Session):
        self.session = session

    def books(self) -> List[Dict[str, Any]]:
        """Every portfolio with a value series: id, name, values, first / last date."""
        from src.infrastructure.models.factor.factor import FactorModel
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel
        rows = (self.session.query(FactorValueModel.entity_id, func.count(FactorValueModel.id),
                                   func.min(FactorValueModel.date), func.max(FactorValueModel.date))
                .join(FactorModel, FactorModel.id == FactorValueModel.factor_id)
                .filter(FactorModel.factor_type == PORTFOLIO_VALUE_FACTOR_TYPE,
                        FactorValueModel.entity_type == PORTFOLIO_ENTITY_TYPE)
                .group_by(FactorValueModel.entity_id).all())
        names = dict(self.session.query(PortfolioModel.id, PortfolioModel.name)
                     .filter(PortfolioModel.id.in_([r[0] for r in rows] or [-1])).all())
        return [{"portfolio_id": pid, "name": names.get(pid), "values": n, "first": first, "last": last}
                for pid, n, first, last in sorted(rows, key=lambda r: r[0])]

    def sub_portfolios(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """The portfolios the book holds (through *PortfolioPortfolioHoldings)."""
        from src.infrastructure.models.finance.holding.holding import HoldingModel
        from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel
        rows = (self.session.query(PortfolioModel.id, PortfolioModel.name, PortfolioModel.portfolio_type)
                .join(HoldingModel, HoldingModel.asset_id == PortfolioModel.id)
                .filter(HoldingModel.container_id == portfolio_id,
                        HoldingModel.holding_type.like("%PortfolioPortfolioHolding%")).all())
        return [{"portfolio_id": pid, "name": name, "type": kind} for pid, name, kind in rows]

    def fills(self, portfolio_ids: List[int], symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Orders of the holdings of these portfolios, oldest first, with the asset traded."""
        from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
        from src.infrastructure.models.finance.holding.holding import HoldingModel
        from src.infrastructure.models.finance.order.order import OrderModel
        if not portfolio_ids:
            return []
        q = (self.session.query(OrderModel.id, OrderModel.created_at, HoldingModel.container_id, HoldingModel.asset_id,
                                FinancialAssetModel.symbol, FinancialAssetModel.entity_type, OrderModel.side,
                                OrderModel.quantity, OrderModel.filled_quantity, OrderModel.average_fill_price,
                                OrderModel.status)
             .join(HoldingModel, HoldingModel.id == OrderModel.holding_id)
             .outerjoin(FinancialAssetModel, FinancialAssetModel.id == HoldingModel.asset_id)
             .filter(HoldingModel.container_id.in_(list(portfolio_ids))))
        if symbol:
            q = q.filter(FinancialAssetModel.symbol == symbol)
        out = []
        for (oid, at, container, asset_id, sym, entity_type, side, qty, filled, price, status) in (
                q.order_by(OrderModel.created_at, OrderModel.id).all()):
            out.append({"order_id": oid, "time": at, "portfolio_id": container, "asset_id": asset_id, "symbol": sym,
                        "asset_type": entity_type, "side": getattr(side, "value", side), "quantity": float(qty or 0),
                        "filled": float(filled or 0), "price": None if price is None else float(price),
                        "status": getattr(status, "value", status)})
        return out

    def closes(self, asset_ids: List[int], start: datetime, end: datetime) -> Dict[int, List[tuple]]:
        """{asset id: [(date, close)]} of the daily traded closes (TRADES, 1d) in the window."""
        from src.infrastructure.models.factor.factor import FactorModel
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        if not asset_ids:
            return {}
        factor_ids = [fid for (fid,) in self.session.query(FactorModel.id).filter(
            FactorModel.name == "close", FactorModel.group == "price", FactorModel.frequency == "1d",
            FactorModel.subgroup == "TRADES").all()]
        if not factor_ids:
            return {}
        out: Dict[int, List[tuple]] = {}
        ids = sorted(set(asset_ids))
        for begin in range(0, len(ids), 200):
            rows = (self.session.query(FactorValueModel.entity_id, FactorValueModel.date, FactorValueModel.value)
                    .filter(FactorValueModel.factor_id.in_(factor_ids),
                            FactorValueModel.entity_id.in_(ids[begin:begin + 200]),
                            FactorValueModel.entity_type == "CompanyShare",
                            FactorValueModel.date >= start, FactorValueModel.date <= end)
                    .order_by(FactorValueModel.entity_id, FactorValueModel.date).all())
            for entity_id, date, value in rows:
                v = _number(value)
                if v is not None:
                    out.setdefault(entity_id, []).append((date, v))
        return out
