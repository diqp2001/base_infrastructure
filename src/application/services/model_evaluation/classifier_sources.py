"""
Observation sources of the two CompanyShare classifier families (ClassifierObservationSourcePort adapters).

Both read through the repositories only (FactorResearchData panels, ML model / training / artifact repositories):
nothing is written, nothing is trained, no TradingStrategy is involved.

LGBMQuintileObservationSource — the LGBM cross-sectional quintile rank momentum model (lgbm_momentum, 5 classes)
    runs        each trained artifact (ModelArtifact 'trained_model'), in force on [valid_from, valid_until] of its
                metadata; evaluable from valid_from + 11 calendar days: its training labels (return_5d read up to 11
                calendar days after a sample date <= valid_from) can cover the forward period of earlier dates
    P(class k)  the run's pickled classifier, ``predict_proba`` (LGBMMomentumModelProvider.class_probabilities) on
                the 24 momentum features stored at T (the factor values the trainer reads; several stored factors of
                one feature are averaged, as LGBMMomentumFeatureDefinition.extract does)
    true class  the model's label: return_5d stored at the first date 5..11 calendar days after T (the trainer's
                lookup), cut into quintiles CROSS-SECTIONALLY per date with the trainer's ordinal rule (the trainer
                itself ranks over the whole training set: documented in the notes)
    forward     that same label return by default (horizon 5); another horizon: stored closes, T -> T + h bars

CSMObservationSource — the cross-sectional momentum classifier (cross_sectional_momentum, binary)
    runs        the configuration's trained artifacts; each in force from its trained_as_of until the next one
                (CSMArtifactStore.select: most recent trained_as_of <= date), evaluable from trained_as_of (its
                labels were known at trained_as_of)
    P(class 1)  the probability the trading cycle stored for (T, asset) (CSMSignalStore, the value
                CSMModelProvider also returns first); P(class 0) = 1 - P(class 1)
    true class  1 when the forward return over the label horizon is above the date's cross-sectional median of the
                universe members, else 0 (csm_features.build_dataset)
    forward     stored closes, T -> T + horizon bars (default: the label horizon)
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from src.application.services.model_evaluation.observations import (
    ObservationResult,
    cross_sectional_classes,
    median_split_classes,
    predicted_classes,
    probability_columns,
    restrict_to_runs,
    run_in_force,
)
from src.application.services.research.factor_research import FactorResearchData, membership_mask, to_bars
from src.application.services.research.statistics import forward_returns
from src.domain.entities.ml.classifier_evaluation import ClassifierModelRef, ClassifierRun
from src.domain.ports.ml.classifier_observation_source_port import ClassifierObservationSourcePort

LABEL_OFFSETS_DAYS = range(5, 12)          # the LGBM trainer's forward label lookup (5..11 calendar days)


def _meta(artifact) -> Dict:
    meta = getattr(artifact, "artifact_metadata", None) or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            return {}
    return meta if isinstance(meta, dict) else {}


def _class_name(factor) -> str:
    """The factor's domain class name: the factor repository returns domain entities or ORM rows ('...Model')."""
    return type(factor).__name__.removesuffix("Model")


def _d(value) -> Optional[date]:
    if value in (None, ""):
        return None
    return pd.Timestamp(value).date()


class _Base(ClassifierObservationSourcePort):

    def __init__(self, factory, data: Optional[FactorResearchData] = None):
        self.factory = factory
        self.data = data or FactorResearchData(factory)

    # -- shared reads --
    def _ml_models(self, prefix: str) -> List:
        return [m for m in (self.factory.ml_model_local_repo.get_all() or [])
                if getattr(m, "name", None) and m.name.startswith(prefix)]

    def _artifacts(self, ml_model_id: int) -> List[tuple]:
        """[(training, artifact)] of the model's trained artifacts, oldest artifact first."""
        out = []
        for training in self.factory.model_training_local_repo.get_by_model(ml_model_id) or []:
            for artifact in self.factory.model_artifact_local_repo.get_by_training_and_type(
                    training.id, "trained_model") or []:
                out.append((training, artifact))
        return sorted(out, key=lambda ta: ta[1].id)

    def _universe_members(self, universe_id: Optional[int], fallback_name: str) -> tuple:
        if universe_id is None:
            u = self.factory.investment_universe_local_repo.get_by_name(fallback_name)
            if u is None:
                raise ValueError(f"no universe given and no universe named '{fallback_name}'")
            universe_id = u.id
        membership = self.data.membership(int(universe_id))
        if not membership:
            raise ValueError(f"universe {universe_id} has no constituents")
        return int(universe_id), membership

    def _factor_ids_of_class(self, class_name: str) -> List[int]:
        return [int(f.id) for f in (self.factory.factor_local_repo.get_all() or []) if _class_name(f) == class_name]

    def _panel(self, factor_ids: List[int], entity_ids: List[int], start, end, frequency: str) -> pd.DataFrame:
        """Stored values of one or several factors (averaged per bar and entity), one column per entity id."""
        frames = []
        for fid in factor_ids:
            p = self.data.panel(fid, entity_ids, start, end)
            if not p.empty:
                frames.append(to_bars(p, frequency))
        if not frames:
            return pd.DataFrame()
        if len(frames) == 1:
            return frames[0]
        stacked = pd.concat([f.stack() for f in frames], axis=1)
        return stacked.mean(axis=1).unstack().sort_index()

    def _closes(self, entity_ids, start, end, frequency: str) -> pd.DataFrame:
        close_id = self.data.close_factor_id(frequency)
        if close_id is None:
            raise ValueError(f"no stored raw close factor at frequency '{frequency}'")
        return to_bars(self.data.panel(close_id, entity_ids, start, end), frequency)

    @staticmethod
    def _long(panel: pd.DataFrame, name: str) -> pd.Series:
        s = panel.stack()
        s.index = s.index.set_names(["date", "asset"])
        return s.rename(name)


# ── LGBM cross-sectional quintile rank momentum model ───────────────────────────────────────────────────────────

class LGBMQuintileObservationSource(_Base):
    kind = "lgbm_quintile"
    FREQUENCY = "1d"

    def __init__(self, factory, data: Optional[FactorResearchData] = None, model_loader=None):
        super().__init__(factory, data)
        from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_configuration import (
            LGBMMomentumModelConfiguration,
        )
        from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_feature_definition import (
            LGBMMomentumFeatureDefinition,
        )
        self.config = LGBMMomentumModelConfiguration()
        self.feature_def = LGBMMomentumFeatureDefinition()
        self.model_loader = model_loader or self._load_model

    @staticmethod
    def _load_model(artifact):
        from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_model_provider import (
            LGBMMomentumModelProvider,
        )
        meta = _meta(artifact)
        return LGBMMomentumModelProvider._deserialize(artifact.location, meta.get("sha256"))

    def models(self) -> List[ClassifierModelRef]:
        n = int(self.config.n_quintiles)
        return [ClassifierModelRef(
            key=f"{self.kind}:{m.id}", kind=self.kind, name=m.name, classes=tuple(range(1, n + 1)),
            true_class_definition=(f"cross-sectional quintile (1 = worst .. {n} = best) per date of the forward "
                                   f"return_5d (stored at the first date 5..11 calendar days after T)"),
            label_horizon=f"{self.config.forward_return_days} trading days")
            for m in self._ml_models(self.config.ML_MODEL_NAME_PREFIX)]

    def runs(self, model: ClassifierModelRef) -> List[ClassifierRun]:
        out = []
        for training, artifact in self._artifacts(int(model.key.split(":")[1])):
            meta = _meta(artifact)
            start, until = _d(meta.get("valid_from")), _d(meta.get("valid_until"))
            out.append(ClassifierRun(
                run_id=int(artifact.id), training_id=getattr(training, "id", None),
                label=f"#{artifact.id} in force {start} .. {until}", valid_from=start, valid_until=until,
                evaluable_from=(start + timedelta(days=max(LABEL_OFFSETS_DAYS)) if start else None),
                notes=("training labels read up to 11 calendar days after valid_from: evaluated from "
                       "valid_from + 11 days",)))
        return out

    def observations(self, model, run_id, universe_id, start, end, horizon=None) -> ObservationResult:
        runs = [r for r in self.runs(model) if run_id is None or r.run_id == run_id]
        artifacts = {int(a.id): a for _, a in self._artifacts(int(model.key.split(":")[1]))}
        classes = list(model.classes)
        _, membership = self._universe_members(universe_id, self.config.UNIVERSE_NAME)
        ids = sorted({m[0] for m in membership})
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        notes = ["true class: the model's label (return_5d 5..11 calendar days after T) ranked into quintiles per date "
                 "(the trainer ranks over its whole training set instead — a global rank)"]

        # features known at T
        features = {}
        for cls_name, fname in self.feature_def.FEATURE_MAP:
            p = self._panel(self._factor_ids_of_class(cls_name), ids, start_ts, end_ts, self.FREQUENCY)
            if p.empty:
                return ObservationResult(pd.DataFrame(columns=_columns(classes)), 5,
                                         notes + [f"no stored values of feature '{fname}' ({cls_name}) in the window"])
            features[fname] = self._long(p, fname)
        frame = pd.concat(features.values(), axis=1).dropna().reset_index()
        mask = membership_mask(pd.DatetimeIndex(sorted(frame["date"].unique())), ids, membership)
        frame = frame[[bool(mask.at[d, a]) for d, a in zip(frame["date"], frame["asset"])]]

        # the run in force at each date, and its probabilities from the features at T
        frame["run_id"] = run_in_force(frame["date"], runs)
        frame = frame.dropna(subset=["run_id"])
        frame["run_id"] = frame["run_id"].astype(int)
        frame = restrict_to_runs(frame, runs).reset_index(drop=True)
        probs = np.full((len(frame), len(classes)), np.nan)
        for rid, rows in frame.groupby("run_id").groups.items():
            artifact = artifacts.get(int(rid))
            model_obj = self.model_loader(artifact) if artifact is not None else None
            if model_obj is None:
                notes.append(f"run {rid}: model file missing or not verified — its dates are left out")
                continue
            from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_model_provider import (
                class_probabilities,
            )
            X = frame.loc[rows, self.feature_def.FEATURE_NAMES].to_numpy(dtype=float)
            labels, p = class_probabilities(model_obj, X)
            for j, k in enumerate(classes):
                probs[frame.index.get_indexer(rows), j] = p[:, labels.index(k)] if k in labels else 0.0
        for j, col in enumerate(probability_columns(classes)):
            frame[col] = probs[:, j]
        frame = frame.dropna(subset=probability_columns(classes))
        frame["predicted_class"] = predicted_classes(frame[probability_columns(classes)].to_numpy(), classes)

        # the label after T: return_5d at the first date 5..11 calendar days later
        ret_ids = self._factor_ids_of_class("CompanyShareReturn5DFactor")
        label_panel = self._panel(ret_ids, ids, start_ts, end_ts + pd.Timedelta(days=max(LABEL_OFFSETS_DAYS)),
                                  self.FREQUENCY)
        frame["label_return"] = _first_after(frame, label_panel, LABEL_OFFSETS_DAYS)
        frame["true_class"] = cross_sectional_classes(frame, "label_return", len(classes))
        if horizon is None or int(horizon) == int(self.config.forward_return_days):
            frame["forward_return"] = frame["label_return"]
            used = int(self.config.forward_return_days)
        else:
            used = int(horizon)
            closes = self._closes(ids, start_ts, end_ts + pd.Timedelta(days=3 * used + 10), self.FREQUENCY)
            frame["forward_return"] = _lookup(frame, forward_returns(closes, used))
            notes.append(f"forward returns of the quintiles: stored closes over {used} bars (the true class keeps "
                         f"the model's 5-day label)")
        frame["symbol"] = frame["asset"].map(self.data.symbols(sorted(frame["asset"].unique().tolist())))
        return ObservationResult(frame[_columns(classes)], used, notes)


# ── cross-sectional momentum classifier ─────────────────────────────────────────────────────────────────────────

class CSMObservationSource(_Base):
    kind = "csm"

    def __init__(self, factory, data: Optional[FactorResearchData] = None):
        super().__init__(factory, data)
        from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
            CSMConfiguration,
        )
        self._config_cls = CSMConfiguration

    def _configurations(self, ml_model) -> Dict[str, tuple]:
        """{model hash: (CSMConfiguration, [(trained_as_of, artifact id, training)])} — one MLModel row per universe is
        shared by every configuration trained on it; each artifact records its own configuration and hash."""
        fallback = getattr(ml_model, "configuration", None) or {}
        if isinstance(fallback, str):
            fallback = json.loads(fallback) if fallback else {}
        out: Dict[str, tuple] = {}
        for training, artifact in self._artifacts(int(ml_model.id)):
            if getattr(training, "status", None) != "completed":
                continue
            meta = _meta(artifact)
            h = meta.get("model_hash")
            if not h or not meta.get("trained_as_of"):
                continue
            if h not in out:
                cfg_dict = meta.get("configuration") or fallback
                cfg = self._config_cls.from_dict(cfg_dict) if cfg_dict else self._config_cls()
                out[h] = (cfg, [])
            out[h][1].append((pd.Timestamp(meta["trained_as_of"]), int(artifact.id), training))
        for _, found in out.values():
            found.sort(key=lambda x: (x[0], x[1]))
        return out

    def _resolve(self, model: ClassifierModelRef):
        """(ml model, configuration, [(trained_as_of, artifact id, training)]) of a model key 'csm:<id>:<hash>'."""
        _, mid, h = model.key.split(":")
        ml_model = next(m for m in self._ml_models(self._config_cls().ml_model_name_prefix) if int(m.id) == int(mid))
        for full, (cfg, found) in self._configurations(ml_model).items():
            if full.startswith(h):
                return ml_model, cfg, found
        raise KeyError(f"no configuration {h} of {ml_model.name}")

    def models(self) -> List[ClassifierModelRef]:
        out = []
        for m in self._ml_models(self._config_cls().ml_model_name_prefix):
            for h, (cfg, found) in self._configurations(m).items():
                unit = "sessions" if not cfg.bar_minutes else f"{cfg.bar_minutes}-minute bars"
                out.append(ClassifierModelRef(
                    key=f"{self.kind}:{m.id}:{h[:12]}", kind=self.kind,
                    name=f"{m.name} · configuration {h[:8]} ({len(found)} runs, from {found[0][0].date()})",
                    classes=(0, 1),
                    true_class_definition=(f"1 when the forward return over {cfg.label.horizon} {unit} is above the "
                                           f"date's cross-sectional median, else 0"),
                    label_horizon=f"{cfg.label.horizon} {unit}"))
        return out

    def runs(self, model: ClassifierModelRef) -> List[ClassifierRun]:
        _, _, found = self._resolve(model)
        out = []
        for i, (as_of, aid, training) in enumerate(found):
            nxt = found[i + 1][0] if i + 1 < len(found) else None
            until = (nxt - pd.Timedelta(days=1)).date() if nxt is not None else None
            out.append(ClassifierRun(run_id=aid, training_id=getattr(training, "id", None),
                                     label=f"#{aid} trained as of {as_of.date()}", valid_from=as_of.date(),
                                     valid_until=until, evaluable_from=as_of.date()))
        return out

    def _shared_signal_dates(self, ml_model, cfg, dates) -> List[str]:
        """Dates also covered by a run of ANOTHER configuration writing the same signal factor: there the stored
        probability may be that configuration's (the store keeps the first value written)."""
        evaluated = set(pd.to_datetime(pd.Series(dates)).dt.normalize())
        out = []
        for h, (other, found) in self._configurations(ml_model).items():
            if h == cfg.model_hash() or other.signal_factor_name != cfg.signal_factor_name \
                    or other.bar_minutes != cfg.bar_minutes or not found:
                continue
            start = found[0][0].normalize()            # its last run stays in force: open-ended from its first run
            shared = sorted(d for d in evaluated if d >= start)
            if shared:
                out.append(f"WARNING: {len(shared)} evaluated dates ({shared[0].date()} .. {shared[-1].date()}) are also "
                           f"in force under configuration {h[:8]} (runs from {start.date()}), which writes the same "
                           f"signal factor: their stored probabilities may be that configuration's")
        return out

    def _signal_factor_id(self, cfg) -> Optional[int]:
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import frequency
        for f in self.factory.factor_local_repo.get_all() or []:
            if _class_name(f) == "CompanyShareCrossSectionalMomentumFactor" and f.name == cfg.signal_factor_name \
                    and getattr(f, "frequency", None) == frequency(cfg.bar_minutes):
                return int(f.id)
        return None

    def observations(self, model, run_id, universe_id, start, end, horizon=None) -> ObservationResult:
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import frequency
        ml_model, cfg, _ = self._resolve(model)
        freq = frequency(cfg.bar_minutes)
        classes = list(model.classes)
        runs = [r for r in self.runs(model) if run_id is None or r.run_id == run_id]
        _, membership = self._universe_members(universe_id, cfg.universe.name)
        ids = sorted({m[0] for m in membership})
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        notes = ["P(class 1): the probability the trading cycle stored for the date (CSMSignalStore keeps the first "
                 "value written: runs of another configuration sharing the signal factor would be read too)"]
        signal_id = self._signal_factor_id(cfg)
        if signal_id is None:
            return ObservationResult(pd.DataFrame(columns=_columns(classes)), int(horizon or cfg.label.horizon),
                                     notes + ["no stored signal factor for this configuration"])
        signals = self._panel([signal_id], ids, start_ts, end_ts, freq)
        if signals.empty:
            return ObservationResult(pd.DataFrame(columns=_columns(classes)), int(horizon or cfg.label.horizon),
                                     notes + ["no stored probability in the window"])
        frame = self._long(signals, "p_1").reset_index()
        mask = membership_mask(pd.DatetimeIndex(sorted(frame["date"].unique())), ids, membership)
        frame = frame[[bool(mask.at[d, a]) for d, a in zip(frame["date"], frame["asset"])]]
        frame["p_0"] = 1.0 - frame["p_1"]
        frame["run_id"] = run_in_force(frame["date"], runs)
        frame = frame.dropna(subset=["run_id"])
        frame["run_id"] = frame["run_id"].astype(int)
        frame = restrict_to_runs(frame, runs).reset_index(drop=True)
        frame["predicted_class"] = predicted_classes(frame[probability_columns(classes)].to_numpy(), classes)
        notes.extend(self._shared_signal_dates(ml_model, cfg, frame["date"]))

        h_label = int(cfg.label.horizon)
        used = int(horizon or h_label)
        pad = pd.Timedelta(days=3 * max(used, h_label) + 10) if not cfg.bar_minutes else pd.Timedelta(days=5)
        closes = self._closes(ids, start_ts, end_ts + pad, freq)
        fwd_label = forward_returns(closes, h_label)
        label_ret = _lookup(frame, fwd_label)
        # the median over the universe members with a forward return at T (not only those with a probability)
        members_fwd = self._long(fwd_label.where(membership_mask(fwd_label.index, fwd_label.columns, membership)),
                                 "fwd").reset_index()
        members_fwd["cls"] = median_split_classes(members_fwd, "fwd")
        frame["true_class"] = _lookup(frame, members_fwd.set_index(["date", "asset"])["cls"].unstack())
        frame.loc[label_ret.isna().to_numpy(), "true_class"] = np.nan
        frame["forward_return"] = label_ret if used == h_label else _lookup(frame, forward_returns(closes, used))
        frame["symbol"] = frame["asset"].map(self.data.symbols(sorted(frame["asset"].unique().tolist())))
        return ObservationResult(frame[_columns(classes)], used, notes)


# ── helpers ─────────────────────────────────────────────────────────────────────────────────────────────────────

def _columns(classes) -> List[str]:
    return ["date", "asset", "symbol", "run_id", "true_class", "predicted_class", "forward_return"] + \
        probability_columns(classes)


def _lookup(frame: pd.DataFrame, panel: pd.DataFrame) -> pd.Series:
    """panel[date, asset] for each row (NaN when absent)."""
    if panel is None or panel.empty:
        return pd.Series(np.nan, index=frame.index)
    s = panel.stack()
    keyed = dict(zip(zip(s.index.get_level_values(0), s.index.get_level_values(1)), s.to_numpy()))
    return pd.Series([keyed.get((d, a), np.nan) for d, a in zip(frame["date"], frame["asset"])], index=frame.index,
                     dtype=float)


def _first_after(frame: pd.DataFrame, panel: pd.DataFrame, offsets_days) -> pd.Series:
    """For each (T, asset): the panel value at the first date T + d (d in ``offsets_days``, calendar days) that has
    one — the LGBM trainer's forward label lookup."""
    out = pd.Series(np.nan, index=frame.index)
    if panel is None or panel.empty:
        return out
    s = panel.stack()
    keyed = dict(zip(zip(s.index.get_level_values(0).normalize(), s.index.get_level_values(1)), s.to_numpy()))
    values = []
    for d, a in zip(pd.DatetimeIndex(pd.to_datetime(frame["date"])).normalize(), frame["asset"]):
        v = np.nan
        for off in offsets_days:
            got = keyed.get((d + pd.Timedelta(days=off), a))
            if got is not None and np.isfinite(got):
                v = got
                break
        values.append(v)
    return pd.Series(values, index=frame.index, dtype=float)
