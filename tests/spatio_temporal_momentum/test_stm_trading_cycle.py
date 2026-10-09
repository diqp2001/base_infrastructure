"""
Time-driven Spatio-Temporal Momentum: MarketDataHistoryService frontier and
STMTradingCycle (the code the Misbuffet algorithm runs on every bar).
"""

import shutil
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd
import torch

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_artifact_store import (
    STMArtifactStore,
    load_model_file,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
    build_feature_panel,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_model_provider import (
    SpatioTemporalMomentumModelProvider,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_trading_cycle import (
    STMTradingCycle,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_walk_forward import (
    STMWalkForwardTrainer,
)
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService
from tests.spatio_temporal_momentum.helpers import ASSETS, make_factory, seed_closes, synthetic_closes, tiny_config

ENTITY_IDS = {a: 100 + i for i, a in enumerate(ASSETS)}


def _history_service(factory):
    stub = SimpleNamespace(entity_service=SimpleNamespace(repository_factory=factory))
    return MarketDataHistoryService(stub)


def _bars(start, end, hour=16):
    return [d + pd.Timedelta(hours=hour) for d in pd.bdate_range(start, end)]


class _Env:
    """In-memory database seeded with daily closes + a frontier history service."""

    def __init__(self, closes, model_type="tft"):
        SpatioTemporalMomentumModelProvider.clear_cache()
        self.tmp = tempfile.mkdtemp()
        self.cfg = tiny_config(model_type=model_type, tmp_dir=self.tmp)
        self.cfg.artifact_selection = "latest_before"
        self.cfg.training.n_epochs = 2
        self.factory, self.session, self.engine = make_factory()
        self.close_factor_id = seed_closes(self.session, closes, ENTITY_IDS)
        self.history = _history_service(self.factory)

    def cycle(self, retrain_every_days=120):
        return STMTradingCycle(self.factory, self.cfg, self.history, ENTITY_IDS, history_start="2015-01-01",
                               retrain_every_days=retrain_every_days)

    def close(self):
        SpatioTemporalMomentumModelProvider.clear_cache()
        self.session.close()
        self.engine.dispose()
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestFrontierHistory(unittest.TestCase):

    def setUp(self):
        self.closes = synthetic_closes(300)
        self.factory, self.session, self.engine = make_factory()
        seed_closes(self.session, self.closes, ENTITY_IDS)
        self.history = _history_service(self.factory)
        self.ids = {v: k for k, v in ENTITY_IDS.items()}

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_reading_without_frontier_is_refused(self):
        with self.assertRaises(ValueError):
            self.history.get_factor_value_panel(self.ids)

    def test_daily_bar_is_hidden_until_it_has_closed(self):
        d = self.closes.index[100]
        self.history.set_frontier((d + pd.Timedelta(hours=16)).to_pydatetime())
        panel = self.history.get_factor_value_panel(self.ids)
        self.assertEqual(panel.index.max(), self.closes.index[99])
        self.history.set_frontier((d + pd.Timedelta(days=1)).to_pydatetime())
        self.assertEqual(self.history.get_factor_value_panel(self.ids).index.max(), d)

    def test_end_cannot_extend_past_the_frontier(self):
        d = self.closes.index[100]
        self.history.set_frontier((d + pd.Timedelta(hours=16)).to_pydatetime())
        panel = self.history.get_factor_value_panel(self.ids, end=self.closes.index[-1].to_pydatetime())
        self.assertLess(panel.index.max(), d)

    def test_frontier_never_moves_backwards(self):
        self.history.set_frontier(pd.Timestamp("2016-01-10").to_pydatetime())
        with self.assertRaises(ValueError):
            self.history.set_frontier(pd.Timestamp("2016-01-05").to_pydatetime())


class TestTradingCycle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.closes = synthetic_closes(900)
        cls.env = _Env(cls.closes)
        cycle = cls.env.cycle(retrain_every_days=120)
        cls.results = [cycle.step(t) for t in _bars("2016-08-01", "2017-03-31")]

    @classmethod
    def tearDownClass(cls):
        cls.env.close()

    def test_decision_session_is_the_last_closed_bar(self):
        for r in self.results[:5]:
            self.assertEqual(r.session, (r.time.normalize() - pd.offsets.BDay(1)).normalize())

    def test_trains_first_then_retrains_on_schedule(self):
        trained = [r.session for r in self.results if r.retrained]
        self.assertEqual(trained[0], self.results[0].session)
        self.assertGreaterEqual(len(trained), 2)
        gaps = [(b - a).days for a, b in zip(trained, trained[1:])]
        self.assertTrue(all(g >= 120 for g in gaps), gaps)

    def test_new_model_is_only_used_from_the_next_session(self):
        first = self.results[0]
        self.assertTrue(first.retrained)
        self.assertEqual(first.scores, {})                       # its own session: no eligible model yet
        self.assertTrue(self.results[1].scores)                   # next session: model available

    def test_every_decision_uses_a_model_validated_before_the_session(self):
        store = STMArtifactStore(self.env.factory, self.env.cfg)
        for r in self.results:
            if r.scores:
                _, meta = store.select(r.session)
                self.assertLess(pd.Timestamp(meta["validation_end"]), r.session)
                self.assertEqual(sorted(r.scores), sorted(meta["assets"]))

    def test_weights_are_produced_for_every_scored_session(self):
        scored = [r for r in self.results if r.scores]
        self.assertTrue(scored)
        for r in scored:
            self.assertEqual(set(r.weights), set(r.scores))
            self.assertLessEqual(sum(abs(w) for w in r.weights.values()), 1.0 + 1e-9)


class TestCycleIgnoresTheFuture(unittest.TestCase):

    def test_decisions_identical_when_future_prices_differ(self):
        closes = synthetic_closes(900)
        cut = pd.Timestamp("2016-12-30")
        shocked = closes.copy()
        shocked.loc[shocked.index > cut] *= 10.0
        bars = _bars("2016-08-01", cut)
        outputs = []
        for data in (closes, shocked):
            env = _Env(data)
            try:
                cycle = env.cycle(retrain_every_days=120)
                outputs.append([(r.session, r.retrained, r.scores) for r in (cycle.step(t) for t in bars)])
            finally:
                env.close()
        self.assertEqual(len(outputs[0]), len(outputs[1]))
        for (s0, t0, sc0), (s1, t1, sc1) in zip(*outputs):
            self.assertEqual((s0, t0), (s1, t1))
            self.assertEqual(sc0.keys(), sc1.keys())
            for k in sc0:
                self.assertAlmostEqual(sc0[k], sc1[k], places=10)

    def test_delisted_asset_triggers_retraining_without_stale_scores(self):
        closes = synthetic_closes(900)
        delist = pd.Timestamp("2016-11-01")
        closes.loc[closes.index > delist, "DDD"] = np.nan
        env = _Env(closes)
        try:
            cycle = env.cycle(retrain_every_days=365)
            results = [cycle.step(t) for t in _bars("2016-08-01", "2016-12-30")]
        finally:
            env.close()
        after = [r for r in results if r.session is not None and r.session > delist]
        self.assertTrue(any(r.retrained for r in after), "retrain once DDD leaves")
        for r in after:
            self.assertNotIn("DDD", r.scores)
            self.assertNotIn("DDD", r.eligible)


class TestMissingArtifactFiles(unittest.TestCase):

    def test_deleted_weight_files_trigger_retraining(self):
        import os
        env = _Env(synthetic_closes(900))
        try:
            cycle = env.cycle(retrain_every_days=365)
            bars = _bars("2016-08-01", "2016-08-31")
            for t in bars[:5]:
                cycle.step(t)
            store = STMArtifactStore(env.factory, env.cfg)
            self.assertTrue(store.list_artifacts())
            for artifact, _ in store.list_artifacts():
                os.remove(artifact.location)
            SpatioTemporalMomentumModelProvider.clear_cache()      # simulate a fresh process

            self.assertEqual(store.list_artifacts(), [], "rows without a file are not usable")
            r = cycle.step(bars[5])
            self.assertTrue(r.retrained, "missing files force a retrain")
            self.assertTrue(cycle.step(bars[6]).scores, "trading resumes from the next session")
        finally:
            env.close()


class TestIntradayClock(unittest.TestCase):
    """5-minute engine clock: one decision per daily session, other bars reuse it."""

    def test_same_session_bars_reuse_the_decision(self):
        env = _Env(synthetic_closes(900))
        try:
            cycle = env.cycle(retrain_every_days=365)
            day1 = pd.Timestamp("2016-08-01")
            day2 = pd.Timestamp("2016-08-02")
            day3 = pd.Timestamp("2016-08-03")
            r_train = cycle.step(day1 + pd.Timedelta(hours=9, minutes=35))      # trains (no scores yet)
            r_train_rep = cycle.step(day1 + pd.Timedelta(hours=9, minutes=40))
            self.assertTrue(r_train.retrained)
            self.assertFalse(r_train_rep.new_decision)
            self.assertFalse(r_train_rep.retrained, "no retraining on a repeated bar")

            first = cycle.step(day2 + pd.Timedelta(hours=9, minutes=35))
            repeats = [cycle.step(day2 + pd.Timedelta(hours=9, minutes=35 + 5 * k)) for k in range(1, 6)]
            self.assertTrue(first.new_decision and first.scores)
            for r in repeats:
                self.assertFalse(r.new_decision)
                self.assertEqual(r.session, first.session)
                self.assertEqual(r.scores, first.scores)
                self.assertEqual(r.weights, first.weights)
            nxt = cycle.step(day3 + pd.Timedelta(hours=9, minutes=35))
            self.assertTrue(nxt.new_decision)
            self.assertGreater(nxt.session, first.session)
        finally:
            env.close()

    def test_five_minute_project_is_configured_and_separate(self):
        import importlib.util
        if importlib.util.find_spec(
                "src.application.managers.project_managers.spatio_temporal_momentum_project_5m") is None:
            self.skipTest("spatio_temporal_momentum_project_5m folder not present")
        from src.application.managers.project_managers.spatio_temporal_momentum_project import config as daily
        from src.application.managers.project_managers.spatio_temporal_momentum_project_5m import config as five
        from src.application.managers.project_managers.spatio_temporal_momentum_project_5m.project_manager import (
            SpatioTemporalMomentum5mProjectManager,  # noqa: F401  (importable)
        )
        c5, cd = five.get_config(), daily.get_config()
        self.assertEqual(c5["config_interval"], {"custom_interval_minutes": 5})
        self.assertEqual(c5["bar_size_setting"], "5 mins")
        s5, sd = five.build_stm_configuration(c5), daily.build_stm_configuration(cd)
        for attr in ("ml_model_name_prefix", "signal_factor_name", "artifact_dir"):
            self.assertNotEqual(getattr(s5, attr), getattr(sd, attr), attr)
        self.assertNotEqual(s5.universe.name, sd.universe.name)
        self.assertNotEqual(c5["results_dir"], cd["results_dir"])
        self.assertEqual(s5.model_hash(), sd.model_hash(), "same daily-close model, only the clock differs")


class TestPaperUniverseProject(unittest.TestCase):

    def test_paper_universe_with_replacements_and_separate_state(self):
        from src.application.managers.project_managers.spatio_temporal_momentum_project import config as daily
        from src.application.managers.project_managers.spatio_temporal_momentum_project_full import config as paper
        from src.application.managers.project_managers.spatio_temporal_momentum_project_full.data.paper_universe import (
            ADDED_ALONGSIDE,
            PAPER_US_EQUITIES,
            REPLACED,
        )
        from src.application.managers.project_managers.spatio_temporal_momentum_project_full.project_manager import (
            SpatioTemporalMomentumFullProjectManager,  # noqa: F401  (importable)
        )
        self.assertEqual(len(PAPER_US_EQUITIES), 46)
        tickers = paper.build_stm_configuration().universe.tickers
        self.assertGreaterEqual(len(tickers), 46)
        for gone, (replacement, _) in REPLACED.items():
            self.assertNotIn(gone, tickers)
            self.assertIn(replacement, tickers)
        for kept, (added, _) in ADDED_ALONGSIDE.items():
            self.assertIn(kept, tickers)
            self.assertIn(added, tickers)
        others = set(PAPER_US_EQUITIES) - set(REPLACED)
        self.assertTrue(others.issubset(tickers))
        self.assertEqual(len(tickers), len(set(tickers)))
        self.assertEqual(list(paper.get_config()["universe"].values())[0], tickers)
        sp, sd = paper.build_stm_configuration(), daily.build_stm_configuration()
        for attr in ("ml_model_name_prefix", "signal_factor_name", "artifact_dir"):
            self.assertNotEqual(getattr(sp, attr), getattr(sd, attr), attr)
        self.assertNotEqual(paper.get_config()["results_dir"], daily.get_config()["results_dir"])


class TestFourMonthSetup(unittest.TestCase):
    """Project 4-month configuration: the cycle trades with ~84 sessions of history in total."""

    def test_trades_with_only_four_months_of_history(self):
        from src.application.managers.project_managers.spatio_temporal_momentum_project.config import (
            build_stm_configuration,
        )
        project_cfg = build_stm_configuration()
        closes = synthetic_closes(130, start="2025-08-25")          # ~4 months before the first bar + 1.5 months
        first_bar = closes.index[90]
        env = _Env(closes)
        try:
            cfg = env.cfg
            cfg.features = project_cfg.features
            cfg.model = project_cfg.model
            cfg.model.params = {"hidden_dim": 8, "n_heads": 2, "prescale_dim": 4, "emb_dim": 4}
            cfg.training.val_days = project_cfg.training.val_days
            cfg.training.rolling_window_rows = project_cfg.training.rolling_window_rows
            cycle = STMTradingCycle(env.factory, cfg, env.history, ENTITY_IDS, history_start="2025-08-25",
                                    retrain_every_days=30)
            results = [cycle.step(t) for t in _bars(first_bar, closes.index[-2])]
            for _, meta in STMArtifactStore(env.factory, cfg).list_artifacts():
                window = closes.loc[pd.Timestamp(meta["history_start"]):pd.Timestamp(meta["validation_end"])]
                self.assertEqual(len(window), 84, "rolling window of 84 sessions known at training time")
        finally:
            env.close()

        self.assertTrue(results[0].retrained, "first bar trains on ~4 months of data")
        self.assertTrue(results[1].scores, "trades from the next session")
        trained = [r for r in results if r.retrained]
        self.assertGreaterEqual(len(trained), 2, "retrains about monthly")
        for r in results:
            self.assertEqual(len(r.eligible), len(ASSETS))


class TestTrainAsOfMatchesWalkForward(unittest.TestCase):

    def test_model_trained_as_of_t_equals_the_walk_forward_window(self):
        closes = synthetic_closes(1000)
        cfg = tiny_config(model_type="mlp")
        cfg.training.n_epochs = 2
        start = pd.Timestamp(cfg.training.first_split_start)
        as_of = start + pd.Timedelta(days=cfg.training.val_days)
        full_panel = build_feature_panel(closes, cfg.features)
        known_panel = build_feature_panel(closes.loc[:as_of], cfg.features)

        tmp = tempfile.mkdtemp()
        try:
            cfg.artifact_dir = tmp
            f1, s1, e1 = make_factory()
            f2, s2, e2 = make_factory()
            wf = STMWalkForwardTrainer(cfg, factory=f1).run(full_panel, ENTITY_IDS)[0]
            live = STMWalkForwardTrainer(cfg, factory=f2).train_as_of(known_panel, as_of, ENTITY_IDS)
            a = load_model_file(f1.model_artifact_local_repo.get_by_id(wf.artifact_id).location)
            b = load_model_file(f2.model_artifact_local_repo.get_by_id(live.artifact_id).location)
            for k, v in a.model.state_dict().items():
                torch.testing.assert_close(v, b.model.state_dict()[k])
            for s, e in ((s1, e1), (s2, e2)):
                s.close()
                e.dispose()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_training_with_a_panel_that_extends_past_t_is_refused(self):
        closes = synthetic_closes(1000)
        cfg = tiny_config(model_type="mlp")
        panel = build_feature_panel(closes, cfg.features)
        with self.assertRaises(ValueError):
            STMWalkForwardTrainer(cfg).train_as_of(panel, "2016-12-01")


if __name__ == "__main__":
    unittest.main()
