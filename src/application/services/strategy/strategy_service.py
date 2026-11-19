"""
StrategyService — the use cases of strategies (what the Flask routes call). Replaces StrategyConfigurationService.

create      a draft from the project's defaults (today's DEFAULT_CONFIG) or given sections
update      edit a draft (a locked strategy raises: revise it instead)
validate    schema + project checks; on success the normalised sections and the typed definition derived from the
            project's native config (bar size / frequency, model type, training window, retraining, horizon) are
            stored and the status is 'validated'
assign_universe   reference the Universe the strategy uses (Strategy.universe_id)
revise      next version of a strategy (draft, same definition, parent = the old version)
clone       a new strategy (version 1) with the same definition under another name
lock        called when an experiment starts: the strategy can never change again
native_config / preview   the project's own config dict the strategy translates to
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.application.services.strategy.project_adapters import ProjectRegistry
from src.domain.entities.strategy.configuration_schema import ERROR, ValidationIssue
from src.domain.entities.strategy.strategy import Strategy, canonical_json


class ConfigurationInvalid(Exception):
    def __init__(self, issues: List[ValidationIssue]):
        super().__init__("; ".join(str(i) for i in issues))
        self.issues = issues


class StrategyService:

    def __init__(self, repository, registry: Optional[ProjectRegistry] = None, clock=datetime.utcnow):
        self.repository = repository
        self.registry = registry or ProjectRegistry()
        self.clock = clock

    # -- reads --------------------------------------------------------------------------------------------------
    def get(self, configuration_id: int) -> Strategy:
        configuration = self.repository.get_by_id(configuration_id)
        if configuration is None:
            raise LookupError(f"strategy {configuration_id} does not exist")
        return configuration

    def list(self) -> List[Strategy]:
        return self.repository.get_all()

    def versions(self, name: str) -> List[Strategy]:
        return self.repository.get_versions(name)

    # -- writes -------------------------------------------------------------------------------------------------
    def create(self, name: str, strategy_type: Optional[str] = None,
               sections: Optional[Dict[str, Dict[str, Any]]] = None, description: str = "",
               universe_id: Optional[int] = None, project_key: Optional[str] = None) -> Strategy:
        """A draft of ``strategy_type`` (``project_key``: its former name) from the project's defaults."""
        strategy_type = strategy_type or project_key
        name = (name or "").strip()
        if not name:
            raise ValueError("a strategy needs a name")
        if self.repository.latest_version_number(name):
            raise ValueError(f"a strategy named '{name}' already exists: revise or clone it")
        adapter = self.registry.get(strategy_type)
        content = adapter.default_sections()
        for section, values in (sections or {}).items():
            content[section] = {**content.get(section, {}), **values}
        configuration = Strategy(name=name, strategy_type=strategy_type, sections=content, description=description,
                                 universe_id=universe_id, created_at=self.clock(), **self._definition(adapter, content))
        return self.repository.add(configuration)

    @staticmethod
    def _definition(adapter, sections) -> Dict[str, Any]:
        """The typed definition the project's native config gives for these sections ({} when it cannot be built:
        invalid sections are reported by validate)."""
        try:
            normalised, issues = adapter.validate(sections)
            if any(i.severity == ERROR for i in issues):
                return {}
            return adapter.definition(normalised)
        except Exception:
            return {}

    def assign_universe(self, strategy_id: int, universe_id: Optional[int]) -> Strategy:
        """Reference the Universe the strategy uses (draft / validated only; it goes back to draft)."""
        strategy = self.get(strategy_id)
        strategy.assign_universe(universe_id)                  # raises StrategyLocked when locked
        return self.repository.update(strategy)

    def update(self, configuration_id: int, sections: Dict[str, Dict[str, Any]],
               description: Optional[str] = None) -> Strategy:
        configuration = self.get(configuration_id)
        merged = {name: {**configuration.section(name), **values} for name, values in (sections or {}).items()}
        configuration.update(merged, description=description)          # raises ConfigurationLocked when locked
        return self.repository.update(configuration)

    def update_from_form(self, configuration_id: int, form: Dict[str, Any], description: Optional[str] = None
                         ) -> Tuple[Strategy, List[ValidationIssue]]:
        """``form``: {'section.field': raw text} as posted by the edit page. Every field of the project's schema is
        parsed to its type (an unchecked checkbox is absent: False); a value that does not parse is kept as typed
        and reported, so the draft never silently changes it."""
        from src.domain.entities.strategy.configuration_schema import coerce
        configuration = self.get(configuration_id)
        schema = self.registry.get(configuration.strategy_type).schema()
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

    def check(self, configuration: Strategy) -> Tuple[Dict[str, Dict[str, Any]], List[ValidationIssue]]:
        """Validation without saving anything (a project-folder strategy: it must apply onto the project)."""
        adapter = self.registry.get(configuration.strategy_type)
        if hasattr(adapter, "validate_strategy"):
            return adapter.validate_strategy(configuration)
        return adapter.validate(configuration.sections)

    def validate(self, configuration_id: int) -> Tuple[Strategy, List[ValidationIssue]]:
        configuration = self.get(configuration_id)
        if configuration.status not in ("draft", "validated"):
            return configuration, []
        normalised, issues = self.check(configuration)
        if not any(i.severity == ERROR for i in issues):
            definition = self.registry.get(configuration.strategy_type).definition(normalised)
            configuration.mark_validated(normalised, self.clock(), definition=definition)
            configuration = self.repository.update(configuration)
        return configuration, issues

    def revise(self, configuration_id: int) -> Strategy:
        source = self.get(configuration_id)
        latest = self.repository.latest_version_number(source.name)
        revision = source.revise(new_version=latest + 1)
        revision.created_at = self.clock()
        return self.repository.add(revision)

    def clone(self, configuration_id: int, name: str) -> Strategy:
        name = (name or "").strip()
        if not name:
            raise ValueError("a clone needs a name")
        if self.repository.latest_version_number(name):
            raise ValueError(f"a strategy named '{name}' already exists")
        clone = self.get(configuration_id).revise(new_version=1, name=name)
        clone.created_at = self.clock()
        return self.repository.add(clone)

    def lock(self, configuration_id: int) -> Strategy:
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

    def archive(self, configuration_id: int) -> Strategy:
        configuration = self.get(configuration_id)
        configuration.archive()
        return self.repository.update(configuration)

    # -- translation ----------------------------------------------------------------------------------------------
    def native_config(self, configuration: Strategy, **kwargs) -> Dict[str, Any]:
        adapter = self.registry.get(configuration.strategy_type)
        normalised, issues = self.check(configuration)
        errors = [i for i in issues if i.severity == ERROR]
        if errors:
            raise ConfigurationInvalid(errors)
        if hasattr(adapter, "native_config_for"):          # project-folder strategy: applied onto the project
            return adapter.native_config_for(configuration, normalised, **kwargs)
        return adapter.native_config(normalised, **kwargs)

    def preview(self, configuration_id: int) -> Dict[str, Any]:
        """What the configuration is, what it changes against its parent / the project defaults, and the issues."""
        configuration = self.get(configuration_id)
        adapter = self.registry.get(configuration.strategy_type)
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


StrategyConfigurationService = StrategyService        # former name
StrategyInvalid = ConfigurationInvalid
