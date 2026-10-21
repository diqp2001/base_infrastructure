"""
Coverage of stored raw series (BI-029): which expected bars are missing, as a report consumers can read before
trusting a window (a backtest, a training set). Read-only: it never downloads, fills or deletes anything.

    report = DataCoverageService(factory).coverage(close_factor, share, start, end)
    if not report.is_complete(0.98):
        logger.warning(report.summary())
"""

import logging
from datetime import date, datetime, time
from typing import Dict, Iterable, Optional

from src.domain.entities.factor.coverage import CoverageReport, coverage


class DataCoverageService:

    def __init__(self, factory, logger: Optional[logging.Logger] = None):
        self.factory = factory
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def coverage(self, factor, entity, start: date, end: date, as_of: Optional[datetime] = None) -> CoverageReport:
        """Coverage of `factor` for `entity` over [start, end], judged at `as_of` (default: now)."""
        repo = self.factory.factor_value_local_repo
        entity_type = type(entity).__name__.removesuffix("Model")
        stored = repo.get_bar_times(factor.id, entity.id, entity_type, datetime.combine(start, time.min),
                                    datetime.combine(end, time.max))
        report = coverage(stored, start, end, as_of or datetime.now())
        if report.gaps:
            self.logger.warning(f"{getattr(factor, 'name', factor.id)} {entity_type}:{entity.id}: {report.summary()}")
        return report

    def coverage_many(self, factor, entities: Iterable, start: date, end: date,
                      as_of: Optional[datetime] = None) -> Dict[int, CoverageReport]:
        return {entity.id: self.coverage(factor, entity, start, end, as_of) for entity in entities}
