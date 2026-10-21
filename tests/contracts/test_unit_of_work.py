"""
BI-006: one transaction around several repository calls (src/infrastructure/database/unit_of_work.atomic).

Run on SQLite and on the SQL Server test database (`backend` fixture). The repository used,
ContinentRepository, commits inside _create_or_get like every local repository.
"""

import pytest
from sqlalchemy import event

from src.infrastructure.database.unit_of_work import TransactionAborted, atomic
from src.infrastructure.models.continent import ContinentModel
from src.infrastructure.repositories.local_repo.geographic.continent_repository import ContinentRepository


@pytest.fixture
def session(backend):
    s = backend.session()
    yield s
    s.rollback()
    s.query(ContinentModel).filter(ContinentModel.name.like("uow-%")).delete(synchronize_session=False)
    s.commit()
    s.close()


def real_commits(session):
    """Counts the database commits of `session` (the in-memory SQLite engine shares one connection between
    sessions, so visibility from another session cannot show what was only flushed)."""
    count = []
    event.listen(session, "after_commit", lambda s: count.append(1))
    return count


def names(backend):
    with backend.session() as other:                      # what another connection sees (committed data)
        return sorted(n for (n,) in other.query(ContinentModel.name).filter(ContinentModel.name.like("uow-%")))


def test_the_block_commits_once_at_exit(backend, session):
    repo = ContinentRepository(session, factory=None)
    commits = real_commits(session)
    with atomic(session):
        repo._create_or_get("uow-a")
        repo._create_or_get("uow-b")
        assert commits == []                              # the repositories' commits only flushed
    assert len(commits) == 1
    assert names(backend) == ["uow-a", "uow-b"]


def test_an_exception_in_any_step_stores_nothing(backend, session):
    repo = ContinentRepository(session, factory=None)
    with pytest.raises(RuntimeError, match="step 2"):
        with atomic(session):
            repo._create_or_get("uow-a")
            raise RuntimeError("step 2 failed")
    assert names(backend) == []


def test_a_failed_step_aborts_the_whole_transaction(backend, session):
    repo = ContinentRepository(session, factory=None)
    with pytest.raises(TransactionAborted, match="position refused"):
        with atomic(session) as tx:
            repo._create_or_get("uow-a")
            tx.fail("position refused")
            repo._create_or_get("uow-b")
    assert names(backend) == []


def test_a_repository_rollback_inside_the_block_aborts_it(backend, session):
    repo = ContinentRepository(session, factory=None)
    with pytest.raises(TransactionAborted, match="rollback requested by a repository"):
        with atomic(session):
            repo._create_or_get("uow-a")
            session.rollback()                            # what a repository's error handler does
            repo._create_or_get("uow-b")                  # written after the rollback: must not survive either
    assert names(backend) == []


def test_a_nested_block_joins_the_outer_transaction(backend, session):
    repo = ContinentRepository(session, factory=None)
    commits = real_commits(session)
    with pytest.raises(TransactionAborted):
        with atomic(session) as outer:
            repo._create_or_get("uow-a")
            with atomic(session) as inner:
                assert inner is outer
                repo._create_or_get("uow-b")
            assert commits == []                          # the inner block did not commit
            outer.fail("later step failed")
    assert commits == [] and names(backend) == []


def test_the_session_is_usable_after_a_failure(backend, session):
    repo = ContinentRepository(session, factory=None)
    with pytest.raises(RuntimeError):
        with atomic(session):
            repo._create_or_get("uow-a")
            raise RuntimeError("boom")
    with atomic(session):
        repo._create_or_get("uow-c")
    assert names(backend) == ["uow-c"]
    assert "commit" not in vars(session) and "rollback" not in vars(session)   # overrides removed
    repo._create_or_get("uow-d")                          # outside a block the repository commits itself
    assert names(backend) == ["uow-c", "uow-d"]


def test_a_block_that_writes_nothing_does_not_commit(backend, session):
    repo = ContinentRepository(session, factory=None)
    repo._create_or_get("uow-a")
    commits = real_commits(session)
    with atomic(session):
        repo._create_or_get("uow-a")                      # already exists: the repository writes nothing
    assert commits == []
    assert names(backend) == ["uow-a"]


def test_a_database_error_swallowed_by_a_repository_aborts_the_block(backend, session):
    """BI-006 slice 3: the `except Exception: print; return None` repository pattern no longer hides a failed
    write from the transaction owner."""
    from sqlalchemy import text
    repo = ContinentRepository(session, factory=None)

    def swallowing_step():
        try:
            session.execute(text("INSERT INTO no_such_table_uow (x) VALUES (1)"))
        except Exception as e:                            # the repository habit
            print(f"Error: {e}")
            return None

    with pytest.raises(TransactionAborted, match="database error"):
        with atomic(session):
            repo._create_or_get("uow-a")
            swallowing_step()
            repo._create_or_get("uow-b")
    assert names(backend) == []
    with atomic(session):                                 # the session is usable afterwards
        repo._create_or_get("uow-c")
    assert names(backend) == ["uow-c"]


def test_errors_on_other_connections_do_not_abort_the_block(backend, session):
    if backend.name == "sqlite":
        pytest.skip("the in-memory SQLite engine shares one DBAPI connection between sessions (StaticPool)")
    from sqlalchemy import text
    repo = ContinentRepository(session, factory=None)
    with atomic(session):
        repo._create_or_get("uow-a")
        with backend.session() as other:
            with pytest.raises(Exception):
                other.execute(text("SELECT * FROM no_such_table_uow"))
    assert names(backend) == ["uow-a"]
