"""BI-016: implied-vol ML model lifecycle — reuse of a valid artifact, training when missing / invalid / corrupt,
training failure surfaced as an error and no value. Fake repositories, temporary artifact files; no DB."""

import hashlib
import logging
import pickle
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_provider import (
    ImpliedVolMlModelProvider,
)
from src.domain.entities.ml.ml_model import MLModel
from src.domain.entities.ml.model_artifact import ModelArtifact
from src.domain.entities.ml.model_training import ModelTraining

D = date(2026, 8, 24)
TRAINER = ("src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_trainer."
           "ImpliedVolMlModelTrainer.train_and_persist")


class Model:
    def __init__(self, iv):
        self.iv = iv

    def predict(self, X):
        return [self.iv]


def new(cls, **fields):
    """Domain entity without running its constructor (the provider only reads these attributes)."""
    obj = cls.__new__(cls)
    obj.__dict__.update(fields)
    return obj


@pytest.fixture(autouse=True)
def empty_cache():
    ImpliedVolMlModelProvider.clear_cache()
    yield
    ImpliedVolMlModelProvider.clear_cache()


def provider_with(tmp_path, payload=None, valid=(date(2026, 8, 1), date(2026, 9, 30)), regime=True):
    provider = ImpliedVolMlModelProvider(factory=None)
    fingerprint = "u-fp"
    meta = {"universe_fingerprint": fingerprint if regime else "other-universe",
            "feature_definition_hash": provider.feature_def.hash(),
            "model_configuration_hash": provider.config.hash(),
            "valid_from": valid[0].isoformat(), "valid_until": valid[1].isoformat()}
    location = tmp_path / "model.pkl"
    if payload is not None:
        location.write_bytes(payload)
    artifact = new(ModelArtifact, id=3, location=str(location), artifact_metadata=meta)
    factory = SimpleNamespace(
        ml_model_local_repo=SimpleNamespace(get_all=lambda: [new(MLModel, id=1,
                                                                 name=provider.config.ML_MODEL_NAME_PREFIX + "x")]),
        model_training_local_repo=SimpleNamespace(get_by_model=lambda mid: [new(ModelTraining, id=2)]),
        model_artifact_local_repo=SimpleNamespace(get_by_training_and_type=lambda tid, kind: [artifact]),
    )
    provider.factory = factory
    provider._get_universe_fingerprint = lambda target_date: fingerprint
    return provider


def regime_key(provider):
    return hashlib.sha256(("u-fp" + provider.feature_def.hash() + provider.config.hash()).encode()).hexdigest()


def test_a_valid_matching_artifact_is_reused_without_training(tmp_path):
    provider = provider_with(tmp_path, payload=pickle.dumps(Model(0.25)))
    with patch(TRAINER) as train:
        model = provider._get_or_train_model(D)
    assert model.iv == 0.25 and not train.called


@pytest.mark.parametrize("case", ["corrupt", "missing_file", "other_regime", "expired"])
def test_an_unusable_artifact_leads_to_training(tmp_path, case, caplog):
    kwargs = {"corrupt": dict(payload=b"not a pickle"), "missing_file": dict(payload=None),
              "other_regime": dict(payload=pickle.dumps(Model(0.25)), regime=False),
              "expired": dict(payload=pickle.dumps(Model(0.25)), valid=(date(2026, 1, 1), date(2026, 3, 31)))}[case]
    provider = provider_with(tmp_path, **kwargs)
    with patch(TRAINER, return_value=Model(0.31)) as train, caplog.at_level(logging.ERROR):
        model = provider._get_or_train_model(D)
    assert train.called and model.iv == 0.31
    assert ImpliedVolMlModelProvider._model_cache[regime_key(provider)] is model
    if case == "corrupt":
        assert "unreadable" in caplog.text


@pytest.mark.parametrize("failure", [None, RuntimeError("not enough history")])
def test_a_training_failure_gives_no_value_and_is_logged(tmp_path, failure, caplog):
    provider = provider_with(tmp_path, payload=None)
    side = {"side_effect": failure} if isinstance(failure, Exception) else {"return_value": None}
    with patch(TRAINER, **side), caplog.at_level(logging.ERROR):
        assert provider._get_or_train_model(D) is None
    assert "training" in caplog.text and regime_key(provider) not in ImpliedVolMlModelProvider._model_cache


def test_an_artifact_that_does_not_match_its_recorded_checksum_is_not_unpickled(tmp_path, caplog):
    """BI-015: the provider passes the recorded SHA-256; a replaced file is refused and the model retrained."""
    provider = provider_with(tmp_path, payload=pickle.dumps(Model(0.25)))
    artifact = provider.factory.model_artifact_local_repo.get_by_training_and_type(2, "trained_model")[0]
    artifact.artifact_metadata["sha256"] = "0" * 64
    with patch(TRAINER, return_value=Model(0.31)) as train, caplog.at_level(logging.ERROR):
        model = provider._get_or_train_model(D)
    assert train.called and model.iv == 0.31 and "differs from the recorded" in caplog.text
