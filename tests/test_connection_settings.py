"""
Checklist section 8 — IBKR endpoint and SQL Server connection settings from the environment.

Pure functions only: nothing connects to IBKR or to a database.
"""

import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from src.application.services.misbuffet.brokers.ibkr import ibkr_settings
from src.infrastructure.database import settings

IBKR_VARS = ("IBKR_HOST", "IBKR_PORT", "IBKR_CLIENT_ID", "IBKR_ACCOUNT_MODE", "IBKR_ALLOW_LIVE",
             "IBKR_CONNECT_RETRIES", "IBKR_CONNECT_RETRY_DELAY")
DB_VARS = ("DB_ODBC_CONNECTION_STRING", "DB_HOST", "DB_SERVER", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
           "DB_DRIVER", "DB_TRUST_SERVER_CERTIFICATE", "DB_READONLY_USER", "DB_READONLY_PASSWORD")


@contextmanager
def env(names, **values):
    """Exactly `values` set among `names`; everything else in the environment untouched."""
    cleaned = {k: v for k, v in os.environ.items() if k not in names}
    with patch.dict(os.environ, {**cleaned, **values}, clear=True):
        yield


class IBKRSettingsTest(unittest.TestCase):

    def test_no_variables_change_nothing(self):
        with env(IBKR_VARS):
            ep = ibkr_settings.resolve_endpoint("127.0.0.1", 7497, 1)
        self.assertEqual((ep.host, ep.port, ep.client_id, ep.account_mode, ep.overridden),
                         ("127.0.0.1", 7497, 1, "paper", False))
        self.assertTrue(ep.paper)

    def test_overrides_apply(self):
        with env(IBKR_VARS, IBKR_HOST="ibkr", IBKR_PORT="4004", IBKR_CLIENT_ID="7"):
            ep = ibkr_settings.resolve_endpoint("127.0.0.1", 7497, 1)
        self.assertEqual((ep.host, ep.port, ep.client_id, ep.overridden), ("ibkr", 4004, 7, True))

    def test_client_id_override_only_replaces_the_default(self):
        with env(IBKR_VARS, IBKR_CLIENT_ID="7"):
            self.assertEqual(ibkr_settings.resolve_endpoint("h", 1, 17).client_id, 17)
            self.assertEqual(ibkr_settings.resolve_endpoint("h", 1, 1).client_id, 7)

    def test_live_requires_explicit_allow(self):
        for allow in (None, "", "no", "true", "1"):
            values = {"IBKR_ACCOUNT_MODE": "live", **({"IBKR_ALLOW_LIVE": allow} if allow is not None else {})}
            with env(IBKR_VARS, **values), self.assertRaises(RuntimeError, msg=f"allow={allow!r}"):
                ibkr_settings.resolve_endpoint("h", 1, 1)
        with env(IBKR_VARS, IBKR_ACCOUNT_MODE="LIVE", IBKR_ALLOW_LIVE="Yes"):
            ep = ibkr_settings.resolve_endpoint("h", 1, 1)
        self.assertEqual((ep.account_mode, ep.paper), ("live", False))

    def test_invalid_values_fail_loudly(self):
        with env(IBKR_VARS, IBKR_ACCOUNT_MODE="demo"), self.assertRaises(ValueError):
            ibkr_settings.account_mode()
        with env(IBKR_VARS, IBKR_PORT="four"), self.assertRaises(ValueError):
            ibkr_settings.resolve_endpoint("h", 1, 1)

    def test_blank_values_mean_unset(self):
        with env(IBKR_VARS, IBKR_HOST="  ", IBKR_PORT=""):
            ep = ibkr_settings.resolve_endpoint("127.0.0.1", 7497, 1)
        self.assertEqual((ep.host, ep.port, ep.overridden), ("127.0.0.1", 7497, False))

    def test_retries(self):
        with env(IBKR_VARS):
            self.assertEqual((ibkr_settings.connect_retries(), ibkr_settings.connect_retry_delay()), (0, 5.0))
        with env(IBKR_VARS, IBKR_CONNECT_RETRIES="-3", IBKR_CONNECT_RETRY_DELAY="0.5"):
            self.assertEqual((ibkr_settings.connect_retries(), ibkr_settings.connect_retry_delay()), (0, 0.5))

    def test_broker_applies_the_endpoint_and_paper_flag(self):
        from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
        with env(IBKR_VARS, IBKR_HOST="ibkr", IBKR_PORT="4003", IBKR_ACCOUNT_MODE="live", IBKR_ALLOW_LIVE="yes"):
            broker = InteractiveBrokersBroker({"host": "127.0.0.1", "port": 7497, "client_id": 1})
        self.assertEqual((broker.host, broker.port, broker.paper_trading), ("ibkr", 4003, False))
        with env(IBKR_VARS, IBKR_ACCOUNT_MODE="live"), self.assertRaises(RuntimeError):
            InteractiveBrokersBroker({"host": "127.0.0.1", "port": 7497, "client_id": 1})


class DatabaseSettingsTest(unittest.TestCase):

    def test_explicit_connection_string_wins(self):
        with env(DB_VARS, DB_ODBC_CONNECTION_STRING="DSN=x", DB_HOST="ignored"):
            self.assertEqual(settings._sql_server_connection_string(), "DSN=x")

    def test_host_builds_sql_authentication(self):
        with env(DB_VARS, DB_HOST="sqlserver", DB_USER="app", DB_PASSWORD="p;w}d", DB_NAME="bi"):
            cs = settings._sql_server_connection_string()
        self.assertIn("SERVER=sqlserver,1433;", cs)
        self.assertIn("DATABASE=bi;", cs)
        self.assertIn("UID=app;", cs)
        self.assertIn("PWD={p;w}}d};", cs)                 # ; and } in a password stay inside the value
        self.assertIn("DRIVER={ODBC Driver 18 for SQL Server};", cs)
        self.assertIn("TrustServerCertificate=yes", cs)

    def test_db_server_is_an_alias(self):
        with env(DB_VARS, DB_SERVER="db2", DB_PORT="14333"):
            self.assertIn("SERVER=db2,14333;", settings._sql_server_connection_string())

    def test_nothing_set_keeps_the_windows_default(self):
        with env(DB_VARS):
            cs = settings._sql_server_connection_string()
        self.assertIn("Server=localhost;", cs)
        self.assertIn("trusted_connection=yes", cs)

    def test_readonly_url_uses_only_the_readonly_login(self):
        with env(DB_VARS, DB_HOST="sqlserver", DB_USER="sa", DB_PASSWORD="admin",
                 DB_READONLY_USER="monitor_reader", DB_READONLY_PASSWORD="ro"):
            url = settings.get_readonly_database_url()
        odbc = url.query["odbc_connect"]
        self.assertIn("UID=monitor_reader;", odbc)
        self.assertIn("PWD={ro};", odbc)
        self.assertNotIn("admin", odbc)

    def test_readonly_url_absent_without_configuration(self):
        for values in ({}, {"DB_HOST": "sqlserver"}, {"DB_READONLY_USER": "monitor_reader"}):
            with env(DB_VARS, **values):
                self.assertIsNone(settings.get_readonly_database_url(), values)

    def test_default_database_type_is_sql_server(self):
        self.assertIs(settings.get_database_url(), settings.DATABASES["sql_server"])
        self.assertEqual(settings.get_database_url().drivername, "mssql+pyodbc")


if __name__ == "__main__":
    unittest.main()
