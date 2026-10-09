"""Configuration, health states, redaction, logs, jobs, database read-only guard."""

import json
import logging
import os
import tempfile
import time
import unittest
from datetime import timedelta
from unittest import mock

from sqlalchemy import text

from src.application.services.monitoring.config import MonitoringConfig, MonitoringConfigError
from src.application.services.monitoring.job_tracker import FAILED, RUNNING, SUCCEEDED, JobReader, JobRecorder
from src.application.services.monitoring.log_store import (
    LogReader, RingBufferHandler, classify, install_monitoring_log_handler,
)
from src.application.services.monitoring.redaction import MASK, redact, redact_text
from src.application.services.monitoring.status import (
    DEGRADED, DISCONNECTED, ERROR, HEALTHY, STALE, UNKNOWN, Section, utcnow, worst,
)
from src.infrastructure.repositories.local_repo.monitoring.monitoring_read_repository import (
    MonitoringReadRepository, ReadOnlyViolation, guard_read_only,
)
from tests.monitoring.helpers import build_service, sqlite_engine


class ConfigTest(unittest.TestCase):

    def test_defaults_are_paper_and_safe(self):
        cfg = MonitoringConfig.from_env({})
        self.assertEqual(cfg.ibkr_account_mode, "paper")
        self.assertFalse(cfg.ibkr_allow_live)
        self.assertEqual(cfg.intervals.health, 10)
        view = json.dumps(cfg.safe_view()).lower()
        for word in ("password", "pwd", "secret", "token"):
            self.assertNotIn(word, view)

    def test_values_are_read_from_environment(self):
        cfg = MonitoringConfig.from_env({"IBKR_HOST": "ibkr", "IBKR_PORT": "4003", "IBKR_ACCOUNT_MODE": "live",
                                         "IBKR_MONITOR_CLIENT_ID": "90", "MONITOR_ACCOUNT_INTERVAL": "20",
                                         "DB_HOST": "sqlserver", "DB_READONLY_USER": "monitor_reader"})
        self.assertEqual((cfg.ibkr_host, cfg.ibkr_port, cfg.ibkr_account_mode, cfg.ibkr_client_id),
                         ("ibkr", 4003, "live", 90))
        self.assertEqual(cfg.intervals.account, 20)
        self.assertTrue(cfg.db_readonly_configured)

    def test_invalid_values_fail_at_startup(self):
        for env in ({"IBKR_ACCOUNT_MODE": "demo"}, {"IBKR_PORT": "abc"}, {"IBKR_PORT": "70000"},
                    {"MONITOR_HEALTH_INTERVAL": "0"}, {"MONITOR_IBKR_ENABLED": "maybe"}):
            with self.assertRaises(MonitoringConfigError, msg=env):
                MonitoringConfig.from_env(env)


class StatusTest(unittest.TestCase):

    def test_never_collected_is_unknown(self):
        self.assertEqual(Section("x", 10).view()["status"], UNKNOWN)

    def test_old_data_is_stale_not_healthy(self):
        s = Section("x", stale_after_seconds=10)
        s.update(HEALTHY, {"a": 1})
        self.assertEqual(s.view()["status"], HEALTHY)
        later = utcnow() + timedelta(seconds=60)
        view = s.view(now=later)
        self.assertEqual(view["status"], STALE)
        self.assertTrue(view["stale"])

    def test_error_keeps_last_data_with_its_timestamp(self):
        s = Section("x", 10)
        s.update(HEALTHY, {"a": 1})
        first = s.view()["updated_at"]
        s.update(DISCONNECTED, error="timeout")
        view = s.view()
        self.assertEqual((view["status"], view["error"], view["data"], view["updated_at"]),
                         (DISCONNECTED, "timeout", {"a": 1}, first))

    def test_aggregation(self):
        self.assertEqual(worst(HEALTHY, DEGRADED), DEGRADED)
        self.assertEqual(worst(HEALTHY, ERROR, DISCONNECTED), ERROR)
        self.assertEqual(worst(), UNKNOWN)


class RedactionTest(unittest.TestCase):

    def test_connection_strings_and_key_values(self):
        cases = [
            "DRIVER={ODBC Driver 18};SERVER=sqlserver,1433;UID=sa;PWD={p@ss;w}}ord};Encrypt=yes",
            "odbc_connect=DRIVER%3D%7BODBC%7D%3BPWD%3D%7Bp%40ss%7D%3BEncrypt",
            "password=hunter2 token=abc123 api_key=xyz789",
            '{"password": "hunter2", "TWS_PASSWORD": "x"}',
            "mssql+pyodbc://sa:hunter2@sqlserver/base_infra",
        ]
        for c in cases:
            out = redact_text(c)
            for secret in ("p@ss", "w}}ord", "hunter2", "abc123", "xyz789", "p%40ss"):
                self.assertNotIn(secret, out, c)
        self.assertIn("SERVER=sqlserver,1433", redact_text(cases[0]))

    def test_environment_secret_values(self):
        from src.application.services.monitoring.redaction import refresh_secret_cache
        with mock.patch.dict(os.environ, {"SOME_API_KEY": "verysecretvalue"}):
            refresh_secret_cache()
            self.assertEqual(redact_text("value is verysecretvalue"), f"value is {MASK}")
        refresh_secret_cache()

    def test_sensitive_keys_in_structures(self):
        out = redact({"db_password": "x1y2z3", "nested": [{"token": "t0k3n"}], "port": 1433})
        self.assertEqual(out, {"db_password": MASK, "nested": [{"token": MASK}], "port": 1433})


class LogTest(unittest.TestCase):

    def test_classification(self):
        self.assertEqual(classify("IBTWSClient"), "ibkr")
        self.assertEqual(classify("sqlalchemy.engine"), "database")
        self.assertEqual(classify("FactorValueResolutionService"), "factors")
        self.assertEqual(classify("misbuffet.engine"), "engine")
        self.assertEqual(classify("x", "TWS Error 502: Couldn't connect"), "ibkr")

    def test_ring_buffer_redacts_and_reader_filters(self):
        ring = RingBufferHandler(capacity=10)
        log = logging.getLogger("tests.monitoring.ring")
        log.addHandler(ring)
        log.setLevel(logging.INFO)
        try:
            log.info("hello")
            log.error("login PWD={supersecret}; failed")
            logging.getLogger("IBTWSClient").addHandler(ring)
            logging.getLogger("IBTWSClient").warning("Error 1100 connectivity lost")
        finally:
            log.removeHandler(ring)
            logging.getLogger("IBTWSClient").removeHandler(ring)
        reader = LogReader(tempfile.mkdtemp(), ring=ring)
        errors = reader.recent(min_level="ERROR")
        self.assertEqual(len(errors), 1)
        self.assertNotIn("supersecret", errors[0]["message"])
        self.assertEqual([r["component"] for r in reader.recent(component="ibkr")], ["ibkr"])
        self.assertEqual(len(reader.recent(query="hello")), 1)

    def test_ibapi_protocol_chatter_is_not_kept(self):
        ring = RingBufferHandler(capacity=10)
        for name in ("ibapi.client", "ibapi.wrapper", "IBTWSClient"):
            logging.getLogger(name).addHandler(ring)
            logging.getLogger(name).setLevel(logging.INFO)
        try:
            logging.getLogger("ibapi.client").info("REQUEST reqAccountSummary {'reqId': 1}")
            logging.getLogger("ibapi.wrapper").warning("ibapi warning kept")
            logging.getLogger("IBTWSClient").info("Connecting to TWS")
        finally:
            for name in ("ibapi.client", "ibapi.wrapper", "IBTWSClient"):
                logging.getLogger(name).removeHandler(ring)
        self.assertEqual([r["message"] for r in ring.snapshot()], ["ibapi warning kept", "Connecting to TWS"])

    def test_json_lines_written_by_app_processes_are_read(self):
        tmp = tempfile.mkdtemp()
        handler = install_monitoring_log_handler(process_name="unit", state_dir=tmp)
        self.assertIsNotNone(handler)
        try:
            logging.getLogger("misbuffet.engine").error("backtest failed: token=abc")
            handler.flush()
        finally:
            logging.getLogger().removeHandler(handler)
            handler.close()
        records = LogReader(tmp).recent(min_level="ERROR", component="engine")
        self.assertTrue(any("backtest failed" in r["message"] for r in records))
        self.assertTrue(all("abc" not in r["message"] for r in records))


class JobsTest(unittest.TestCase):

    def test_recorder_and_reader(self):
        tmp = tempfile.mkdtemp()
        ok = JobRecorder("backtest", "spx", state_dir=tmp).start()
        reader = JobReader(tmp, os.path.join(tmp, "results"))
        self.assertEqual(reader.jobs()[0]["status"], RUNNING)
        ok.finish(True)
        bad = JobRecorder("backtest", "stm", state_dir=tmp).start()
        bad.finish(False, error="RuntimeError: PWD={x}")
        jobs = {j["name"]: j for j in reader.jobs()}
        self.assertEqual(jobs["spx"]["status"], SUCCEEDED)
        self.assertEqual(jobs["stm"]["status"], FAILED)
        self.assertNotIn("{x}", jobs["stm"]["error"])

    def test_existing_progress_files_are_listed(self):
        tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(tmp, "results", "stm_full"))
        with open(os.path.join(tmp, "results", "stm_full", "progress.json"), "w") as f:
            json.dump({"status": "running", "phase": "training", "percent": 42.0, "updated_at": "2026-10-08T10:00:00"}, f)
        jobs = JobReader(tmp, os.path.join(tmp, "results")).jobs()
        self.assertEqual(jobs[0]["name"], "stm_full")
        self.assertEqual(jobs[0]["details"]["percent"], 42.0)

    def test_backtest_runner_hook_does_not_change_the_run(self):
        from src.application.services.misbuffet.engine.base_backtest_runner import _record_job
        tmp = tempfile.mkdtemp()

        class Runner:
            @_record_job
            def run_backtest(self, config):
                if config.get("fail"):
                    raise ValueError("boom")
                return {"success": True, "misbuffet_result": "ok"}

        with mock.patch.dict(os.environ, {"MONITOR_STATE_DIR": tmp, "MONITOR_LOG_FILE_ENABLED": "false"}):
            self.assertEqual(Runner().run_backtest({"project_name": "p"}), {"success": True, "misbuffet_result": "ok"})
            with self.assertRaises(ValueError):
                Runner().run_backtest({"project_name": "q", "fail": True})
            jobs = {j["name"]: j for j in JobReader(tmp, tmp).jobs()}
        self.assertEqual(jobs["p"]["status"], SUCCEEDED)
        self.assertEqual(jobs["q"]["status"], FAILED)


class DatabaseReadOnlyTest(unittest.TestCase):

    def test_guard_rejects_writes(self):
        engine = guard_read_only(sqlite_engine())
        with engine.connect() as conn:
            self.assertEqual(conn.execute(text("SELECT 1")).scalar(), 1)
            for stmt in ("INSERT INTO factors (id) VALUES (99)", "UPDATE factors SET name='x'",
                         "DELETE FROM factor_values", "DROP TABLE factors", "  /* c */ delete from factors",
                         "EXEC sp_who", "CREATE TABLE t (a int)"):
                with self.assertRaises(ReadOnlyViolation, msg=stmt):
                    conn.execute(text(stmt))

    def test_repository_queries(self):
        repo = MonitoringReadRepository(guard_read_only(sqlite_engine()))
        self.assertEqual(repo.table_counts(), {"factors": 2, "factor_values": 3, "financial_assets": 1})
        factors = {f["name"]: f for f in repo.factor_summary()}
        self.assertEqual(factors["close"]["value_count"], 2)
        rows = repo.market_data_freshness()
        self.assertEqual([(r["factor"], r["symbol"]) for r in rows], [("close", "SPY")])
        self.assertEqual({s["source"] for s in repo.data_sources()}, {"calculated", "ibkr"})

    def test_service_reports_freshness_and_overall_health(self):
        service = build_service()
        service.collect_health()
        service.collect_data()
        md = service.market_data()
        self.assertEqual(md["data"]["total_series"], 1)
        self.assertEqual(md["data"]["rows"][0]["state"], "fresh")
        self.assertIsNone(md["data"]["last_historical_retrieval"])
        fac = service.factors()
        self.assertEqual(fac["data"]["counts"]["factor_values"], 3)
        db = service.database()
        self.assertEqual(db["status"], HEALTHY)
        self.assertTrue(db["data"]["app_level_read_only_guard"])
        self.assertEqual(service.overview()["status"], UNKNOWN)       # collectors not started yet
        service.start()
        try:
            time.sleep(0.5)
            self.assertIn(service.overview()["status"], (HEALTHY, DEGRADED))
        finally:
            service.stop()

    def test_database_outage_is_reported_without_crashing(self):
        service = build_service()

        class Broken:
            db_level_read_only = True

            def health(self):
                raise OSError("Login timeout expired (connect)")
            repo = property(lambda self: (_ for _ in ()).throw(OSError("connect failed")))
        service.db = Broken()
        service.collect_health()
        service.collect_data()
        self.assertEqual(service.database()["status"], DISCONNECTED)
        self.assertEqual(service.factors()["status"], ERROR)
        self.assertEqual(service.overview()["status"], DISCONNECTED)


if __name__ == "__main__":
    unittest.main()
