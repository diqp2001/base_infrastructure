"""
StrategyConfigurationService — the use cases of strategy configurations (what the Flask routes call).

create      a draft from the project's defaults (today's DEFAULT_CONFIG) or given sections
update      edit a draft (a locked configuration raises: revise it instead)
validate    schema + project checks; on success the normalised sections are stored and the status is 'validated'
revise      next version of a configuration (draft, same content, parent = the old version)
clone       a new configuration (version 1) with the same content under another name
lock        called when an experiment starts: the configuration can never change again
native_config / preview   the project's own config dict the configuration translates to
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.application.services.strategy.project_adapters import ProjectRegistry
from src.domain.entities.strategy.configuration_schema import ERROR, ValidationIssue
from src.domain.entities.strategy.strategy_configuration import (
    StrategyConfiguration,
    canonical_json,
)


class ConfigurationInvalid(Exception):
    def __init__(self, issues: List[ValidationIssue]):
        super().__init__("; ".join(str(i) for i in issues))
        self.issues = issues


class StrategyConfigurationService:

    def __init__(self, repository, registry: Optional[ProjectRegistry] = None, clock=datetime.utcnow):
        self.repository = repository
        self.registry = registry or ProjectRegistry()
        self.clock = clock

    # -- reads --------------------------------------------------------------------------------------------------
    def get(self, configuration_id: int) -> StrategyConfiguration:
        configuration = self.repository.get_by_id(configuration_id)
        if configuration is None:
            raise LookupError(f"strategy configuration {configuration_id} does not exist")
        return configuration

    def list(self) -> List[StrategyConfiguration]:
        return self.repository.get_all()

    def versions(self, name: str) -> List[StrategyConfiguration]:
        return self.repository.get_versions(name)

    # -- writes -------------------------------------------------------------------------------------------------
    def create(self, name: str, project_key: str, sections: Optional[Dict[str, Dict[str, Any]]] = None,
               description: str = "") -> StrategyConfiguration:
        name = (name or "").strip()
        if not name:
            raise ValueError("a configuration needs a name")
        if self.repository.latest_version_number(name):
            raise ValueError(f"a configuration named '{name}' already exists: revise or clone it")
        adapter = self.registry.get(project_key)
        content = adapter.default_sections()
        for section, values in (sections or {}).items():
            content[section] = {**content.get(section, {}), **values}
        configuration = StrategyConfiguration(name=name, project_key=project_key, sections=content,
                                              description=description, created_at=self.clock())
        return self.repository.add(configuration)

    def update(self, configuration_id: int, sections: Dict[str, Dict[str, Any]],
               description: Optional[str] = None) -> StrategyConfiguration:
        configuration = self.get(configuration_id)
        merged = {name: {**configuration.section(name), **values} for name, values in (sections or {}).items()}
        configuration.update(merged, description=description)          # raises ConfigurationLocked when locked
        return self.repository.update(configuration)

    def update_from_form(self, configuration_id: int, form: Dict[str, Any], description: Optional[str] = None
                         ) -> Tuple[StrategyConfiguration, List[ValidationIssue]]:
        """``form``: {'section.field': raw text} as posted by the edit page. Every field of the project's schema is
        parsed to its type (an unchecked checkbox is absent: False); a value that does not parse is kept as typed
        and reported, so the draft never silently changes it."""
        from src.domain.entities.strategy.configuration_schema import coerce
        configuration = self.get(configuration_id)
        schema = self.registry.get(configuration.project_key).schema()
        sections: Dict[str, Dict[str, Any]] = {}
        issues: List[ValidationIssue] = []
        for section in schema.sections:
            values = {}
            for spec in section.fields:
                key = f"{section.name}.{spec.name}"
                if spec.kind == "bool":
                    raw = form.get(key, "off")
                elif spec.kind == "choice_list":
                    raw = form.get(key, [])
                elif key not in form:
                    continue
                else:
                    raw = form[key]
                if spec.kind == "choice" and raw == "" and None in spec.choices:
                    values[spec.name] = None
                    continue
                if spec.kind == "choice":
                    raw = next((c for c in spec.choices if str(c) == str(raw)), raw)
                value, error = coerce(spec, raw)
                if error:
                    issues.append(ValidationIssue(section.name, spec.name, error))
                values[spec.name] = value
            sections[section.name] = values
        return self.update(configuration_id, sections, description=description), issues

    def check(self, configuration: StrategyConfiguration) -> Tuple[Dict[str, Dict[str, Any]], List[ValidationIssue]]:
        """Validation without saving anything."""
        return self.registry.get(configuration.project_key).validate(configuration.sections)

    def validate(self, configuration_id: int) -> Tuple[StrategyConfiguration, List[ValidationIssue]]:
        configuration = self.get(configuration_id)
        if configuration.status not in ("draft", "validated"):
            return configuration, []
        normalised, issues = self.check(configuration)
        if not any(i.severity == ERROR for i in issues):
            configuration.mark_validated(normalised, self.clock())
            configuration = self.repository.update(configuration)
        return configuration, issues

    def revise(self, configuration_id: int) -> StrategyConfiguration:
        source = self.get(configuration_id)
        latest = self.repository.latest_version_number(source.name)
        revision = source.revise(new_version=latest + 1)
        revision.created_at = self.clock()
        return self.repository.add(revision)

    def clone(self, configuration_id: int, name: str) -> StrategyConfiguration:
        name = (name or "").strip()
        if not name:
            raise ValueError("a clone needs a name")
        if self.repository.latest_version_number(name):
            raise ValueError(f"a configuration named '{name}' already exists")
        clone = self.get(configuration_id).revise(new_version=1, name=name)
        clone.created_at = self.clock()
        return self.repository.add(clone)

    def lock(self, configuration_id: int) -> StrategyConfiguration:
        """Before an experiment: validate again (data checks may depend on the content) and freeze."""
        configuration = self.get(configuration_id)
        if configuration.status == "locked":
            return configuration
        configuration, issues = self.validate(configuration_id)
        errors = [i for i in issues if i.severity == ERROR]
        if errors:
            raise ConfigurationInvalid(errors)
        configuration.lock(self.clock())
        return self.repository.update(configuration)

    def archive(self, configuration_id: int) -> StrategyConfiguration:
        configuration = self.get(configuration_id)
        configuration.archive()
        return self.repository.update(configuration)

    # -- translation ----------------------------------------------------------------------------------------------
    def native_config(self, configuration: StrategyConfiguration, **kwargs) -> Dict[str, Any]:
        adapter = self.registry.get(configuration.project_key)
        normalised, issues = adapter.validate(configuration.sections)
        errors = [i for i in issues if i.severity == ERROR]
        if errors:
            raise ConfigurationInvalid(errors)
        return adapter.native_config(normalised, **kwargs)

    def preview(self, configuration_id: int) -> Dict[str, Any]:
        """What the configuration is, what it changes against its parent / the project defaults, and the issues."""
        configuration = self.get(configuration_id)
        adapter = self.registry.get(configuration.project_key)
        base = (self.get(configuration.parent_id).sections if configuration.parent_id
                else adapter.default_sections())
        changes = []
        for section, values in configuration.sections.items():
            for key, value in values.items():
                before = base.get(section, {}).get(key)
                if canonical_json(before) != canonical_json(value):
                    changes.append({"section": section, "field": key, "before": before, "after": value})
        _, issues = self.check(configuration)
        return {"configuration": configuration.to_dict(), "changes": changes,
                "compared_with": "parent version" if configuration.parent_id else "project defaults",
                "issues": [vars(i) for i in issues]}
