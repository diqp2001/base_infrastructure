"""
ModelRegistryService - the generic model registry on top of the EXISTING ML registry (2026-11-18).

A model is a reusable research artifact: ``ml_models`` (MLModel) with its features (``model_features`` and/or the
feature names in its configuration), its trainings (``model_trainings``: one per fit, the versions), their metrics
(``training_metrics``) and artifacts (``model_artifacts``: metadata + location; the trained binary stays outside SQL).
Nothing here adds a universe to a model: the universe belongs to each run that used it (backtest_run_models).

    register_model(name, algorithm, configuration={features, hyperparameters, training_frequency, ...})
    describe(model_id)  -> model, version, status, algorithm, features, training configuration / metrics,
                           artifacts, runs using it (with each run's universe)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.domain.entities.ml.ml_model import MLModel

CONFIG_KEYS = ("features", "hyperparameters", "training_frequency", "prediction_frequency", "version",
               "algorithm", "code_commit")


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


class ModelRegistryService:

    def __init__(self, factory):
        self.factory = factory
        self.models = factory.ml_model_local_repo
        self.features = factory.model_feature_local_repo
        self.trainings = factory.model_training_local_repo
        self.training_metrics = factory.training_metric_local_repo
        self.artifacts = factory.model_artifact_local_repo
        self.run_links = factory.backtest_run_model_link_local_repo
        self.runs = factory.backtest_run_local_repo

    # -- writes -------------------------------------------------------------------------------------------------
    def register_model(self, name: str, algorithm: str, description: Optional[str] = None,
                       configuration: Optional[Dict[str, Any]] = None) -> MLModel:
        """Create the model, or update its configuration when the name exists (same research artifact)."""
        configuration = dict(configuration or {})
        configuration.setdefault("algorithm", algorithm)
        existing = self.models.get_by_name(name)
        if existing is not None:
            if existing.configuration != configuration or (description and existing.description != description):
                existing.configuration = configuration
                existing.description = description or existing.description
                existing = self.models.update(existing) or existing
            return existing
        return self.models.add(MLModel(name=name, model_type=algorithm, description=description,
                                       configuration=configuration))

    # -- reads --------------------------------------------------------------------------------------------------
    def list_models(self) -> List[Dict[str, Any]]:
        out = []
        for m in sorted(self.models.get_all(), key=lambda m: m.id):
            trainings = self.trainings.get_by_model(m.id)
            out.append({**self._header(m, trainings), "runs": len(self.run_links.get_by_model(m.id))})
        return out

    def _header(self, m: MLModel, trainings) -> Dict[str, Any]:
        cfg = m.configuration if isinstance(m.configuration, dict) else {}
        latest = max(trainings, key=lambda t: t.id) if trainings else None
        return {"id": m.id, "name": m.name, "description": m.description,
                "algorithm": cfg.get("algorithm") or m.model_type, "model_type": m.model_type,
                "version": cfg.get("version") or (f"{len(trainings)} trainings" if trainings else "untrained"),
                "trainings": len(trainings), "status": latest.status if latest else "registered",
                "created_at": _iso(m.created_at), "updated_at": _iso(m.updated_at)}

    def describe(self, model_id: int) -> Optional[Dict[str, Any]]:
        m = self.models.get_by_id(model_id)
        if m is None:
            return None
        trainings = sorted(self.trainings.get_by_model(m.id), key=lambda t: t.id)
        cfg = m.configuration if isinstance(m.configuration, dict) else {}
        features = [{"name": f.name, "factor_id": f.factor_id, "lag": f.lag, "enabled": f.enabled}
                    for f in self.features.get_by_model(m.id)]
        if not features:
            features = [{"name": str(n)} for n in cfg.get("features", []) or []]
        latest = trainings[-1] if trainings else None
        metrics = []
        if latest is not None:
            metrics = [{"name": t.metric_name, "value": float(t.metric_value) if t.metric_value is not None else None,
                        "dataset": t.dataset_type} for t in self.training_metrics.get_by_training(latest.id)]
        return {
            **self._header(m, trainings),
            "configuration": cfg,
            "hyperparameters": cfg.get("hyperparameters", {}),
            "training_frequency": cfg.get("training_frequency"),
            "prediction_frequency": cfg.get("prediction_frequency"),
            "features": features,
            "latest_training": None if latest is None else {
                "id": latest.id, "status": latest.status, "training": [_iso(latest.training_start_date),
                                                                      _iso(latest.training_end_date)],
                "validation": [_iso(latest.validation_start_date), _iso(latest.validation_end_date)],
                "configuration": getattr(latest, "training_configuration", None) or {}},
            "training_metrics": metrics,
            "trainings_list": [{"id": t.id, "status": t.status, "training_end": _iso(t.training_end_date),
                                "completed_at": _iso(t.completed_at)} for t in trainings[-50:]],
            "runs": self.runs_of_model(m.id),
        }

    def artifacts_of_model(self, model_id: int) -> List[Dict[str, Any]]:
        out = []
        for t in self.trainings.get_by_model(model_id):
            for a in self.artifacts.get_by_training(t.id):
                out.append({"id": a.id, "training_id": t.id, "type": a.artifact_type, "name": a.name,
                            "location": a.location, "format": a.format, "created_at": _iso(a.created_at)})
        return sorted(out, key=lambda a: a["id"], reverse=True)

    def runs_of_model(self, model_id: int) -> List[Dict[str, Any]]:
        out = []
        for link in self.run_links.get_by_model(model_id):
            run = self.runs.get_by_id(link.run_id)
            if run is None:
                continue
            out.append({"run_id": run.id, "role": link.role, "project": run.project_name, "status": run.status,
                        "progress": run.progress_label(), "universe": run.universe_description,
                        "period": [_iso(run.requested_start), _iso(run.requested_end)],
                        "price_source": run.price_source})
        return out
