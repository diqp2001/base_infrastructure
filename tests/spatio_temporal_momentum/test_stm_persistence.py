"""Artifact, signal and end-to-end tests against an in-memory SQLite RepositoryFactory."""

import shutil
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd
import torch

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_artifact_store import (
    load_model_file,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
    build_feature_panel,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_feature_store import (
    STMFeatureStore,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_model_provider import (
    SpatioTemporalMomentumModelProvider,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_training import predict_last_step
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_walk_forward import (
    STMWalkForwardTrainer,
)
from src.domain.entities.ml.model_artifact import ModelArtifact
from src.domain.entities.ml.model_training import ModelTraining
from tests.spatio_temporal_momentum.helpers import ASSETS, make_factory, seed_closes, synthetic_closes, tiny_config

ENTITY_IDS = {a: 100 + i for i, a in enumerate(ASSETS)}


class _DBCase(unittest.TestCase):

    def setUp(self):
        SpatioTemporalMomentumModelProvider.clear_cache()
        self.tmp = tempfile.mkdtemp()
        self.cfg = tiny_config(tmp_dir=self.tmp)
        self.factory, self.session, self.engine = make_factory()
        self.closes = synthetic_closes(1000)
        self.close_factor_id = seed_closes(self.session, self.closes, ENTITY_IDS)
        self.panel = build_feature_panel(self.closes, self.cfg.features)

    def tearDown(self):
        SpatioTemporalMomentumModelProvider.clear_cache()
        SpatioTemporalMomentumModelProvider.default_config = None
        self.session.close()
        self.engine.dispose()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _train(self):
        return STMWalkForwardTrainer(self.cfg, factory=self.factory).run(self.panel, ENTITY_IDS)


class TestArtifacts(_DBCase):

    def test_walk_forward_persists_training_metrics_and_artifacts(self):
        results = self._train()
        self.assertGreaterEqual(len(results), 2)
        for r in results:
            training = self.factory.model_training_local_repo.get_by_id(r.training_id)
            self.assertIsInstance(training, ModelTraining)
            self.assertEqual(training.status, "completed")
            artifact = self.factory.model_artifact_local_repo.get_by_id(r.artifact_id)
            self.assertIsInstance(artifact, ModelArtifact)
            meta = artifact.artifact_metadata
            for key in ("model_type", "assets", "asset_entity_ids", "feature_names", "lookback", "encoder_length",
                        "scaler", "training_end", "validation_end", "valid_from", "valid_until",
                        "model_params", "configuration", "torch_version", "history_start"):
                self.assertIn(key, meta)
            self.assertEqual(meta["assets"], ASSETS)
            self.assertEqual(meta["feature_names"], self.cfg.features.feature_names())
            metrics = {m.metric_name for m in self.factory.training_metric_local_repo.get_all()
                       if m.model_training_id == r.training_id}
            self.assertIn("sharpe_ratio_0bps", metrics)
        features = self.factory.model_feature_local_repo.get_all()
        self.assertEqual([f.name for f in features], self.cfg.features.feature_names())

    def test_saved_model_reloads_with_identical_predictions(self):
        results = self._train()
        r = results[0]
        artifact = self.factory.model_artifact_local_repo.get_by_id(r.artifact_id)
        loaded = load_model_file(artifact.location)
        reloaded_preds = predict_last_step(loaded.model, r.test, 32)
        np.testing.assert_allclose(reloaded_preds, r.test_preds, rtol=1e-6, atol=1e-7)


class TestSignals(_DBCase):

    def test_inference_produces_one_score_per_constituent_matching_research_prediction(self):
        results = self._train()
        r = results[0]
        d = r.test.dates[5]
        provider = SpatioTemporalMomentumModelProvider(factory=self.factory, config=self.cfg)
        scores = provider.score_universe(d, persist=True)
        self.assertEqual(set(scores), set(ENTITY_IDS.values()))
        expected = r.test_preds[5]
        got = np.array([scores[ENTITY_IDS[a]] for a in ASSETS])
        np.testing.assert_allclose(got, expected, rtol=1e-5, atol=1e-6)
        stored = STMFeatureStore(self.factory, self.cfg).read_signals(d)
        self.assertEqual(stored.keys(), scores.keys())

    def test_signal_factor_uses_repository_injected_provider(self):
        results = self._train()
        d = results[0].test.dates[3]
        SpatioTemporalMomentumModelProvider.default_config = self.cfg
        factor = STMFeatureStore(self.factory, self.cfg).ensure_signal_factor()
        self.assertIsNotNone(factor._provider)
        value = factor.calculate({"entity": SimpleNamespace(id=ENTITY_IDS["BBB"]), "target_date": d})
        self.assertAlmostEqual(value, float(results[0].test_preds[3][1]), places=5)

    def test_no_signal_without_an_out_of_sample_artifact(self):
        self._train()
        provider = SpatioTemporalMomentumModelProvider(factory=self.factory, config=self.cfg)
        self.assertEqual(provider.score_universe("2016-06-01"), {})  # before any validation ended


if __name__ == "__main__":
    unittest.main()
