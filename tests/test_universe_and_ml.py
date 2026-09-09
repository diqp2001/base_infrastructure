"""
tests/test_universe_and_ml.py

Unit tests for:
- Universe / UniverseConstituent domain entities + repos
- MLModel, ModelFeature, ModelTraining, TrainingMetric, ModelArtifact domain entities + repos
- ConstituentScoreFactor
"""

import unittest
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.infrastructure.models import (
    ModelBase,
    UniverseModel,
    UniverseConstituentModel,
    MLModelModel,
    ModelFeatureModel,
    ModelTrainingModel,
    TrainingMetricModel,
    ModelArtifactModel,
)
from src.infrastructure.repositories.repository_factory import RepositoryFactory

# Domain entities
from src.domain.entities.universe.universe import Universe
from src.domain.entities.universe.universe_constituent import UniverseConstituent
from src.domain.entities.ml.ml_model import MLModel
from src.domain.entities.ml.model_feature import ModelFeature
from src.domain.entities.ml.model_training import ModelTraining
from src.domain.entities.ml.training_metric import TrainingMetric
from src.domain.entities.ml.model_artifact import ModelArtifact
from src.domain.entities.factor.constituent_score_factor import ConstituentScoreFactor


def _make_engine():
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    return engine


class TestUniverse(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine()
        self.session = Session(self.engine)
        self.factory = RepositoryFactory(self.session)
        self.repo = self.factory.investment_universe_local_repo

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_create_universe(self):
        u = Universe(name="SP500", description="S&P 500 index constituents")
        created = self.repo.add(u)
        self.assertIsNotNone(created)
        self.assertIsNotNone(created.id)
        self.assertEqual(created.name, "SP500")

    def test_get_by_name(self):
        u = Universe(name="Russell1000")
        self.repo.add(u)
        found = self.repo.get_by_name("Russell1000")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Russell1000")

    def test_create_or_get_idempotent(self):
        entity_cls = Universe
        r1 = self.repo._create_or_get(entity_cls, "SP500", description="First")
        r2 = self.repo._create_or_get(entity_cls, "SP500", description="Second")
        self.assertIsNotNone(r1)
        self.assertIsNotNone(r2)
        self.assertEqual(r1.id, r2.id)

    def test_get_all(self):
        self.repo.add(Universe(name="A"))
        self.repo.add(Universe(name="B"))
        all_u = self.repo.get_all()
        names = {u.name for u in all_u}
        self.assertIn("A", names)
        self.assertIn("B", names)

    def test_delete(self):
        u = self.repo.add(Universe(name="ToDelete"))
        self.assertIsNotNone(u)
        result = self.repo.delete(u.id)
        self.assertTrue(result)
        self.assertIsNone(self.repo.get_by_id(u.id))


class TestUniverseConstituent(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine()
        self.session = Session(self.engine)
        self.factory = RepositoryFactory(self.session)
        self.u_repo = self.factory.investment_universe_local_repo
        self.repo = self.factory.universe_constituent_local_repo
        self.universe = self.u_repo.add(Universe(name="TestUniverse"))

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_create_constituent(self):
        c = UniverseConstituent(
            universe_id=self.universe.id,
            entity_id=1,
            entity_type="CompanyShare",
            start_date=date(2024, 1, 1),
        )
        created = self.repo.add(c)
        self.assertIsNotNone(created)
        self.assertEqual(created.universe_id, self.universe.id)
        self.assertEqual(created.entity_type, "CompanyShare")

    def test_is_active_no_end_date(self):
        c = UniverseConstituent(
            universe_id=self.universe.id,
            entity_id=2,
            entity_type="CompanyShare",
            start_date=date(2024, 1, 1),
        )
        self.assertTrue(c.is_active)

    def test_is_active_with_end_date(self):
        c = UniverseConstituent(
            universe_id=self.universe.id,
            entity_id=3,
            entity_type="CompanyShare",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )
        self.assertFalse(c.is_active)

    def test_get_active_by_universe(self):
        self.repo.add(UniverseConstituent(
            universe_id=self.universe.id, entity_id=10, entity_type="CompanyShare",
            start_date=date(2024, 1, 1),
        ))
        self.repo.add(UniverseConstituent(
            universe_id=self.universe.id, entity_id=11, entity_type="CompanyShare",
            start_date=date(2024, 1, 1), end_date=date(2024, 3, 31),
        ))
        active = self.repo.get_active_by_universe(self.universe.id, as_of=date(2024, 6, 1))
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].entity_id, 10)

    def test_create_or_get_idempotent(self):
        r1 = self.repo._create_or_get(
            UniverseConstituent, "uc_key",
            universe_id=self.universe.id, entity_id=99,
            entity_type="CompanyShare", start_date=date(2024, 1, 1),
        )
        r2 = self.repo._create_or_get(
            UniverseConstituent, "uc_key",
            universe_id=self.universe.id, entity_id=99,
            entity_type="CompanyShare", start_date=date(2024, 1, 1),
        )
        self.assertIsNotNone(r1)
        self.assertIsNotNone(r2)
        self.assertEqual(r1.id, r2.id)


class TestMLModel(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine()
        self.session = Session(self.engine)
        self.factory = RepositoryFactory(self.session)
        self.repo = self.factory.ml_model_local_repo

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_create_ml_model(self):
        m = MLModel(
            name="LightGBM_Return",
            model_type="lightgbm",
            configuration={"n_estimators": 100, "learning_rate": 0.05},
        )
        created = self.repo.add(m)
        self.assertIsNotNone(created)
        self.assertEqual(created.name, "LightGBM_Return")
        self.assertEqual(created.model_type, "lightgbm")

    def test_configuration_json_roundtrip(self):
        m = MLModel(
            name="JsonTest",
            model_type="random_forest",
            configuration={"n_estimators": 200},
        )
        created = self.repo.add(m)
        self.assertIsNotNone(created.configuration)
        self.assertEqual(created.configuration.get("n_estimators"), 200)

    def test_get_by_name(self):
        self.repo.add(MLModel(name="FindMe", model_type="logistic_regression"))
        found = self.repo.get_by_name("FindMe")
        self.assertIsNotNone(found)

    def test_delete(self):
        m = self.repo.add(MLModel(name="DelModel", model_type="lightgbm"))
        self.assertTrue(self.repo.delete(m.id))
        self.assertIsNone(self.repo.get_by_id(m.id))


class TestModelTraining(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine()
        self.session = Session(self.engine)
        self.factory = RepositoryFactory(self.session)
        self.ml_repo = self.factory.ml_model_local_repo
        self.repo = self.factory.model_training_local_repo
        self.model = self.ml_repo.add(MLModel(name="TrainMe", model_type="lightgbm"))

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_create_training(self):
        t = ModelTraining(
            model_id=self.model.id,
            training_start_date=date(2020, 1, 1),
            training_end_date=date(2022, 12, 31),
        )
        created = self.repo.add(t)
        self.assertIsNotNone(created)
        self.assertEqual(created.status, "pending")

    def test_status_transitions(self):
        t = ModelTraining(model_id=self.model.id, training_start_date=date(2020, 1, 1))
        t.mark_running()
        self.assertEqual(t.status, "running")
        self.assertIsNotNone(t.started_at)
        t.mark_completed()
        self.assertEqual(t.status, "completed")
        self.assertIsNotNone(t.completed_at)

    def test_mark_failed(self):
        t = ModelTraining(model_id=self.model.id)
        t.mark_failed()
        self.assertEqual(t.status, "failed")


class TestTrainingMetric(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine()
        self.session = Session(self.engine)
        self.factory = RepositoryFactory(self.session)
        ml_repo = self.factory.ml_model_local_repo
        tr_repo = self.factory.model_training_local_repo
        self.repo = self.factory.training_metric_local_repo
        model = ml_repo.add(MLModel(name="MetricTest", model_type="lightgbm"))
        self.training = tr_repo.add(ModelTraining(model_id=model.id))

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_create_metric(self):
        m = TrainingMetric(
            model_training_id=self.training.id,
            metric_name="roc_auc",
            metric_value=Decimal("0.85"),
            dataset_type="validation",
        )
        created = self.repo.add(m)
        self.assertIsNotNone(created)
        self.assertEqual(created.metric_name, "roc_auc")
        self.assertAlmostEqual(float(created.metric_value), 0.85, places=4)

    def test_get_by_training_and_dataset(self):
        self.repo.add(TrainingMetric(
            model_training_id=self.training.id,
            metric_name="f1", metric_value=Decimal("0.7"), dataset_type="training",
        ))
        self.repo.add(TrainingMetric(
            model_training_id=self.training.id,
            metric_name="roc_auc", metric_value=Decimal("0.8"), dataset_type="validation",
        ))
        val_metrics = self.repo.get_by_training_and_dataset(self.training.id, "validation")
        self.assertEqual(len(val_metrics), 1)
        self.assertEqual(val_metrics[0].metric_name, "roc_auc")

    def test_create_or_get_idempotent(self):
        r1 = self.repo._create_or_get(
            TrainingMetric, "auc",
            model_training_id=self.training.id, metric_name="roc_auc",
            metric_value=Decimal("0.9"), dataset_type="test",
        )
        r2 = self.repo._create_or_get(
            TrainingMetric, "auc",
            model_training_id=self.training.id, metric_name="roc_auc",
            metric_value=Decimal("0.95"), dataset_type="test",
        )
        self.assertIsNotNone(r1)
        self.assertEqual(r1.id, r2.id)
        self.assertAlmostEqual(float(r1.metric_value), 0.9, places=4)


class TestModelArtifact(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine()
        self.session = Session(self.engine)
        self.factory = RepositoryFactory(self.session)
        ml_repo = self.factory.ml_model_local_repo
        tr_repo = self.factory.model_training_local_repo
        self.repo = self.factory.model_artifact_local_repo
        model = ml_repo.add(MLModel(name="ArtifactTest", model_type="lightgbm"))
        self.training = tr_repo.add(ModelTraining(model_id=model.id))

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_create_artifact(self):
        a = ModelArtifact(
            model_training_id=self.training.id,
            artifact_type="trained_model",
            name="model.pkl",
            location="/models/run1/model.pkl",
            format="pickle",
        )
        created = self.repo.add(a)
        self.assertIsNotNone(created)
        self.assertEqual(created.artifact_type, "trained_model")
        self.assertEqual(created.location, "/models/run1/model.pkl")

    def test_get_by_training_and_type(self):
        self.repo.add(ModelArtifact(
            model_training_id=self.training.id,
            artifact_type="trained_model",
            name="model.pkl", location="/a/model.pkl",
        ))
        self.repo.add(ModelArtifact(
            model_training_id=self.training.id,
            artifact_type="feature_importance",
            name="fi.csv", location="/a/fi.csv",
        ))
        arts = self.repo.get_by_training_and_type(self.training.id, "trained_model")
        self.assertEqual(len(arts), 1)
        self.assertEqual(arts[0].name, "model.pkl")


class TestConstituentScoreFactor(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine()
        self.session = Session(self.engine)
        self.factory = RepositoryFactory(self.session)
        self.repo = self.factory.constituent_score_factor_local_repo

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_defaults(self):
        f = ConstituentScoreFactor()
        self.assertEqual(f.name, "constituent_score")
        self.assertEqual(f.group, "fundamental")
        self.assertEqual(f.subgroup, "score")
        self.assertEqual(f.source, "calculated")
        self.assertIsNone(f.score_type)

    def test_calculate_returns_none(self):
        f = ConstituentScoreFactor()
        self.assertIsNone(f.calculate({}))

    def test_create_or_get(self):
        r1 = self.repo._create_or_get(ConstituentScoreFactor, "momentum_rank")
        r2 = self.repo._create_or_get(ConstituentScoreFactor, "momentum_rank")
        self.assertIsNotNone(r1)
        self.assertIsNotNone(r1.id)
        self.assertEqual(r1.id, r2.id)

    def test_get_by_name(self):
        self.repo._create_or_get(ConstituentScoreFactor, "zscore_factor")
        found = self.repo.get_by_name("zscore_factor")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "zscore_factor")

    def test_get_all(self):
        self.repo._create_or_get(ConstituentScoreFactor, "score_a")
        self.repo._create_or_get(ConstituentScoreFactor, "score_b")
        all_factors = self.repo.get_all()
        names = {f.name for f in all_factors}
        self.assertIn("score_a", names)
        self.assertIn("score_b", names)


if __name__ == "__main__":
    unittest.main()
