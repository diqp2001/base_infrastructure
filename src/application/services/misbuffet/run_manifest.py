"""
Run manifest (P.08.11, GA-E5 / GA-F6): what a backtest or live session ran with, written to its results_dir.

    run_manifest.json     the latest run (rewritten at start, completed at the end)
    run_manifests.jsonl   every run, one JSON line each (appended at the end, or at a failure)

Content: kind (backtest / live), project, start / end, git commit + dirty flag + the changed files, the config and
its sha256, the data window, the model artifact ids used, the outcome.

A live session refuses a dirty working tree (``require_clean_tree``): the code that trades must be a commit. Changes
under __pycache__ / *.pyc and the local graphify-out/ do not count. A PAPER session may override it with
RUN_MANIFEST_ALLOW_DIRTY=yes (recorded in the manifest); a live account never.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

MANIFEST_FILE = "run_manifest.json"
HISTORY_FILE = "run_manifests.jsonl"
ALLOW_DIRTY_ENV = "RUN_MANIFEST_ALLOW_DIRTY"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[os.pardir] * 4))
IGNORED_CHANGES = ("__pycache__/", ".pyc", "graphify-out/")


class DirtyWorkingTree(RuntimeError):
    pass


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


def build_manifest(kind: str, project: str, config: Dict[str, Any], data_window: Iterable[Any],
                   git: Optional[GitState] = None, started_at: Optional[datetime] = None) -> Dict[str, Any]:
    git = git or git_state()
    return {
        "kind": kind, "project": project, "started_at": str(started_at or datetime.now()), "finished_at": None,
        "outcome": "running", "git": asdict(git), "config_sha256": config_hash(config),
        "data_window": [str(x) for x in data_window], "models": [], "dirty_override": False,
        "config": _redact(_jsonable(config)),
    }


SECRET_KEYS = ("password", "secret", "token", "topic")


def _redact(value):
    """Credentials never reach a results file, whatever a config carries."""
    if isinstance(value, dict):
        return {k: "***" if any(s in str(k).lower() for s in SECRET_KEYS) else _redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def require_clean_tree(manifest: Dict[str, Any], paper: bool) -> None:
    """Live: refuse a dirty or unknown working tree (the override only on a paper account)."""
    git = manifest["git"]
    if git.get("dirty") is False:
        return
    why = (f"{len(git['changed_files'])} uncommitted change(s): {', '.join(git['changed_files'][:5])}"
           if git.get("dirty") else git.get("error") or "git state unknown")
    if paper and os.getenv(ALLOW_DIRTY_ENV, "").lower() in ("1", "yes", "true"):
        manifest["dirty_override"] = True
        return
    raise DirtyWorkingTree(f"live session refused: the working tree is not a clean commit ({why}). Commit the "
                           f"changes first" + (f", or set {ALLOW_DIRTY_ENV}=yes for a paper session" if paper else ""))


def write_manifest(results_dir: str, manifest: Dict[str, Any]) -> str:
    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, MANIFEST_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, default=str)
    return path


def finish_manifest(results_dir: str, manifest: Dict[str, Any], outcome: str, models: Iterable[Any] = ()) -> str:
    """Complete the manifest (outcome, model ids) and append it to the run history."""
    manifest["finished_at"] = str(datetime.now())
    manifest["outcome"] = outcome
    manifest["models"] = sorted({int(m) for m in models if m is not None})
    path = write_manifest(results_dir, manifest)
    with open(os.path.join(results_dir, HISTORY_FILE), "a", encoding="utf-8") as f:
        f.write(json.dumps({k: v for k, v in manifest.items() if k != "config"}, default=str) + "\n")
    return path


def models_of(algorithm) -> List[int]:
    """Artifact ids an STM-style run used: those retrained during it and the newest one (the model scoring)."""
    if algorithm is None:
        return []
    ids = [r.artifact_id for r in getattr(algorithm, "cycle_results", []) or [] if getattr(r, "retrained", False)]
    cycle = getattr(algorithm, "cycle", None)
    if cycle is not None and hasattr(cycle, "model_artifact_id"):
        try:
            ids.append(cycle.model_artifact_id())
        except Exception:
            pass
    return [i for i in ids if i is not None]
