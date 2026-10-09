"""Dashboard API: only read operations, mutation requests rejected, no DB writes, no secrets."""

import os
import tempfile
import time
import unittest
from unittest import mock

from sqlalchemy import event, func, select

from src.application.services.monitoring.log_store import RingBufferHandler
from src.application.services.monitoring.redaction import refresh_secret_cache
from src.infrastructure.models import ModelBase
from src.interfaces.flask.monitoring_app import create_monitoring_app
from tests.monitoring.helpers import build_service

MUTATING = ("POST", "PUT", "PATCH", "DELETE")
SECRET_ENV = {
    "DB_PASSWORD": "Sa-Secret-Value-123!", "DB_READONLY_PASSWORD": "Reader-Secret-456!",
    "MSSQL_SA_PASSWORD": "Mssql-Secret-789!", "TWS_PASSWORD": "Tws-Secret-000!",
    "FMP_API_KEY": "fmp-key-secret-abc", "ERCOT_SUBSCRIPTION_KEY": "ercot-secret-def",
}


class ReadOnlyApiTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.env = mock.patch.dict(os.environ, SECRET_ENV)
        cls.env.start()
        refresh_secret_cache()
        cls.service = build_service(cls.tmp)
        cls.service.ring = RingBufferHandler(capacity=100)
        cls.service.logs.ring = cls.service.ring
        import logging
        logging.getLogger().addHandler(cls.service.ring)
        cls.app = create_monitoring_app(service_provider=lambda: cls.service)
        cls.client = cls.app.test_client()
        cls.client.get("/monitor/api/health")          # starts the (SQLite) collector
        time.sleep(1.5)

    @classmethod
    def tearDownClass(cls):
        import logging
        logging.getLogger().removeHandler(cls.service.ring)
        cls.service.stop()
        cls.env.stop()
        refresh_secret_cache()

    def routes(self):
        return [r for r in self.app.url_map.iter_rules() if "<" not in r.rule]

    def test_every_route_is_read_only(self):
        for rule in self.app.url_map.iter_rules():
            self.assertTrue(set(rule.methods) <= {"GET", "HEAD", "OPTIONS"}, f"{rule.rule}: {rule.methods}")

    def test_only_monitoring_routes_are_exposed(self):
        for rule in self.app.url_map.iter_rules():
            self.assertTrue(rule.rule == "/" or rule.rule.startswith("/monitor/"), rule.rule)
        names = {r.rule for r in self.routes()}
        for forbidden in ("/backtest", "/entity-upload", "/api/test_managers/backtest", "/test_live_trading"):
            self.assertNotIn(forbidden, names)

    def test_mutation_requests_are_rejected_on_every_route(self):
        for rule in self.routes():
            for method in MUTATING:
                r = self.client.open(rule.rule, method=method, json={"action": "placeOrder"})
                self.assertEqual(r.status_code, 405, f"{method} {rule.rule}")
        r = self.client.open("/does-not-exist", method="POST")
        self.assertEqual(r.status_code, 405)

    def test_get_endpoints_answer_with_the_status_envelope(self):
        for rule in self.routes():
            r = self.client.get(rule.rule)
            self.assertIn(r.status_code, (200, 302), rule.rule)
            if rule.rule.startswith("/monitor/api/") and r.is_json:
                body = r.get_json()
                self.assertIn("status", body, rule.rule)
                self.assertIn("generated_at", body, rule.rule)
                self.assertEqual(r.headers["Cache-Control"], "no-store")

    def test_requests_do_not_write_to_the_database(self):
        engine = self.service.db.repo.engine
        statements = []
        listener = lambda conn, cursor, statement, *a: statements.append(statement)  # noqa: E731
        event.listen(engine, "before_cursor_execute", listener)
        tables = [t for t in ModelBase.metadata.sorted_tables
                  if t.name in ("financial_entities", "financial_assets", "factors", "factor_values")]

        def counts():
            with engine.connect() as conn:
                return {t.name: conn.execute(select(func.count()).select_from(t)).scalar() for t in tables}
        before = counts()
        try:
            self.service.collect_health()
            self.service.collect_data()
            for rule in self.routes():
                self.client.get(rule.rule)
                for method in MUTATING:
                    self.client.open(rule.rule, method=method)
        finally:
            event.remove(engine, "before_cursor_execute", listener)
        self.assertEqual(before, counts())
        self.assertTrue(statements)
        for s in statements:
            self.assertRegex(s.lstrip().upper(), r"^(SELECT|WITH)", s[:80])

    def test_responses_and_logs_never_contain_secrets(self):
        import logging
        logging.getLogger("IBTWSClient").error("connect failed PWD={%s};UID=sa", SECRET_ENV["DB_PASSWORD"])
        logging.getLogger("monitoring.database").warning("odbc_connect=PWD%%3D%%7B%s%%7D", SECRET_ENV["DB_READONLY_PASSWORD"])
        self.service.ibkr._on_error(-1, 502, f"password={SECRET_ENV['TWS_PASSWORD']} rejected")
        bodies = []
        for rule in self.routes():
            bodies.append(self.client.get(rule.rule).get_data(as_text=True))
        bodies.append(self.client.get("/monitor/api/logs/recent?level=DEBUG").get_data(as_text=True))
        text = "\n".join(bodies)
        for name, secret in SECRET_ENV.items():
            self.assertNotIn(secret, text, name)
        self.assertNotIn("Dev_Only", text)

    def test_query_parameters_are_validated(self):
        self.assertEqual(self.client.get("/monitor/api/logs/recent?level=EVIL").status_code, 400)
        self.assertEqual(self.client.get("/monitor/api/logs/recent?limit=999999").status_code, 400)
        self.assertEqual(self.client.get("/monitor/api/logs/recent?component=../../etc").status_code, 400)
        self.assertEqual(self.client.get("/monitor/api/market-data/status?limit=abc").status_code, 400)
        self.assertEqual(self.client.get("/monitor/api/logs/recent?level=ERROR&limit=5").status_code, 200)

    def test_security_headers(self):
        r = self.client.get("/monitor/")
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertIn("form-action 'none'", r.headers["Content-Security-Policy"])
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")
        html = r.get_data(as_text=True)
        self.assertNotIn("<form", html.lower())
        self.assertNotIn("method=\"post\"", html.lower())

    def test_pages_have_no_trading_or_mutation_controls(self):
        for rule in self.routes():
            if rule.rule.startswith("/monitor/api") or rule.rule == "/":
                continue
            html = self.client.get(rule.rule).get_data(as_text=True).lower()
            for word in ("place order", "cancel order", "buy</button", "sell</button", "submit", "<form"):
                self.assertNotIn(word, html, f"{rule.rule}: {word}")

    def test_dev_app_monitor_routes_are_also_get_only(self):
        from src.interfaces.flask.app import FlaskApp
        app = FlaskApp().app
        for rule in app.url_map.iter_rules():
            if rule.rule.startswith("/monitor"):
                self.assertTrue(set(rule.methods) <= {"GET", "HEAD", "OPTIONS"}, rule.rule)


if __name__ == "__main__":
    unittest.main()
