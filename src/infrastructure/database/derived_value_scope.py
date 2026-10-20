"""
All-or-nothing derived values for one operation (BI-006 slice 2b), raw observations kept.

A portfolio valuation resolves holding values (derived, factor source ``calculated``) and, on the way, may fetch
and store raw prices (factor source ``ibkr`` etc.). Rule:

  - raw observations are committed as they arrive and are never undone — they are facts;
  - the derived values written by one operation are kept together or not at all: when the operation fails, the
    derived rows it inserted are deleted and the derived rows it overwrote get their previous value back.

One database transaction cannot keep some rows and drop others, so this is done by compensation: the scope
records every factor value inserted or updated in the session while it is open, and on failure undoes the
derived ones in a new transaction, then re-raises. A nested scope joins the outer one.

Limit: another writer changing the same derived row between the write and the compensation is overwritten by
the restore (the scope is meant for one valuation at one date). The provenance (BI-025) of every derived row the
operation touched is removed: a restored value's quality is unknown until it is recomputed.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Iterator, List

from sqlalchemy import event, inspect

_KEY = "derived_value_scope.active"
DERIVED_SOURCE = "calculated"


@contextmanager
def derived_values_all_or_nothing(session) -> Iterator[None]:
    from src.infrastructure.models.factor.factor_value import FactorValueModel

    if session.info.get(_KEY):                   # nested: the outer scope owns the compensation
        yield
        return

    inserted: List[int] = []
    previous: Dict[int, str] = {}                # id -> value before this operation first changed it

    def _after_flush(sess, _ctx):
        for obj in sess.new:
            if isinstance(obj, FactorValueModel) and obj.id is not None:
                inserted.append(obj.id)
        for obj in sess.dirty:
            if isinstance(obj, FactorValueModel) and obj.id is not None and obj.id not in inserted:
                history = inspect(obj).attrs.value.history
                if history.deleted and obj.id not in previous:
                    previous[obj.id] = history.deleted[0]

    session.info[_KEY] = True
    event.listen(session, "after_flush", _after_flush)
    try:
        yield
    except BaseException:
        event.remove(session, "after_flush", _after_flush)
        session.info.pop(_KEY, None)
        _compensate(session, inserted, previous)
        raise
    event.remove(session, "after_flush", _after_flush)
    session.info.pop(_KEY, None)


def _compensate(session, inserted: List[int], previous: Dict[int, str]) -> None:
    from src.infrastructure.models.factor.factor import FactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel

    session.rollback()                           # whatever was pending when the operation failed
    ids = set(inserted) | set(previous)
    if not ids:
        return
    rows = (session.query(FactorValueModel.id, FactorModel.source)
            .join(FactorModel, FactorModel.id == FactorValueModel.factor_id)
            .filter(FactorValueModel.id.in_(ids)).all())
    derived = {row_id for row_id, source in rows if source == DERIVED_SOURCE}
    to_delete = [i for i in inserted if i in derived]
    # provenance written by the failed operation (BI-025) goes with it: a deleted row has none, a restored row's
    # recorded lineage would describe the failed computation — its quality becomes unknown again
    from src.infrastructure.models.factor.factor_value_provenance import (
        FactorValueLineageModel, FactorValueProvenanceModel,
    )
    touched = list(derived)
    if touched:
        session.query(FactorValueLineageModel).filter(
            FactorValueLineageModel.factor_value_id.in_(touched)).delete(synchronize_session=False)
        session.query(FactorValueLineageModel).filter(
            FactorValueLineageModel.input_factor_value_id.in_(to_delete)).delete(synchronize_session=False)
        session.query(FactorValueProvenanceModel).filter(
            FactorValueProvenanceModel.factor_value_id.in_(touched)).delete(synchronize_session=False)
    if to_delete:
        session.query(FactorValueModel).filter(FactorValueModel.id.in_(to_delete)).delete(synchronize_session=False)
    for row_id, value in previous.items():
        if row_id in derived and row_id not in to_delete:
            session.query(FactorValueModel).filter(FactorValueModel.id == row_id).update(
                {FactorValueModel.value: value}, synchronize_session=False)
    session.commit()
    session.expire_all()
