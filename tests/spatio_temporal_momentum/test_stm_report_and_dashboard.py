"""Research report (paper tables/figures), renderer, and the Flask /stm dashboard."""

import time
import unittest
from unittest import mock

import numpy as np
import pandas as pd
import torch

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_research_report import (
    average_turnover,
    benchmark_positions,
    expected_gradients,
    strategy_metrics,
)


class _LinearUniverseModel(torch.nn.Module):
    """f(x)[k] = w_k . vec(x) — SHAP of a linear model is known exactly."""

    def __init__(self, n, t, f):
        super().__init__()
        self.lin = torch.nn.Linear(n * t * f, n, bias=True)

    def forward(self, x):
        return self.lin(x.flatten(start_dim=1))


class TestReportCalculations(unittest.TestCase):

    def test_metrics(self):
        r = pd.Series([0.01, -0.02, 0.015, 0.0, 0.005])
        m = strategy_metrics(r)
        self.assertAlmostEqual(m["E[Return]"], r.mean() * 252)
        self.assertAlmostEqual(m["Sharpe"], r.mean() / r.std(ddof=1) * np.sqrt(252))
        self.assertAlmostEqual(m["Hit Rate"], 3 / 5)
        self.assertAlmostEqual(m["Ave. P / Ave. L"], (0.03 / 3) / 0.02)
        self.assertGreater(m["MDD"], 0)

    def test_csmom_takes_decile_long_short(self):
        feats = np.zeros((1, 20, 2))
        feats[0, :, 0] = np.arange(20)                      # longest-horizon return ranks the assets
        pos = benchmark_positions(feats, ["ret", "macd_a"], "ret", ["macd_a"])
        cs = pos["CSMOM"][0]
        self.assertEqual(cs[-2:].tolist(), [1.0, 1.0])       # top 10%
        self.assertEqual(cs[:2].tolist(), [-1.0, -1.0])      # bottom 10%
        self.assertEqual(int(np.abs(cs).sum()), 4)
        np.testing.assert_array_equal(pos["TSMOM"][0], np.sign(np.arange(20)))

    def test_turnover_is_equation_12(self):
        pos = np.array([[1.0, -1.0], [-1.0, -1.0]])
        vols = np.full((2, 2), 0.01)
        ann = 0.01 * np.sqrt(252)
        expected = 0.15 * np.mean([abs(-1 / ann - 1 / ann), 0.0])
        self.assertAlmostEqual(average_turnover(pos, vols, 0.15)[0], expected)

    def test_expected_gradients_exact_for_linear_model(self):
        torch.manual_seed(0)
        n, t, f = 3, 4, 2
        model = _LinearUniverseModel(n, t, f)
        X = np.random.default_rng(1).normal(size=(5, n, t, f))
        bg = np.random.default_rng(2).normal(size=(1, n, t, f))          # single baseline -> deterministic
        phi = expected_gradients(model, X, bg, n_draws=3)
        w = model.lin.weight.detach().numpy().reshape(n, n, t, f)          # [out, N, T, F]
        expected = (X - bg)[:, None] * w[None]
        np.testing.assert_allclose(phi, expected, rtol=1e-5, atol=1e-6)
        with torch.no_grad():
            diff = (model(torch.tensor(X, dtype=torch.float32)) - model(torch.tensor(bg, dtype=torch.float32))).numpy()
        np.testing.assert_allclose(phi.reshape(5, n, -1).sum(axis=2), diff, rtol=1e-4, atol=1e-5)   # completeness


class TestBacktestWiring(unittest.TestCase):

    def test_tracker_survives_base_runner_progress_float(self):
        """BaseBacktestRunner sets self.progress = 0.0; the tracker must not travel under that name."""
        from src.application.managers.project_managers.spatio_temporal_momentum_project.backtesting.backtest_runner import (
            BacktestRunner,
        )
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import (
            STMProgressTracker,
        )
        tracker = STMProgressTracker()
        runner = BacktestRunner(mock.Mock())
        runner.progress_tracker = tracker
        runner.progress = 0.0                                  # what run_backtest does
        runner.model_trainer = mock.Mock(data_loader=mock.Mock(financial_asset_service=None))
        algorithm = runner.create_algorithm_instance()
        self.assertIs(algorithm.progress_tracker, tracker)

    def test_engine_failure_is_reported_not_hidden(self):
        from src.application.managers.project_managers.spatio_temporal_momentum_project.project_manager import (
            SpatioTemporalMomentumProjectManager,
        )
        import shutil
        import tempfile
        from src.application.managers.project_managers.spatio_temporal_momentum_project.config import get_config
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import (
            STMProgressTracker,
        )
        results_dir = tempfile.mkdtemp(prefix="stm_results_test_")      # never touch the real results_dir
        try:
            config = get_config()
            config["results_dir"] = results_dir
            manager = SpatioTemporalMomentumProjectManager(config=config, database_service=mock.Mock())
            manager.runner.run_backtest = mock.Mock(return_value={
                "success": True, "misbuffet_result": "❌ Backtest failed: TWS not connected"})
            with self.assertRaises(RuntimeError) as ctx:
                manager.run()
            self.assertIn("TWS not connected", str(ctx.exception))
            snap = STMProgressTracker.read_snapshot(f"{results_dir}/progress.json")
            self.assertEqual(snap["status"], "failed")                     # the dashboard shows the error
            self.assertIn("TWS not connected", snap["error"])
        finally:
            shutil.rmtree(results_dir, ignore_errors=True)


class TestDashboard(unittest.TestCase):
    """The dashboard only READS progress / results written by a run in another thread or process."""

    def test_dashboard_follows_external_run_and_shows_stored_results(self):
        import shutil
        import tempfile
        import threading

        from src.application.managers.project_managers.spatio_temporal_momentum_project.backtesting.synthetic_demo import (
            run_synthetic_demo,
        )
        from src.application.services.data.entities.factor.spatio_temporal_momentum import stm_report_store
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import (
            STMProgressTracker,
        )
        from src.interfaces.flask.app import FlaskApp

        results_dir = tempfile.mkdtemp(prefix="stm_results_test_")
        try:
            app = FlaskApp().get_app()
            app.config["STM_RESULTS_DIR"] = results_dir
            client = app.test_client()

            page = client.get("/stm/").get_data(as_text=True)
            self.assertNotIn("Run backtest", page)
            self.assertNotIn("Run synthetic demo", page)
            self.assertEqual(client.post("/stm/api/start", json={"mode": "demo"}).status_code, 404)
            idle = client.get("/stm/api/progress").get_json()
            self.assertEqual(idle["status"], "idle")
            self.assertFalse(idle["has_report"])
            self.assertEqual(client.get("/stm/results").status_code, 404)

            # A run elsewhere (here: another thread) writes progress + results to results_dir
            def external_run():
                tracker = STMProgressTracker(persist_path=stm_report_store.progress_path(results_dir),
                                             min_write_interval=0.2)
                tracker.start("demo")
                report = run_synthetic_demo(tracker, backtest_sessions=40, n_epochs=2)
                stm_report_store.save_report(report, results_dir)
                tracker.complete(report)

            worker = threading.Thread(target=external_run)
            worker.start()
            seen_running = False
            deadline = time.time() + 900
            while worker.is_alive() and time.time() < deadline:
                snap = client.get("/stm/api/progress").get_json()
                seen_running |= snap["status"] == "running" and snap["bars_done"] > 0
                time.sleep(0.5)
            worker.join()

            self.assertTrue(seen_running, "live progress visible while the external run is in progress")
            snap = client.get("/stm/api/progress").get_json()
            self.assertEqual(snap["status"], "completed")
            self.assertTrue(snap["has_report"])
            self.assertGreater(len(snap["retrainings"]), 0)

            html = client.get("/stm/results").get_data(as_text=True)
            for title in ("Table 1", "Table 2", "Table 6", "Figure 1", "Figure 3", "Figure 4", "Figure 5", "Figure 6"):
                self.assertIn(title, html)
            self.assertEqual(html.count("data:image/png;base64,"), 5)
            pdf = client.get("/stm/report.pdf")
            self.assertEqual(pdf.status_code, 200)
            self.assertTrue(pdf.data.startswith(b"%PDF"))

            # stored results survive a restart of the web app
            app2 = FlaskApp().get_app()
            app2.config["STM_RESULTS_DIR"] = results_dir
            self.assertEqual(app2.test_client().get("/stm/results").status_code, 200)
        finally:
            shutil.rmtree(results_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
