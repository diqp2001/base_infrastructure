"""
Run identity helpers (generic research / backtest registry, 2026-11-18): the code version and a JSON-safe, redacted
snapshot of a configuration. Used by the run registry (backtest_run_service) and by misbuffet's run_manifest (which
re-exports them): misbuffet depends on the registry, never the reverse.

    git_state() -> GitState(commit, dirty, changed_files)     git_branch() -> name | None
    _jsonable(config) -> plain JSON    _redact(value) -> secrets as '***'    config_hash(config) -> sha256
    pid_alive(pid) -> bool (never os.kill(pid, 0) on Windows: it terminates the process)
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[os.pardir] * 4))
IGNORED_CHANGES = ("__pycache__/", ".pyc", "graphify-out/")


@dataclass
class GitState:
    commit: Optional[str] = None
    dirty: Optional[bool] = None                 # None = unknown (git unavailable)
    changed_files: List[str] = field(default_factory=list)
    error: Optional[str] = None


def _git(args: List[str], root: str) -> str:
    # safe.directory: a bind-mounted clone owned by another uid (Docker) is otherwise refused ("dubious ownership")
    return subprocess.run(["git", "-c", f"safe.directory={root}", *args], cwd=root, capture_output=True,
                          text=True, timeout=30, check=True).stdout


def git_state(root: str = REPO_ROOT) -> GitState:
    try:
        commit = _git(["rev-parse", "HEAD"], root).strip()
        lines = _git(["status", "--porcelain", "--untracked-files=no"], root).splitlines()
    except Exception as e:
        return GitState(error=f"git unavailable: {e!r}"[:300])
    changed = [line[3:].strip() for line in lines if line.strip()]
    changed = [p for p in changed if not any(marker in p.replace("\\", "/") for marker in IGNORED_CHANGES)]
    return GitState(commit=commit, dirty=bool(changed), changed_files=changed)


def git_branch(root: str = REPO_ROOT) -> Optional[str]:
    """Current branch name (None when detached or git is unavailable)."""
    try:
        name = _git(["rev-parse", "--abbrev-ref", "HEAD"], root).strip()
    except Exception:
        return None
    return None if name in ("", "HEAD") else name


def _jsonable(value):
    """Config as plain JSON: keys and values that are not JSON (a class key such as universe {CompanyShare: [...]},
    a date) become their str()."""
    if isinstance(value, dict):
        return {k if isinstance(k, str) else str(getattr(k, "__name__", k)): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def config_hash(config: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(_jsonable(config), sort_keys=True).encode("utf-8")).hexdigest()


SECRET_KEYS = ("password", "secret", "token", "topic")


def _redact(value):
    """Credentials never reach a results file, whatever a config carries."""
    if isinstance(value, dict):
        return {k: "***" if any(s in str(k).lower() for s in SECRET_KEYS) else _redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def pid_alive(pid: Optional[int]) -> bool:
    """Never os.kill(pid, 0) on Windows: it terminates the process."""
    if not pid:
        return False
    try:
        import psutil
        p = psutil.Process(int(pid))
        return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False
