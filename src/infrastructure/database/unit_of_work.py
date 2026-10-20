"""
One transaction around several repository calls (BI-006).

The local repositories commit after each write (and roll back in their own error handlers), so a use case that
writes through several of them is not atomic by default. ``atomic(session)`` makes it atomic without changing the
repositories:

    with atomic(session) as tx:
        order_repo.add(order)            # repository commit() -> flush only
        position_repo.update(position)
        if not ok:
            tx.fail("position update refused")
    # exit: one real commit; any exception, failed step or repository rollback -> one real rollback

- Owner: the outermost ``atomic`` block owns commit / rollback. A nested ``atomic`` on the same session joins the
  outer transaction (its failures abort the outer one; it never commits on its own).
- A repository calling ``session.rollback()`` inside the block (its error handler) rolls back immediately and
  marks the transaction failed: the block cannot commit afterwards.
- On failure the block raises (the exception, or ``TransactionAborted`` with the recorded failures); the session
  is clean and usable for the next transaction.
- A block that wrote nothing (no repository commit requested, no pending change) does not commit: wrapping an
  idempotent "ensure" step costs nothing when the rows already exist.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, List

_KEY = "unit_of_work.transaction"


class TransactionAborted(Exception):
    """The block completed but a step failed (``fail`` or a repository rollback): nothing was committed."""

    def __init__(self, failures: List[str]):
        super().__init__("; ".join(failures) or "transaction aborted")
        self.failures = list(failures)


class Transaction:
    def __init__(self):
        self.failures: List[str] = []

    def fail(self, reason: str) -> None:
        """Record a failed step: the transaction will roll back instead of committing."""
        self.failures.append(reason)

    @property
    def failed(self) -> bool:
        return bool(self.failures)


@contextmanager
def atomic(session) -> Iterator[Transaction]:
    current = session.info.get(_KEY)
    if current is not None:                      # nested: join the owner's transaction
        yield current
        return

    tx = Transaction()
    real_commit, real_rollback = session.commit, session.rollback
    commit_requested = []

    def _commit():
        commit_requested.append(True)
        session.flush()

    def _rollback():
        tx.fail("rollback requested by a repository")
        real_rollback()

    session.info[_KEY] = tx
    session.commit, session.rollback = _commit, _rollback
    try:
        yield tx
    except BaseException:
        _restore(session, real_commit, real_rollback)
        real_rollback()
        raise
    _restore(session, real_commit, real_rollback)
    if tx.failed:
        real_rollback()
        raise TransactionAborted(tx.failures)
    if not (commit_requested or session.new or session.dirty or session.deleted):
        return                                   # nothing written in the block: nothing to commit
    try:
        real_commit()
    except BaseException:
        real_rollback()
        raise


def _restore(session, real_commit, real_rollback) -> None:
    """Remove the overrides: the session's own commit / rollback apply again."""
    for name, real in (("commit", real_commit), ("rollback", real_rollback)):
        if name in vars(session):
            del vars(session)[name]
        if getattr(session, name) != real:          # was itself an instance override before the block
            setattr(session, name, real)
    session.info.pop(_KEY, None)
