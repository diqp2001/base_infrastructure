"""
Strategy — what a trading / research strategy IS: one version of its persistent definition.

Replaces StrategyConfiguration (owner's choice 2026-11-19): the same versions and lifecycle, plus a first-class
universe reference and the typed definition shared by every project.

Identity: ``name`` + ``version`` (a database id per version).

Definition
* ``strategy_type``  which project implementation runs it (the ProjectRegistry key, e.g. 'stm_monthly_deciles');
* ``universe_id``    the Universe it trades / researches - never a ticker list held by the strategy itself;
* typed definition   ``bar_frequency`` ('1d', '10m', ...), ``bar_size`` (IBKR bar size, '10 mins'), ``model_type``,
                     ``training_window`` (rows), ``retrain_every_days``, ``prediction_horizon`` (rows);
* ``sections``       the project's own parameters, validated by its ConfigurationSchema (universe, factors, model,
                     training, portfolio, trading, risk, evaluation, data_policy), seen through ``parameters``,
                     ``features``, ``portfolio_construction`` and ``risk``.
Not part of a strategy: where / how it is deployed (broker, account, host, client id, paper / live price settings):
that is a later StrategyDeployment.

Lifecycle:  draft --validate--> validated --lock (an experiment starts)--> locked;  any --archive--> archived.
* A draft can be edited (editing a validated strategy sends it back to draft).
* A locked strategy is immutable: ``revise`` returns a NEW draft version whose ``parent_id`` is this one, so every
  experiment keeps pointing at exactly what it ran.
* ``content_hash`` identifies the definition (type, universe, typed definition, sections), not the name / version /
  status: two strategies with the same hash run the same experiment.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

from src.domain.entities.entity import Entity
from src.domain.entities.strategy.configuration_schema import SECTIONS

DRAFT, VALIDATED, LOCKED, ARCHIVED = "draft", "validated", "locked", "archived"
STATUSES = (DRAFT, VALIDATED, LOCKED, ARCHIVED)

# typed definition fields (columns), in addition to strategy_type / universe_id
DEFINITION_FIELDS = ("bar_frequency", "bar_size", "model_type", "training_window", "retrain_every_days",
                     "prediction_horizon")
_INT_FIELDS = ("training_window", "retrain_every_days", "prediction_horizon")
# how the project sections group into the strategy's parameter families
PARAMETER_SECTIONS = ("model", "training", "trading", "evaluation", "data_policy", "strategy")


class StrategyLocked(Exception):
    """The strategy is used by an experiment: create a new version instead."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(strategy_type: str, sections: Dict[str, Dict[str, Any]],
                 definition: Optional[Dict[str, Any]] = None) -> str:
    """Hash of the definition. Without typed fields / universe it equals the former configuration hash, so the
    experiments recorded before the replacement still match their (migrated) strategy."""
    payload: Dict[str, Any] = {"project_key": strategy_type, "sections": sections}
    extra = {k: v for k, v in (definition or {}).items() if v is not None}
    if extra:
        payload["definition"] = extra
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


class Strategy(Entity):

    def __init__(self, name: str, strategy_type: str, sections: Optional[Dict[str, Dict[str, Any]]] = None,
                 id: Optional[int] = None, description: str = "", version: int = 1, parent_id: Optional[int] = None,
                 status: str = DRAFT, universe_id: Optional[int] = None, bar_frequency: Optional[str] = None,
                 bar_size: Optional[str] = None, model_type: Optional[str] = None,
                 training_window: Optional[int] = None, retrain_every_days: Optional[int] = None,
                 prediction_horizon: Optional[int] = None, created_at: Optional[datetime] = None,
                 validated_at: Optional[datetime] = None, locked_at: Optional[datetime] = None):
        super().__init__(id)
        if not (name or "").strip():
            raise ValueError("a strategy needs a name")
        if not (strategy_type or "").strip():
            raise ValueError("a strategy needs a strategy_type (the project that implements it)")
        if status not in STATUSES:
            raise ValueError(f"unknown status '{status}'")
        if int(version) < 1:
            raise ValueError("a strategy version starts at 1")
        unknown = [s for s in (sections or {}) if s not in SECTIONS]
        if unknown:
            raise ValueError(f"unknown configuration sections {unknown}")
        self.name = name.strip()
        self.description = description
        self.strategy_type = strategy_type.strip()
        self.version = int(version)
        self.parent_id = parent_id
        self.status = status
        self.universe_id = universe_id
        self._sections: Dict[str, Dict[str, Any]] = copy.deepcopy(sections or {})
        self.bar_frequency = self.bar_size = self.model_type = None
        self.training_window = self.retrain_every_days = self.prediction_horizon = None
        self._set_definition(dict(bar_frequency=bar_frequency, bar_size=bar_size, model_type=model_type,
                                  training_window=training_window, retrain_every_days=retrain_every_days,
                                  prediction_horizon=prediction_horizon))
        self.created_at = created_at
        self.validated_at = validated_at
        self.locked_at = locked_at

    # -- definition -----------------------------------------------------------------------------------------------
    @property
    def project_key(self) -> str:
        """The former StrategyConfiguration name of ``strategy_type`` (ProjectRegistry key)."""
        return self.strategy_type

    @property
    def sections(self) -> Dict[str, Dict[str, Any]]:
        """A copy: the content can only change through ``update`` (which enforces the lifecycle)."""
        return copy.deepcopy(self._sections)

    def section(self, name: str) -> Dict[str, Any]:
        return copy.deepcopy(self._sections.get(name, {}))

    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        """Strategy / model parameters: the model, training, trading, evaluation and data-policy sections."""
        return {s: self.section(s) for s in PARAMETER_SECTIONS if s in self._sections}

    @property
    def features(self) -> Dict[str, Any]:
        """Feature / factor configuration."""
        return self.section("factors")

    @property
    def portfolio_construction(self) -> Dict[str, Any]:
        return self.section("portfolio")

    @property
    def risk(self) -> Dict[str, Any]:
        return self.section("risk")

    @property
    def definition(self) -> Dict[str, Any]:
        """The typed definition, with the universe reference."""
        return {"universe_id": self.universe_id, **{f: getattr(self, f) for f in DEFINITION_FIELDS}}

    @property
    def content_hash(self) -> str:
        return content_hash(self.strategy_type, self._sections, self.definition)

    @property
    def is_editable(self) -> bool:
        return self.status in (DRAFT, VALIDATED)

    def _set_definition(self, values: Dict[str, Any]) -> None:
        for key, value in values.items():
            if key not in DEFINITION_FIELDS:
                raise ValueError(f"unknown strategy definition field '{key}'")
            if value is not None and key in _INT_FIELDS:
                if isinstance(value, bool) or int(value) != value or int(value) < 0:
                    raise ValueError(f"{key} must be a non-negative integer, got {value!r}")
                value = int(value)
            setattr(self, key, value)

    def _require_editable(self) -> None:
        if not self.is_editable:
            raise StrategyLocked(f"strategy '{self.name}' v{self.version} is {self.status}: create a new version")

    # -- changes --------------------------------------------------------------------------------------------------
    def update(self, sections: Optional[Dict[str, Dict[str, Any]]] = None, description: Optional[str] = None,
               **definition) -> "Strategy":
        """Replace the given sections / typed definition fields (a draft / validated strategy only); it goes back to
        draft."""
        self._require_editable()
        for name, values in (sections or {}).items():
            if name not in SECTIONS:
                raise ValueError(f"unknown configuration section '{name}'")
            self._sections[name] = copy.deepcopy(values)
        if "universe_id" in definition:
            self.universe_id = definition.pop("universe_id")
        self._set_definition(definition)
        if description is not None:
            self.description = description
        self.status = DRAFT
        self.validated_at = None
        return self

    def assign_universe(self, universe_id: Optional[int]) -> "Strategy":
        """Reference the Universe the strategy uses (a draft / validated strategy only)."""
        return self.update(universe_id=universe_id)

    def mark_validated(self, normalised_sections: Dict[str, Dict[str, Any]], at: datetime,
                       definition: Optional[Dict[str, Any]] = None) -> None:
        """Validation passed: store the normalised sections (defaults filled in) and the typed definition derived
        from them (fields the project does not define keep their value)."""
        self._require_editable()
        self._sections = copy.deepcopy(normalised_sections)
        self._set_definition({k: v for k, v in (definition or {}).items() if v is not None})
        self.status = VALIDATED
        self.validated_at = at

    def lock(self, at: datetime) -> None:
        """An experiment starts on it: from now on it never changes."""
        if self.status == LOCKED:
            return
        if self.status != VALIDATED:
            raise ValueError(f"only a validated strategy can be used by an experiment (status: {self.status})")
        self.status = LOCKED
        self.locked_at = at

    def archive(self) -> None:
        self.status = ARCHIVED

    def revise(self, new_version: int, name: Optional[str] = None) -> "Strategy":
        """A new draft with the same definition: the next version of this strategy (or a clone under ``name``,
        starting at version 1)."""
        return Strategy(
            name=name or self.name, strategy_type=self.strategy_type, sections=self._sections,
            description=self.description, version=1 if name and name != self.name else new_version,
            parent_id=self.id, status=DRAFT, universe_id=self.universe_id,
            **{f: getattr(self, f) for f in DEFINITION_FIELDS},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description, "strategy_type": self.strategy_type,
            "project_key": self.strategy_type, "version": self.version, "parent_id": self.parent_id,
            "status": self.status, "content_hash": self.content_hash, **self.definition, "sections": self.sections,
            "created_at": self.created_at, "validated_at": self.validated_at, "locked_at": self.locked_at,
        }

    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name={self.name!r}, v{self.version}, {self.strategy_type}, {self.status})>"
