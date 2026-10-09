"""Fixtures for the monitoring tests: SQLite read-only database, IBKR monitor fed by callbacks.

Nothing here connects to SQL Server or to IB Gateway.
"""

import datetime as dt
import tempfile
from types import SimpleNamespace

from sqlalchemy import create_engine, insert
from sqlalchemy.pool import StaticPool

from src.application.services.monitoring.config import MonitoringConfig, RefreshIntervals
from src.application.services.monitoring.db_monitor import DatabaseMonitor
from src.application.services.monitoring.ibkr_monitor import IBKRMonitor
from src.application.services.monitoring.service import MonitoringService
from src.infrastructure.models import ModelBase
from src.infrastructure.models.factor.factor import FactorModel
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel
from src.infrastructure.repositories.local_repo.monitoring.monitoring_read_repository import guard_read_only

TABLES = None


def _defaults_for(table, values):
    """Fill NOT NULL columns without defaults so test rows can be inserted on any schema."""
    row = dict(values)
    for col in table.columns:
        if col.name in row or col.nullable or col.default is not None or col.server_default is not None \
                or col.primary_key and col.autoincrement:
            continue
        py = getattr(col.type, "python_type", str)
        try:
            py = col.type.python_type
        except NotImplementedError:
            py = str
        row[col.name] = {int: 0, float: 0.0, str: "x", bool: False,
                         dt.datetime: dt.datetime(2020, 1, 1), dt.date: dt.date(2020, 1, 1)}.get(py, "x")
    return row


def sqlite_engine():
    """In-memory SQLite with the factor / asset tables and a few rows (setup writes directly)."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    tables = [t for t in ModelBase.metadata.sorted_tables
              if t.name in ("financial_entities", "financial_assets", "factors", "factor_values", "currencies")]
    ModelBase.metadata.create_all(engine, tables=tables)
    entity_t = ModelBase.metadata.tables["financial_entities"]
    with engine.begin() as conn:
        conn.execute(insert(entity_t).values(**_defaults_for(entity_t, {"id": 1})))
        conn.execute(insert(FinancialAssetModel.__table__).values(
            **_defaults_for(FinancialAssetModel.__table__, {"id": 1, "symbol": "SPY", "start_date": dt.date(2020, 1, 1)})))
        conn.execute(insert(FactorModel.__table__).values(**_defaults_for(FactorModel.__table__, {
            "id": 1, "name": "close", "group": "price", "subgroup": "raw", "frequency": "1d", "source": "ibkr",
            "factor_type": "factor", "data_type": "numeric", "definition": "close"})))
        conn.execute(insert(FactorModel.__table__).values(**_defaults_for(FactorModel.__table__, {
            "id": 2, "name": "momentum", "group": "momentum", "subgroup": "x", "frequency": "1d",
            "source": "calculated", "factor_type": "factor", "data_type": "numeric", "definition": "m"})))
        now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        for i, (fid, days_ago) in enumerate([(1, 1), (1, 30), (2, 0)]):
            conn.execute(insert(FactorValueModel.__table__).values(**_defaults_for(FactorValueModel.__table__, {
                "id": i + 1, "factor_id": fid, "entity_id": 1, "entity_type": "CompanyShare",
                "date": now - dt.timedelta(days=days_ago), "value": "1.0"})))
    return engine


def make_config(tmp_dir=None, **overrides) -> MonitoringConfig:
    tmp_dir = tmp_dir or tempfile.mkdtemp()
    params = dict(environment="test", version="test", db_host="sqlite", ibkr_enabled=True, ibkr_host="ibkr",
                  ibkr_port=4004, ibkr_client_id=90, ibkr_account_mode="paper",
                  state_dir=f"{tmp_dir}/.monitor", results_dir=f"{tmp_dir}/results",
                  intervals=RefreshIntervals(health=2, account=5, positions=5, data=5, logs=2))
    params.update(overrides)
    return MonitoringConfig(**params)


class NoConnectIBKRMonitor(IBKRMonitor):
    """IBKRMonitor whose thread is never started: state comes from callbacks called by the test."""

    def start(self):
        return None


def contract(symbol="SPY", sec_type="STK", currency="USD", con_id=756733):
    return SimpleNamespace(conId=con_id, symbol=symbol, localSymbol=symbol, secType=sec_type, currency=currency,
                           exchange="SMART", primaryExchange="ARCA", lastTradeDateOrContractMonth="", strike=0.0,
                           right="", multiplier="")


def fed_ibkr_monitor() -> NoConnectIBKRMonitor:
    m = NoConnectIBKRMonitor("ibkr", 4004, 90, "paper", account_interval=5, positions_interval=5, heartbeat_interval=2)
    m.last_connect_attempt = m.connected_since = m.last_heartbeat = dt.datetime.now(dt.timezone.utc)
    m.connected = True
    m._on_accounts(["DU1234567"])
    m._summary_req = {1: "summary", 2: "ledger"}
    m._summary_stage = {"summary": {}, "ledger": {}}
    m._on_summary(1, "DU1234567", "NetLiquidation", "100250.50", "USD")
    m._on_summary(1, "DU1234567", "TotalCashValue", "0.00", "USD")          # a genuine zero
    m._on_summary(1, "DU1234567", "AvailableFunds", "50000", "USD")
    m._on_summary(1, "DU1234567", "AccountType", "INDIVIDUAL", "")
    # real IBKR format: "$LEDGER-<tag>" per currency, plus "BASE"
    m._on_summary(2, "DU1234567", "$LEDGER-CashBalance", "1000", "USD")
    m._on_summary(2, "DU1234567", "$LEDGER-Currency", "USD", "USD")
    m._on_summary(2, "DU1234567", "$LEDGER-CashBalance", "-200", "EUR")
    m._on_summary(2, "DU1234567", "$LEDGER-UnrealizedPnL", "12.5", "BASE")
    m._on_summary_end(1)
    m._on_summary_end(2)
    m._on_position("DU1234567", contract(), 10, 400.0)
    m._on_position("DU1234567", contract("SAP", currency="EUR", con_id=14204), -5, 120.0)
    m._on_position_end()
    m._on_portfolio(contract(), 10, 450.0, 4500.0, 400.0, 500.0, 0.0, "DU1234567")
    m._on_portfolio(contract("SAP", currency="EUR", con_id=14204), -5, 130.0, -650.0, 120.0, -50.0, 0.0, "DU1234567")
    order = SimpleNamespace(permId=111, clientId=1, account="DU1234567", action="BUY", orderType="LMT",
                            totalQuantity=5, lmtPrice=440.0, auxPrice=None, tif="DAY")
    m._on_open_order(7, contract(), order, SimpleNamespace(status="Submitted"))
    m._on_order_status(7, "Submitted", 2, 3)
    m._on_open_order_end()
    return m


def build_service(tmp_dir=None, ibkr=None, **cfg) -> MonitoringService:
    engine = guard_read_only(sqlite_engine())
    db = DatabaseMonitor(engine=engine, db_level_read_only=None)
    return MonitoringService(make_config(tmp_dir, **cfg), db=db, ibkr=ibkr if ibkr is not None else fed_ibkr_monitor())
