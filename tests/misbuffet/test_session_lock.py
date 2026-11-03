"""P.08.05 one live session per strategy: an OS file lock, released by the OS when its process dies."""

import subprocess
import sys

import pytest

from src.application.services.misbuffet.live.session_lock import SessionLock, SessionLockedError

ROOT = __file__.rsplit("tests", 1)[0]


def other_process(path, hold_and_crash=False):
    """Try the lock from another process; with hold_and_crash it takes it and dies without releasing it."""
    code = (f"import os, sys; sys.path.insert(0, {ROOT!r})\n"
            "from src.application.services.misbuffet.live.session_lock import SessionLock, SessionLockedError\n"
            f"lock = SessionLock({path!r}, 'other')\n"
            "try:\n    lock.acquire()\nexcept SessionLockedError as e:\n    print('REFUSED', e); sys.exit(3)\n"
            + ("os._exit(0)\n" if hold_and_crash else "print('ACQUIRED')\nlock.release()\n"))
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)


def test_a_second_process_is_refused_while_the_session_runs(tmp_path):
    path = str(tmp_path / "S.session.lock")
    with SessionLock(path, "run"):
        result = other_process(path)
        assert result.returncode == 3, result.stderr
        assert "REFUSED" in result.stdout and "run, since" in result.stdout     # who holds it
    assert other_process(path).stdout.strip().splitlines()[-1] == "ACQUIRED"    # released at the end


def test_a_crashed_holder_never_leaves_a_stale_lock(tmp_path):
    path = str(tmp_path / "S.session.lock")
    assert other_process(path, hold_and_crash=True).returncode == 0
    with SessionLock(path, "run") as lock:                                      # the OS released it
        assert "run" in lock.holder()


def test_run_and_check_refuse_while_the_lock_is_held(tmp_path, monkeypatch):
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live import config as cfg
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.project_manager import (
        SpatioTemporalMomentum10mLiveProjectManager as Manager,
    )
    manager = Manager.__new__(Manager)
    manager.results_dir, manager.config = str(tmp_path), cfg.get_config()
    started = []
    monkeypatch.setattr(Manager, "_run", lambda self: started.append("run") or {"ok": True})
    monkeypatch.setattr(Manager, "_check", lambda self: started.append("check") or {"ok": True})
    with manager.session_lock("run"):
        with pytest.raises(SessionLockedError):
            manager.check()
        with pytest.raises(SessionLockedError):
            manager.run()
    assert started == []
    assert manager.run() == {"ok": True} and manager.check() == {"ok": True} and started == ["run", "check"]
