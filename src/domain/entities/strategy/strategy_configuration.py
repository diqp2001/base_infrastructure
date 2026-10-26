"""
StrategyConfiguration — one version of a configured investment strategy experiment.

Identity: ``name`` + ``version``. Content: ``project_key`` (which project implementation runs it) and the
configuration ``sections`` (universe, factors, model, training, portfolio, trading, risk, evaluation, data_policy),
each a plain dict validated by the project's ConfigurationSchema.

Lifecycle:  draft --validate--> validated --lock (an experiment starts)--> locked;  any --archive--> archived.
* A draft can be edited (editing a validated configuration sends it back to draft).
* A locked configuration is immutable: ``revise`` returns a NEW draft version whose ``parent_id`` is this one,
  so every completed experiment keeps pointing at exactly what it ran.
* ``content_hash`` identifies the content (project + sections), not the name / version / status: two
  configurations with the same hash run the same experiment.
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


class ConfigurationLocked(Exception):
    """The configuration is used by an experiment: create a new version instead."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(project_key: str, sections: Dict[str, Dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_json({"project_key": project_key, "sections": sections}).encode()).hexdigest()


class StrategyConfiguration(Entity):

    def __init__(self, name: str, project_key: str, sections: Optional[Dict[str, Dict[str, Any]]] = None,
                 id: Optional[int] = None, description: str = "", version: int = 1, parent_id: Optional[int] = None,
                 status: str = DRAFT, created_at: Optional[datetime] = None, validated_at: Optional[datetime] = None,
                 locked_at: Optional[datetime] = None):
        super().__init__(id)
        if status not in STATUSES:
            raise ValueError(f"unknown status '{status}'")
        unknown = [s for s in (sections or {}) if s not in SECTIONS]
        if unknown:
            raise ValueError(f"unknown configuration sections {unknown}")
        self.name = name
        self.description = description
        self.project_key = project_key
        self.version = int(version)
        self.parent_id = parent_id
        self.status = status
        self._sections: Dict[str, Dict[str, Any]] = copy.deepcopy(sections or {})
        self.created_at = created_at
        self.validated_at = validated_at
        self.locked_at = locked_at

    # ------------------------------------------------------------------
    @property
    def sections(self) -> Dict[str, Dict[str, Any]]:
        """A copy: the content can only change through ``update`` (which enforces the lifecycle)."""
        return copy.deepcopy(self._sections)

    def section(self, name: str) -> Dict[str, Any]:
        return copy.deepcopy(self._sections.get(name, {}))

    @property
    def content_hash(self) -> str:
        return content_hash(self.project_key, self._sections)

    @property
    def is_editable(self) -> bool:
        return self.status in (DRAFT, VALIDATED)

    # ------------------------------------------------------------------
    def update(self, sections: Optional[Dict[str, Dict[str, Any]]] = None, description: Optional[str] = None
               ) -> "StrategyConfiguration":
        """Replace the given sections (a draft / validated configuration only); it goes back to draft."""
        if not self.is_editable:
            raise ConfigurationLocked(f"configuration '{self.name}' v{self.version} is {self.status}: "
                                      f"create a new version")
        for name, values in (sections or {}).items():
            if name not in SECTIONS:
                raise ValueError(f"unknown configuration section '{name}'")
            self._sections[name] = copy.deepcopy(values)
        if description is not None:
            self.description = description
        self.status = DRAFT
        self.validated_at = None
        return self

    def mark_validated(self, normalised_sections: Dict[str, Dict[str, Any]], at: datetime) -> None:
        """Validation passed: store the normalised sections (defaults filled in)."""
        if not self.is_editable:
            raise ConfigurationLocked(f"configuration '{self.name}' v{self.version} is {self.status}")
        self._sections = copy.deepcopy(normalised_sections)
        self.status = VALIDATED
        self.validated_at = at

    def lock(self, at: datetime) -> None:
        """An experiment starts on it: from now on it never changes."""
        if self.status == LOCKED:
            return
        if self.status != VALIDATED:
            raise ValueError(f"only a validated configuration can be used by an experiment (status: {self.status})")
        self.status = LOCKED
        self.locked_at = at

    def archive(self) -> None:
        self.status = ARCHIVED

    def revise(self, new_version: int, name: Optional[str] = None) -> "StrategyConfiguration":
        """A new draft with the same content: the next version of this configuration (or a clone under ``name``,
        starting at version 1)."""
        return StrategyConfiguration(
            name=name or self.name, project_key=self.project_key, sections=self._sections,
            description=self.description, version=1 if name and name != self.name else new_version,
            parent_id=self.id, status=DRAFT,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description, "project_key": self.project_key,
            "version": self.version, "parent_id": self.parent_id, "status": self.status,
            "content_hash": self.content_hash, "sections": self.sections,
            "created_at": self.created_at, "validated_at": self.validated_at, "locked_at": self.locked_at,
        }

    def __repr__(self) -> str:
        return f"<StrategyConfiguration(id={self.id}, name={self.name!r}, v{self.version}, {self.status})>"
