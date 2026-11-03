"""
One live session per strategy (P.08.05). A second session started by mistake (another window, another client id)
would trade the same book twice: TWS only refuses a second connection with the SAME client id.

SessionLock is an exclusive, non-blocking OS lock on a file (msvcrt on Windows, fcntl elsewhere): the operating
system releases it when the process ends, crashes included, so a stale lock never blocks the next start. Who holds
it (pid, start time, purpose) is written to `<path>.info` for the refusal message.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional


class SessionLockedError(RuntimeError):
    pass


class SessionLock:

    def __init__(self, path: str, purpose: str = "session"):
        self.path = path
        self.info_path = path + ".info"
        self.purpose = purpose
        self._handle = None

    def acquire(self) -> "SessionLock":
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        handle = open(self.path, "a+b")
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise SessionLockedError(f"another live session holds {self.path}: {self.holder() or 'unknown holder'}"
                                     f" — stop it first (one session per strategy)")
        self._handle = handle
        with open(self.info_path, "w", encoding="utf-8") as f:
            f.write(f"pid {os.getpid()}, {self.purpose}, since {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC")
        return self

    def holder(self) -> Optional[str]:
        try:
            with open(self.info_path, encoding="utf-8") as f:
                return f.read().strip() or None
        except OSError:
            return None

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> "SessionLock":
        return self.acquire()

    def __exit__(self, *exc) -> None:
        self.release()
