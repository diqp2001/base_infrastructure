"""Former entry point of the project, kept so existing imports (src/main.py) keep working."""

from src.application.managers.project_managers.cross_sectionnal_project.project_manager import (
    CrossSectionalMomentumProjectManager,
)

CrossSectionnal = CrossSectionalMomentumProjectManager

__all__ = ["CrossSectionalMomentumProjectManager", "CrossSectionnal"]
