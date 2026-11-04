"""P.08.12 (GA-E6): research / live decision parity. The research project (spatio_temporal_momentum_project_10m,
the backtests) and the live project (spatio_temporal_momentum_project_10m_live) must decide the SAME weights from the
same data and the same trained model. In-memory SQLite, synthetic closes, a shrunk model; nothing is stored anywhere
else (temp artifact folder).

  1. configuration: every setting the model or the decision reads is identical; the differences are named below
     (names / folders, and the KNOWN cycle differences, which change WHEN a model is retrained, not how it decides);
  2. decisions: both projects' cycles, built with their own settings on one fixture, score with the same model and
     return identical weights at every decision.
"""

import tempfile
import unittest
from dataclasses import asdict, is_dataclass
from types import SimpleNamespace

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.managers.project_managers.spatio_temporal_momentum_project_10m import config as research
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.backtesting.synthetic_demo import (
    _seed_closes, synthetic_universe_closes,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live import config as live
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import bars_per_session
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_trading_cycle import STMTradingCycle
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_universe import STMUniverseService
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService

# names and folders: each project keeps its own models, factors, universe and results
NAMING = {".artifact_dir", ".feature_factor_prefix", ".ml_model_name_prefix", ".signal_factor_name",
          ".universe.name"}
# cycle settings that differ ON PURPOSE today (owner to confirm): when the model is retrained, not how it decides
KNOWN_CYCLE_DIFFERENCES = {"retrain_every_days": (1, 2), "missing_asset_patience": (0, 3)}
CYCLE_KEYS = ("retrain_every_days", "missing_asset_patience", "gross_exposure_cap")
TICKERS = ["JPM", "BAC", "WFC", "C", "USB", "PNC"]


def _flat(obj, prefix=""):
    data = asdict(obj) if is_dataclass(obj) else obj
    if not isinstance(data, dict):
        return {prefix: data}
    out = {}
    for k, v in data.items():
        out.update(_flat(v, f"{prefix}.{k}"))
    return out


def _cycle_settings(config):
    return {"retrain_every_days": config.get("retrain_every_days", 365),
            "missing_asset_patience": config.get("missing_asset_patience", 0) or 0,
            "gross_exposure_cap": config.get("gross_exposure_cap", 1.0)}


class ConfigurationParityTest(unittest.TestCase):

    def test_the_model_and_decision_settings_are_identical(self):
        r = _flat(research.build_stm_configuration(research.get_config()))
        lv = _flat(live.build_stm_configuration(live.get_config()))
        different = {k for k in set(r) | set(lv) if str(r.get(k)) != str(lv.get(k))}
        self.assertEqual(different - NAMING, set(), {k: (r.get(k), lv.get(k)) for k in different - NAMING})

    def test_cycle_settings_differ_only_where_known(self):
        r, lv = _cycle_settings(research.get_config()), _cycle_settings(live.get_config())
        different = {k: (r[k], lv[k]) for k in CYCLE_KEYS if r[k] != lv[k]}
        self.assertEqual(different, KNOWN_CYCLE_DIFFERENCES)


class DecisionParityTest(unittest.TestCase):
    """Same fixture, same model: research and live weights identical at every decision."""

    @classmethod
    def setUpClass(cls):
        from src.application.services.data.entities.factor import preloaded_coverage
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_model_provider import (
            SpatioTemporalMomentumModelProvider,
        )
        from src.infrastructure.models import ModelBase
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        # process-wide caches are keyed by database ids: another test's in-memory database reuses artifact id 1
        SpatioTemporalMomentumModelProvider.clear_cache()
        preloaded_coverage.clear()
        cls.research_config, cls.live_config = research.get_config(), live.get_config()
        artifacts = tempfile.mkdtemp(prefix="stm_parity_")
        cls.stm = {}
        for name, module, config in (("research", research, cls.research_config), ("live", live, cls.live_config)):
            stm = module.build_stm_configuration(config)
            stm.universe.tickers = list(TICKERS)
            stm.model.params = {"hidden_dim": 8, "n_heads": 2, "prescale_dim": 4, "emb_dim": 4, "dropout": 0.1}
            stm.training.n_epochs = 2
            stm.artifact_dir = artifacts
            cls.stm[name] = stm
        # one model for both: the live cycle finds the research cycle's artifact (names are per project otherwise)
        r, lv = cls.stm["research"], cls.stm["live"]
        lv.ml_model_name_prefix, lv.feature_factor_prefix = r.ml_model_name_prefix, r.feature_factor_prefix
        lv.signal_factor_name, lv.universe.name = r.signal_factor_name, r.universe.name
        bar_minutes = r.bar_minutes
        cls.history_rows = int(cls.research_config["training_window"]) + bars_per_session(bar_minutes)
        cls.closes = synthetic_universe_closes(TICKERS, "2026-09-01", cls.history_rows + 8, bar_minutes, seed=11)
        cls.engine = create_engine("sqlite:///:memory:")
        ModelBase.metadata.create_all(cls.engine)
        cls.session = Session(cls.engine)
        cls.factory = RepositoryFactory(cls.session)
        cls.ids = {t: 2000 + i for i, t in enumerate(TICKERS)}
        _seed_closes(cls.session, cls.closes, cls.ids, bar_minutes)
        cls.bar_minutes = bar_minutes

    @classmethod
    def tearDownClass(cls):
        cls.session.close()
        cls.engine.dispose()

    def _cycle(self, name):
        stm = self.stm[name]
        config = self.research_config if name == "research" else self.live_config
        universe_service = STMUniverseService(self.factory, stm.universe)
        universe = universe_service.ensure_universe(self.ids, self.closes.index[0].date())
        history = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(
            repository_factory=self.factory)))
        settings = _cycle_settings(config)
        return STMTradingCycle(self.factory, stm, history, self.ids, history_start=self.closes.index[0].normalize(),
                               retrain_every_days=settings["retrain_every_days"],
                               universe_service=universe_service, universe_id=universe.id,
                               gross_cap=settings["gross_exposure_cap"],
                               missing_asset_patience=settings["missing_asset_patience"], log=lambda m: None)

    def test_same_data_same_model_same_weights(self):
        step = pd.Timedelta(minutes=self.bar_minutes)
        decisions = [d + step for d in self.closes.index[self.history_rows:self.history_rows + 6]]
        research_cycle = self._cycle("research")
        research_results = [research_cycle.step(t) for t in decisions]          # trains once, then scores
        live_cycle = self._cycle("live")
        live_results = [live_cycle.step(t) for t in decisions]                  # same model: no retraining
        self.assertTrue(any(r.retrained for r in research_results))
        self.assertFalse(any(r.retrained for r in live_results))
        scored = [(r, lv) for r, lv in zip(research_results, live_results) if r.weights]
        self.assertGreaterEqual(len(scored), 3)
        for r, lv in zip(research_results, live_results):
            self.assertEqual(r.session, lv.session)
            self.assertEqual(sorted(r.weights), sorted(lv.weights))
            for ticker, weight in r.weights.items():
                self.assertAlmostEqual(weight, lv.weights[ticker], places=12, msg=f"{r.session} {ticker}")
        self.assertEqual(research_cycle.model_artifact_id(), live_cycle.model_artifact_id())


if __name__ == "__main__":
    unittest.main()
