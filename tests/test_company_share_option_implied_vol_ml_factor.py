"""
Tests for CompanyShareOptionImpliedVolMlFactor and associated ML lifecycle components.

Coverage:
- Analytical factor (CompanyShareOptionImpliedVolFactor) unchanged / still functional
- ML factor domain entity attributes and calculate_dependencies
- ML factor calculate() without / with provider
- ImpliedVolMlModelConfiguration: deterministic hash
- ImpliedVolMlFeatureDefinition: deterministic hash, feature extraction
- ImpliedVolMlModelProvider: regime key, cache hit, artifact validation, no-factory guard
- No recursive training: universe fingerprint targets analytical factor only
- Batch efficiency: class-level cache shared across provider instances
"""

import hashlib
import json
import math
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(strike=100.0, option_type="call", expiry_date=date(2026, 12, 31)):
    entity = SimpleNamespace()
    entity.strike_price = strike
    entity.option_type = option_type
    entity.end_date = expiry_date
    return entity


def _make_deps(opt_price=5.0, stock_price=100.0, rf_rate=0.05):
    return {
        "CompanyShareOptionValueFactor": opt_price,
        "CompanyShareValueFactor": stock_price,
        "CompanyShareOptionRFYieldFactor": rf_rate,
        "entity": _make_entity(),
        "target_date": date(2026, 6, 1),
    }


# ---------------------------------------------------------------------------
# 1. Analytical factor still functional
# ---------------------------------------------------------------------------

class TestAnalyticalFactorUnchanged(unittest.TestCase):

    def test_analytical_factor_importable(self):
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor import (
            CompanyShareOptionImpliedVolFactor,
        )
        self.assertIsNotNone(CompanyShareOptionImpliedVolFactor)

    def test_analytical_factor_attributes(self):
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor import (
            CompanyShareOptionImpliedVolFactor,
        )
        f = CompanyShareOptionImpliedVolFactor()
        self.assertEqual(f.group, "volatility")
        self.assertEqual(f.subgroup, "implied")
        self.assertEqual(f.frequency, "1d")

    def test_analytical_factor_has_calculate_dependencies(self):
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor import (
            CompanyShareOptionImpliedVolFactor,
        )
        f = CompanyShareOptionImpliedVolFactor()
        deps = f.calculate_dependencies
        self.assertIsInstance(deps, list)
        self.assertGreater(len(deps), 0)

    def test_analytical_and_ml_are_distinct_classes(self):
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor import (
            CompanyShareOptionImpliedVolFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_ml_factor import (
            CompanyShareOptionImpliedVolMlFactor,
        )
        self.assertIsNot(CompanyShareOptionImpliedVolFactor, CompanyShareOptionImpliedVolMlFactor)


# ---------------------------------------------------------------------------
# 2. ML factor domain entity
# ---------------------------------------------------------------------------

class TestMlFactorDomainEntity(unittest.TestCase):

    def setUp(self):
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_ml_factor import (
            CompanyShareOptionImpliedVolMlFactor,
        )
        self.FactorClass = CompanyShareOptionImpliedVolMlFactor

    def test_default_attributes(self):
        f = self.FactorClass()
        self.assertEqual(f.name, "implied_vol_ml")
        self.assertEqual(f.group, "volatility")
        self.assertEqual(f.subgroup, "implied")
        self.assertEqual(f.frequency, "1d")
        self.assertEqual(f.source, "calculated")

    def test_provider_none_by_default(self):
        f = self.FactorClass()
        self.assertIsNone(f._provider)

    def test_calculate_returns_none_without_provider(self):
        f = self.FactorClass()
        result = f.calculate(_make_deps())
        self.assertIsNone(result)

    def test_calculate_returns_none_when_entity_missing(self):
        provider = MagicMock()
        f = self.FactorClass(provider=provider)
        result = f.calculate({"target_date": date(2026, 6, 1)})
        self.assertIsNone(result)
        provider.predict.assert_not_called()

    def test_calculate_returns_none_when_date_missing(self):
        provider = MagicMock()
        f = self.FactorClass(provider=provider)
        result = f.calculate({"entity": _make_entity()})
        self.assertIsNone(result)
        provider.predict.assert_not_called()

    def test_calculate_delegates_to_provider(self):
        provider = MagicMock()
        provider.predict.return_value = 0.25
        f = self.FactorClass(provider=provider)
        deps = _make_deps()
        result = f.calculate(deps)
        self.assertEqual(result, 0.25)
        provider.predict.assert_called_once()

    def test_calculate_dependencies_returns_three_specs(self):
        f = self.FactorClass()
        specs = f.calculate_dependencies
        self.assertEqual(len(specs), 3)

    def test_calculate_dependencies_references_correct_factor_types(self):
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_value_factor import (
            CompanyShareOptionValueFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import (
            CompanyShareValueFactor,
        )
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rf_yield_factor import (
            CompanyShareOptionRFYieldFactor,
        )
        f = self.FactorClass()
        spec_types = {spec.factor_type for spec in f.calculate_dependencies}
        self.assertIn(CompanyShareOptionValueFactor, spec_types)
        self.assertIn(CompanyShareValueFactor, spec_types)
        self.assertIn(CompanyShareOptionRFYieldFactor, spec_types)


# ---------------------------------------------------------------------------
# 3. ImpliedVolMlModelConfiguration
# ---------------------------------------------------------------------------

class TestImpliedVolMlModelConfiguration(unittest.TestCase):

    def setUp(self):
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_configuration import (
            ImpliedVolMlModelConfiguration,
        )
        self.Config = ImpliedVolMlModelConfiguration

    def test_hash_is_string(self):
        h = self.Config().hash()
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)

    def test_hash_is_deterministic(self):
        self.assertEqual(self.Config().hash(), self.Config().hash())

    def test_different_config_different_hash(self):
        h1 = self.Config(n_estimators=100).hash()
        h2 = self.Config(n_estimators=200).hash()
        self.assertNotEqual(h1, h2)

    def test_to_dict_round_trips(self):
        c = self.Config(max_depth=7, model_type="random_forest")
        d = c.to_dict()
        self.assertEqual(d["max_depth"], 7)
        self.assertEqual(d["model_type"], "random_forest")


# ---------------------------------------------------------------------------
# 4. ImpliedVolMlFeatureDefinition
# ---------------------------------------------------------------------------

class TestImpliedVolMlFeatureDefinition(unittest.TestCase):

    def setUp(self):
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_feature_definition import (
            ImpliedVolMlFeatureDefinition,
        )
        self.FeatureDef = ImpliedVolMlFeatureDefinition
        self.fd = ImpliedVolMlFeatureDefinition()

    def test_hash_is_64_hex(self):
        h = self.fd.hash()
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)

    def test_hash_is_deterministic(self):
        self.assertEqual(self.FeatureDef().hash(), self.FeatureDef().hash())

    def test_extract_returns_six_features(self):
        entity = _make_entity(strike=100.0, option_type="call", expiry_date=date(2026, 12, 31))
        deps = {
            "CompanyShareOptionValueFactor": 5.0,
            "CompanyShareValueFactor": 100.0,
            "CompanyShareOptionRFYieldFactor": 0.05,
        }
        features = self.fd.extract(deps, entity, date(2026, 6, 1))
        self.assertIsNotNone(features)
        self.assertEqual(len(features), 6)

    def test_extract_moneyness_correct(self):
        entity = _make_entity(strike=100.0, option_type="call", expiry_date=date(2026, 12, 31))
        deps = {
            "CompanyShareOptionValueFactor": 5.0,
            "CompanyShareValueFactor": 110.0,
            "CompanyShareOptionRFYieldFactor": 0.05,
        }
        features = self.fd.extract(deps, entity, date(2026, 6, 1))
        self.assertIsNotNone(features)
        moneyness = features[0]
        self.assertAlmostEqual(moneyness, 110.0 / 100.0, places=6)
        log_moneyness = features[1]
        self.assertAlmostEqual(log_moneyness, math.log(1.1), places=6)

    def test_extract_is_call_correct(self):
        entity_call = _make_entity(option_type="call", expiry_date=date(2026, 12, 31))
        entity_put = _make_entity(option_type="put", expiry_date=date(2026, 12, 31))
        deps = {
            "CompanyShareOptionValueFactor": 5.0,
            "CompanyShareValueFactor": 100.0,
            "CompanyShareOptionRFYieldFactor": 0.05,
        }
        features_call = self.fd.extract(deps, entity_call, date(2026, 6, 1))
        features_put = self.fd.extract(deps, entity_put, date(2026, 6, 1))
        self.assertEqual(features_call[5], 1.0)
        self.assertEqual(features_put[5], 0.0)

    def test_extract_returns_none_when_option_price_missing(self):
        entity = _make_entity()
        deps = {
            "CompanyShareValueFactor": 100.0,
            "CompanyShareOptionRFYieldFactor": 0.05,
        }
        self.assertIsNone(self.fd.extract(deps, entity, date(2026, 6, 1)))

    def test_extract_returns_none_when_stock_price_missing(self):
        entity = _make_entity()
        deps = {
            "CompanyShareOptionValueFactor": 5.0,
            "CompanyShareOptionRFYieldFactor": 0.05,
        }
        self.assertIsNone(self.fd.extract(deps, entity, date(2026, 6, 1)))

    def test_extract_returns_none_when_expired(self):
        entity = _make_entity(expiry_date=date(2025, 1, 1))
        deps = {
            "CompanyShareOptionValueFactor": 5.0,
            "CompanyShareValueFactor": 100.0,
            "CompanyShareOptionRFYieldFactor": 0.05,
        }
        self.assertIsNone(self.fd.extract(deps, entity, date(2026, 6, 1)))

    def test_extract_returns_none_when_no_strike(self):
        entity = SimpleNamespace(option_type="call", end_date=date(2026, 12, 31))
        deps = {
            "CompanyShareOptionValueFactor": 5.0,
            "CompanyShareValueFactor": 100.0,
            "CompanyShareOptionRFYieldFactor": 0.05,
        }
        self.assertIsNone(self.fd.extract(deps, entity, date(2026, 6, 1)))


# ---------------------------------------------------------------------------
# 5. ImpliedVolMlModelProvider — unit tests with mocks
# ---------------------------------------------------------------------------

class TestImpliedVolMlModelProvider(unittest.TestCase):

    def setUp(self):
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_provider import (
            ImpliedVolMlModelProvider,
        )
        self.Provider = ImpliedVolMlModelProvider
        ImpliedVolMlModelProvider.clear_cache()

    def tearDown(self):
        self.Provider.clear_cache()

    def _make_provider(self, factory=None):
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_configuration import (
            ImpliedVolMlModelConfiguration,
        )
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_feature_definition import (
            ImpliedVolMlFeatureDefinition,
        )
        return self.Provider(
            factory=factory,
            config=ImpliedVolMlModelConfiguration(),
            feature_def=ImpliedVolMlFeatureDefinition(),
        )

    def test_predict_returns_none_when_features_cannot_be_extracted(self):
        provider = self._make_provider()
        entity = SimpleNamespace()  # no attributes
        result = provider.predict({}, entity, date(2026, 6, 1))
        self.assertIsNone(result)

    def test_predict_returns_none_with_no_factory(self):
        provider = self._make_provider(factory=None)
        entity = _make_entity()
        deps = _make_deps()
        # Even if features extracted, model cannot be loaded/trained without factory
        result = provider.predict(deps, entity, date(2026, 6, 1))
        self.assertIsNone(result)

    def test_regime_key_is_deterministic(self):
        factory = MagicMock()
        factory.session = MagicMock()

        session_mock = factory.session
        factor_query = MagicMock()
        factor_query.filter.return_value.all.return_value = []
        session_mock.query.return_value = factor_query

        p1 = self._make_provider(factory=factory)
        p2 = self._make_provider(factory=factory)
        k1 = p1._compute_regime_key(date(2026, 6, 1))
        k2 = p2._compute_regime_key(date(2026, 6, 1))
        self.assertEqual(k1, k2)

    def test_regime_key_changes_with_different_config(self):
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_configuration import (
            ImpliedVolMlModelConfiguration,
        )
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_feature_definition import (
            ImpliedVolMlFeatureDefinition,
        )

        factory = MagicMock()
        factory.session = MagicMock()
        factor_query = MagicMock()
        factor_query.filter.return_value.all.return_value = []
        factory.session.query.return_value = factor_query

        p1 = self.Provider(factory=factory, config=ImpliedVolMlModelConfiguration(n_estimators=100), feature_def=ImpliedVolMlFeatureDefinition())
        p2 = self.Provider(factory=factory, config=ImpliedVolMlModelConfiguration(n_estimators=999), feature_def=ImpliedVolMlFeatureDefinition())
        k1 = p1._compute_regime_key(date(2026, 6, 1))
        k2 = p2._compute_regime_key(date(2026, 6, 1))
        self.assertNotEqual(k1, k2)

    def test_cache_hit_avoids_artifact_load(self):
        """Second call with same regime key uses in-memory cache — no artifact scan."""
        provider = self._make_provider()
        regime_key = "test_regime_key_abc"
        mock_model = MagicMock()
        self.Provider._model_cache[regime_key] = mock_model

        # Patch _compute_regime_key to return our key
        with patch.object(provider, "_compute_regime_key", return_value=regime_key):
            with patch.object(provider, "_load_artifact") as mock_load:
                result = provider._get_or_train_model(date(2026, 6, 1))
                mock_load.assert_not_called()
        self.assertIs(result, mock_model)

    def test_cache_miss_tries_artifact(self):
        """Cache miss → tries to load artifact before training."""
        provider = self._make_provider()
        regime_key = "fresh_regime_xyz"
        with patch.object(provider, "_compute_regime_key", return_value=regime_key):
            with patch.object(provider, "_load_artifact", return_value=None) as mock_load:
                with patch.object(provider, "_train_and_cache", return_value=None) as mock_train:
                    provider._get_or_train_model(date(2026, 6, 1))
                    mock_load.assert_called_once_with(regime_key, date(2026, 6, 1))
                    mock_train.assert_called_once_with(regime_key, date(2026, 6, 1))

    def test_artifact_loaded_stored_in_cache(self):
        """If artifact loads successfully it is put in _model_cache."""
        provider = self._make_provider()
        regime_key = "cached_after_load"
        mock_model = MagicMock()
        with patch.object(provider, "_compute_regime_key", return_value=regime_key):
            with patch.object(provider, "_load_artifact", return_value=mock_model):
                result = provider._get_or_train_model(date(2026, 6, 1))
        self.assertIs(self.Provider._model_cache.get(regime_key), mock_model)
        self.assertIs(result, mock_model)

    def test_predict_clamps_result_below_minimum(self):
        """Predicted value below 0.001 is clamped to 0.001."""
        provider = self._make_provider()
        entity = _make_entity()
        deps = _make_deps()

        mock_model = MagicMock()
        import numpy as np
        mock_model.predict.return_value = np.array([-5.0])

        with patch.object(provider, "_get_or_train_model", return_value=mock_model):
            result = provider.predict(deps, entity, date(2026, 6, 1))
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, 0.001)

    def test_predict_clamps_result_above_maximum(self):
        """Predicted value above 20.0 is clamped to 20.0."""
        provider = self._make_provider()
        entity = _make_entity()
        deps = _make_deps()

        mock_model = MagicMock()
        import numpy as np
        mock_model.predict.return_value = np.array([999.0])

        with patch.object(provider, "_get_or_train_model", return_value=mock_model):
            result = provider.predict(deps, entity, date(2026, 6, 1))
        self.assertIsNotNone(result)
        self.assertLessEqual(result, 20.0)

    def test_clear_cache(self):
        self.Provider._model_cache["some_key"] = MagicMock()
        self.Provider.clear_cache()
        self.assertEqual(len(self.Provider._model_cache), 0)


# ---------------------------------------------------------------------------
# 6. Artifact matching
# ---------------------------------------------------------------------------

class TestArtifactMatching(unittest.TestCase):

    def setUp(self):
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_provider import (
            ImpliedVolMlModelProvider,
        )
        self.Provider = ImpliedVolMlModelProvider
        ImpliedVolMlModelProvider.clear_cache()

    def tearDown(self):
        self.Provider.clear_cache()

    def _provider(self):
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_configuration import ImpliedVolMlModelConfiguration
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_feature_definition import ImpliedVolMlFeatureDefinition
        return self.Provider(config=ImpliedVolMlModelConfiguration(), feature_def=ImpliedVolMlFeatureDefinition())

    def _make_artifact(self, universe_fp, feature_hash, config_hash, valid_from, valid_until):
        combined = universe_fp + feature_hash + config_hash
        meta = {
            "universe_fingerprint": universe_fp,
            "feature_definition_hash": feature_hash,
            "model_configuration_hash": config_hash,
            "valid_from": str(valid_from),
            "valid_until": str(valid_until),
        }
        artifact = SimpleNamespace(artifact_metadata=meta, location="/fake/path.pkl")
        return artifact

    def test_artifact_matches_correct_regime_and_valid_date(self):
        provider = self._provider()
        feature_hash = provider.feature_def.hash()
        config_hash = provider.config.hash()
        universe_fp = "abc123"
        regime_key = hashlib.sha256((universe_fp + feature_hash + config_hash).encode()).hexdigest()

        artifact = self._make_artifact(universe_fp, feature_hash, config_hash,
                                       date(2026, 1, 1), date(2026, 12, 31))
        self.assertTrue(provider._artifact_matches(artifact, regime_key, date(2026, 6, 1)))

    def test_artifact_does_not_match_wrong_regime(self):
        provider = self._provider()
        artifact = self._make_artifact("universe_A", provider.feature_def.hash(),
                                       provider.config.hash(),
                                       date(2026, 1, 1), date(2026, 12, 31))
        wrong_regime = hashlib.sha256(b"wrong").hexdigest()
        self.assertFalse(provider._artifact_matches(artifact, wrong_regime, date(2026, 6, 1)))

    def test_artifact_does_not_match_expired(self):
        provider = self._provider()
        feature_hash = provider.feature_def.hash()
        config_hash = provider.config.hash()
        universe_fp = "abc123"
        regime_key = hashlib.sha256((universe_fp + feature_hash + config_hash).encode()).hexdigest()

        artifact = self._make_artifact(universe_fp, feature_hash, config_hash,
                                       date(2025, 1, 1), date(2025, 6, 30))
        self.assertFalse(provider._artifact_matches(artifact, regime_key, date(2026, 6, 1)))

    def test_artifact_does_not_match_future_valid_from(self):
        provider = self._provider()
        feature_hash = provider.feature_def.hash()
        config_hash = provider.config.hash()
        universe_fp = "abc123"
        regime_key = hashlib.sha256((universe_fp + feature_hash + config_hash).encode()).hexdigest()

        artifact = self._make_artifact(universe_fp, feature_hash, config_hash,
                                       date(2027, 1, 1), date(2027, 12, 31))
        self.assertFalse(provider._artifact_matches(artifact, regime_key, date(2026, 6, 1)))


# ---------------------------------------------------------------------------
# 7. No recursive training (universe fingerprint uses analytical factor)
# ---------------------------------------------------------------------------

class TestNoRecursiveTraining(unittest.TestCase):
    """
    The universe fingerprint must query 'company_share_option_implied_vol_factor'
    (analytical), never 'company_share_option_implied_vol_ml_factor' (ML).

    We verify this by inspecting the source of _get_universe_fingerprint — the
    exact discriminator string is a literal in the code and must not be the ML one.
    """

    def test_universe_fingerprint_source_uses_analytical_discriminator(self):
        import inspect
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_provider import (
            ImpliedVolMlModelProvider,
        )
        source = inspect.getsource(ImpliedVolMlModelProvider._get_universe_fingerprint)
        self.assertIn(
            "company_share_option_implied_vol_factor",
            source,
            "Universe fingerprint must filter on the analytical IV factor discriminator",
        )
        # The ML discriminator must NOT be used as the filter criterion
        # (the ml suffix would make it company_share_option_implied_vol_ml_factor)
        self.assertNotIn(
            '"company_share_option_implied_vol_ml_factor"',
            source,
            "Universe fingerprint must not use the ML factor discriminator (would be recursive)",
        )

    def test_trainer_source_uses_analytical_discriminator(self):
        import inspect
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_trainer import (
            ImpliedVolMlModelTrainer,
        )
        source = inspect.getsource(ImpliedVolMlModelTrainer._build_training_data)
        self.assertIn(
            "company_share_option_implied_vol_factor",
            source,
            "Trainer must query the analytical IV factor for training targets",
        )
        self.assertNotIn(
            '"company_share_option_implied_vol_ml_factor"',
            source,
            "Trainer must not use ML factor as its own training target",
        )


# ---------------------------------------------------------------------------
# 8. Batch efficiency (class-level cache)
# ---------------------------------------------------------------------------

class TestBatchEfficiency(unittest.TestCase):

    def setUp(self):
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_provider import (
            ImpliedVolMlModelProvider,
        )
        self.Provider = ImpliedVolMlModelProvider
        ImpliedVolMlModelProvider.clear_cache()

    def tearDown(self):
        self.Provider.clear_cache()

    def test_model_loaded_once_for_n_entities(self):
        """
        Simulating N per-entity predict() calls: _get_or_train_model should only
        call _load_artifact once — subsequent calls hit the class-level cache.
        """
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_configuration import ImpliedVolMlModelConfiguration
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_feature_definition import ImpliedVolMlFeatureDefinition
        import numpy as np

        N = 5
        regime_key = "batch_regime_key"
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.25])

        load_call_count = [0]

        def fake_load_artifact(rk, td):
            load_call_count[0] += 1
            # Store in cache on first call (as real code does)
            self.Provider._model_cache[rk] = mock_model
            return mock_model

        provider = self.Provider(
            config=ImpliedVolMlModelConfiguration(),
            feature_def=ImpliedVolMlFeatureDefinition(),
        )

        entities = [_make_entity() for _ in range(N)]
        target_date = date(2026, 6, 1)
        deps = _make_deps()

        with patch.object(provider, "_compute_regime_key", return_value=regime_key):
            with patch.object(provider, "_load_artifact", side_effect=fake_load_artifact):
                for entity in entities:
                    deps["entity"] = entity
                    deps["target_date"] = target_date
                    provider.predict(deps, entity, target_date)

        self.assertEqual(load_call_count[0], 1,
                         f"Expected model to load once but was loaded {load_call_count[0]} times")

    def test_class_level_cache_shared_across_instances(self):
        """Two separate provider instances share the same class-level cache."""
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_configuration import ImpliedVolMlModelConfiguration
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_feature_definition import ImpliedVolMlFeatureDefinition

        p1 = self.Provider(config=ImpliedVolMlModelConfiguration(), feature_def=ImpliedVolMlFeatureDefinition())
        p2 = self.Provider(config=ImpliedVolMlModelConfiguration(), feature_def=ImpliedVolMlFeatureDefinition())

        self.assertIs(p1._model_cache, p2._model_cache)


# ---------------------------------------------------------------------------
# 9. ORM discriminator registered
# ---------------------------------------------------------------------------

class TestOrmDiscriminatorRegistered(unittest.TestCase):

    def test_ml_factor_orm_model_importable(self):
        from src.infrastructure.models.factor.factor import CompanyShareOptionImpliedVolMlFactorModel
        self.assertIsNotNone(CompanyShareOptionImpliedVolMlFactorModel)

    def test_ml_factor_orm_discriminator(self):
        from src.infrastructure.models.factor.factor import CompanyShareOptionImpliedVolMlFactorModel
        identity = CompanyShareOptionImpliedVolMlFactorModel.__mapper_args__["polymorphic_identity"]
        self.assertEqual(identity, "company_share_option_implied_vol_ml_factor")


# ---------------------------------------------------------------------------
# 10. Factor library entry registered
# ---------------------------------------------------------------------------

class TestFactorLibraryEntry(unittest.TestCase):

    def test_implied_vol_ml_in_library(self):
        from src.application.services.data.entities.factor.factor_library.finance.financial_assets.derivatives.option.company_share_option_library import (
            COMPANY_SHARE_OPTION_LIBRARY,
        )
        self.assertIn("implied_vol_ml", COMPANY_SHARE_OPTION_LIBRARY)

    def test_implied_vol_ml_library_entry_attributes(self):
        from src.application.services.data.entities.factor.factor_library.finance.financial_assets.derivatives.option.company_share_option_library import (
            COMPANY_SHARE_OPTION_LIBRARY,
        )
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_ml_factor import (
            CompanyShareOptionImpliedVolMlFactor,
        )
        entry = COMPANY_SHARE_OPTION_LIBRARY["implied_vol_ml"]
        self.assertIs(entry["class"], CompanyShareOptionImpliedVolMlFactor)
        self.assertEqual(entry["group"], "volatility")
        self.assertEqual(entry["subgroup"], "implied")
        self.assertEqual(entry["frequency"], "1d")
        self.assertEqual(entry["data_type"], "numeric")

    def test_implied_vol_library_entry_still_present(self):
        """Analytical factor entry must not have been removed."""
        from src.application.services.data.entities.factor.factor_library.finance.financial_assets.derivatives.option.company_share_option_library import (
            COMPANY_SHARE_OPTION_LIBRARY,
        )
        self.assertIn("implied_vol", COMPANY_SHARE_OPTION_LIBRARY)


if __name__ == "__main__":
    unittest.main()
