"""
ClassifierBacktestFileSource — the monthly classifier backtests (monthly_classifier_backtest) as an observation source
of the classifier evaluation: results/classifier_backtests/<stamp>/manifest.json + <model>.csv.

One model per (backtest, model): key 'monthly_backtest:<stamp>:<model>'. Its runs are the monthly retrainings
(run_id = the training month, yyyymm), each in force from its training month end until the next one. The table is
already the observation table (date T, asset, run, true class realised over the next month, predicted class, forward
return, P(class k) or the score); the forward-return horizon is fixed at one month.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.application.services.model_evaluation.observations import ObservationResult
from src.domain.entities.ml.classifier_evaluation import ClassifierModelRef, ClassifierRun
from src.domain.ports.ml.classifier_observation_source_port import ClassifierObservationSourcePort


class ClassifierBacktestFileSource(ClassifierObservationSourcePort):
    kind = "monthly_backtest"

    def __init__(self, results_dir=None):
        if results_dir is None:
            from src.application.services.model_evaluation.monthly_classifier_backtest import RESULTS_DIR
            results_dir = RESULTS_DIR
        self.results_dir = Path(results_dir)
        self._tables: Dict[str, pd.DataFrame] = {}

    def _manifests(self) -> List[dict]:
        if not self.results_dir.is_dir():
            return []
        out = []
        for path in sorted(self.results_dir.glob("*/manifest.json"), reverse=True):
            try:
                m = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            m["_dir"] = str(path.parent)
            out.append(m)
        return out

    def models(self) -> List[ClassifierModelRef]:
        out = []
        for m in self._manifests():
            window = f"{m['config'].get('start', '')[:7]} .. {m['config'].get('end', '')[:7]}"
            for name, info in (m.get("models") or {}).items():
                if info.get("status") != "completed":
                    continue
                out.append(ClassifierModelRef(
                    key=f"{self.kind}:{m['stamp']}:{name}", kind=self.kind,
                    name=(f"{info['name']} · monthly backtest {m['stamp']} "
                          f"({window}, {m.get('universe_label', 'DJIA PIT')})"),
                    classes=tuple(int(k) for k in info["classes"]), true_class_definition=info["definition"],
                    label_horizon="1 month (next month end)", output=info.get("output", "probabilities")))
        return out

    def _table(self, model: ClassifierModelRef) -> pd.DataFrame:
        if model.key not in self._tables:
            _, stamp, name = model.key.split(":")
            m = next(x for x in self._manifests() if x["stamp"] == stamp)
            frame = pd.read_csv(Path(m["_dir"]) / m["models"][name]["file"], parse_dates=["date"])
            self._tables[model.key] = frame
        return self._tables[model.key]

    def runs(self, model: ClassifierModelRef) -> List[ClassifierRun]:
        f = self._table(model)
        if f.empty:
            return []
        spans = f.groupby("run_id")["date"].agg(["min", "max"]).sort_index()
        out = []
        for run_id, row in spans.iterrows():
            y, mth = divmod(int(run_id), 100)
            out.append(ClassifierRun(run_id=int(run_id), training_id=None, label=f"retrained {y}-{mth:02d}",
                                     valid_from=row["min"].date(), valid_until=row["max"].date(),
                                     evaluable_from=row["min"].date()))
        return out

    def observations(self, model, run_id, universe_id, start, end, horizon=None) -> ObservationResult:
        f = self._table(model)
        notes = ["monthly walk-forward backtest: each month's model was fit on month-end rows dated before the "
                 "prediction date; target = the next month"]
        if horizon not in (None, 1):
            notes.append("the backtest's forward-return horizon is fixed at one month (the requested horizon is "
                         "ignored)")
        if universe_id is not None:
            stamp = model.key.split(":")[1]
            label = next((m.get("universe_label", "DJIA PIT") for m in self._manifests() if m["stamp"] == stamp),
                         "DJIA PIT")
            notes.append(f"the backtest's universe ({label} members) is used; the universe filter is ignored")
        rows = (f["date"] >= pd.Timestamp(start)) & (f["date"] <= pd.Timestamp(end) + pd.Timedelta(days=1))
        if run_id is not None:
            rows &= f["run_id"] == int(run_id)
        return ObservationResult(f[rows].reset_index(drop=True), 1, notes)
