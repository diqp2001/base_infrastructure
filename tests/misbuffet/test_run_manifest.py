"""P.08.11: run manifest (config, commit + dirty flag, data window, models) in results_dir; a live session refuses
a dirty working tree. Git runs on a throwaway repository in a temp folder."""

import json
import os
import subprocess
from types import SimpleNamespace

import pytest

from src.application.services.misbuffet import run_manifest as rm


def _repo(tmp_path):
    root = str(tmp_path / "repo")
    os.makedirs(os.path.join(root, "pkg", "__pycache__"))
    for args in (["init", "-q"], ["config", "user.email", "t@example.com"], ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=root, check=True)
    for path in ("pkg/a.py", "pkg/__pycache__/a.cpython-313.pyc"):
        with open(os.path.join(root, path), "w") as f:
            f.write("x = 1\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)
    return root


def _write(root, path, text):
    with open(os.path.join(root, path), "w") as f:
        f.write(text)


def test_clean_tree_and_ignored_bytecode(tmp_path):
    root = _repo(tmp_path)
    state = rm.git_state(root)
    assert state.dirty is False and len(state.commit) == 40 and state.error is None
    _write(root, "pkg/__pycache__/a.cpython-313.pyc", "changed")              # bytecode: not a code change
    _write(root, "untracked.py", "new")                                       # untracked: not counted
    assert rm.git_state(root).dirty is False
    _write(root, "pkg/a.py", "x = 2\n")
    state = rm.git_state(root)
    assert state.dirty is True and state.changed_files == ["pkg/a.py"]


def test_git_unavailable_is_unknown_not_clean(tmp_path):
    state = rm.git_state(str(tmp_path))                                       # not a repository
    assert state.dirty is None and state.commit is None and "git unavailable" in state.error


def test_manifest_written_with_the_commit_config_window_and_models(tmp_path):
    root = _repo(tmp_path)
    config = {"backtest_start": "2026-10-05", "db": {"password": "hunter2"}, "ntfy_topic": "x"}
    manifest = rm.build_manifest("backtest", "stm10m", config, ("2026-09-01", "2026-10-05", "2026-10-09"),
                                 git=rm.git_state(root))
    results = str(tmp_path / "results")
    rm.write_manifest(results, manifest)
    started = json.load(open(os.path.join(results, rm.MANIFEST_FILE)))
    assert started["outcome"] == "running" and started["git"]["commit"] == manifest["git"]["commit"]
    assert started["config"]["db"]["password"] == "***" and started["config"]["ntfy_topic"] == "***"
    assert started["config_sha256"] == rm.config_hash(config)
    algorithm = SimpleNamespace(cycle_results=[SimpleNamespace(retrained=True, artifact_id=41),
                                               SimpleNamespace(retrained=False, artifact_id=None)],
                                cycle=SimpleNamespace(model_artifact_id=lambda: 45))
    rm.finish_manifest(results, manifest, "completed", rm.models_of(algorithm))
    done = json.load(open(os.path.join(results, rm.MANIFEST_FILE)))
    assert (done["outcome"], done["models"], done["data_window"]) == ("completed", [41, 45],
                                                                     ["2026-09-01", "2026-10-05", "2026-10-09"])
    history = [json.loads(line) for line in open(os.path.join(results, rm.HISTORY_FILE))]
    assert len(history) == 1 and "config" not in history[0] and history[0]["models"] == [41, 45]


def test_a_dirty_tree_is_refused_in_live_mode(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    clean = rm.build_manifest("live", "STM", {}, (), git=rm.git_state(root))
    rm.require_clean_tree(clean, paper=False)                                 # clean: allowed
    _write(root, "pkg/a.py", "x = 3\n")
    dirty = rm.build_manifest("live", "STM", {}, (), git=rm.git_state(root))
    with pytest.raises(rm.DirtyWorkingTree, match="pkg/a.py"):
        rm.require_clean_tree(dirty, paper=False)
    unknown = rm.build_manifest("live", "STM", {}, (), git=rm.GitState(error="git unavailable"))
    with pytest.raises(rm.DirtyWorkingTree, match="git unavailable"):
        rm.require_clean_tree(unknown, paper=True)
    monkeypatch.setenv(rm.ALLOW_DIRTY_ENV, "yes")
    with pytest.raises(rm.DirtyWorkingTree):
        rm.require_clean_tree(dirty, paper=False)                             # a live account: never
    rm.require_clean_tree(dirty, paper=True)                                  # paper: override, recorded
    assert dirty["dirty_override"] is True


def test_the_supervisor_does_not_restart_a_refused_session():
    from datetime import date, datetime, time
    from src.application.services.misbuffet.live.daily_supervisor import (
        REFUSED_DIRTY_TREE, DailySupervisor, SupervisorConfig,
    )
    calls, alerts = [], []
    supervisor = DailySupervisor(
        name="STM", config=SupervisorConfig(start_time=time(9, 20), max_restarts=3, restart_delay_seconds=0),
        sessions=lambda start, end: [(date(2026, 11, 5), datetime(2026, 11, 5, 9, 30), datetime(2026, 11, 5, 16))],
        run_session=lambda: calls.append(1) or REFUSED_DIRTY_TREE,
        now=lambda: datetime(2026, 11, 5, 9, 25), notifier=None, heartbeat_path=None)
    supervisor._alert = lambda title, text, priority: alerts.append(title)
    outcome = supervisor.run_day(date(2026, 11, 5), datetime(2026, 11, 5, 16))
    assert len(calls) == 1 and outcome.status == "refused: dirty working tree" and alerts == ["not started"]
