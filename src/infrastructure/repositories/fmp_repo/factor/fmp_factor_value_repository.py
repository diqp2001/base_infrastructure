"""
FMP Factor Value Repository - company financial statements from Financial Modeling Prep as factor values (the
counterpart of IBKRFactorValueRepository for source 'fmp').

Pipeline: FMP statement rows -> StatementRecord (fmp_repo/finance/financial_statements) -> raw CompanyShareFactor
series (group 'fundamental', subgroup = statement, frequency 1q | 1y, source 'fmp', name = the FMP field) -> factor
values stamped at the filing's publication (StatementRecord.available_at), stored through the local
FactorValueRepository (add_bulk: a value already stored is kept, never overwritten).

FactorValueResolutionService calls fetch_factor_value (FactorValueProviderPort) for a raw 'fmp' series with no value known at the
decision time (family 'fmp', see RepositoryFactory.create_fmp_repositories): the statement's whole history at that
frequency is loaded once per (share, statement, frequency) and session, then the value is read as of the decision
time (Factor.point_in_time_policy) - a statement published after the decision time is never returned.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Tuple

from src.domain.entities.factor.factor_value import FactorValue
from src.domain.ports.factor.factor_value_provider_port import FactorValueProviderPort
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_factor import (
    ANNUAL, GROUP, METADATA_FIELDS, QUARTERLY,
)
from src.infrastructure.repositories.fmp_repo.base_fmp_repository import BaseFMPRepository
from src.infrastructure.repositories.fmp_repo.finance.financial_statements.fmp_financial_statement_repository import (
    PERIOD_REQUESTS, STATEMENT_REPOSITORIES, StatementRecord,
)
from src.infrastructure.repositories.fmp_repo.fmp_client import FMPError

logger = logging.getLogger(__name__)

SOURCE = "fmp"
FREQUENCY_LABEL = {QUARTERLY: "quarterly", ANNUAL: "annual"}
SHARE_COUNT_FIELDS = frozenset({"weightedAverageShsOut", "weightedAverageShsOutDil"})   # not amounts


class FMPFactorValueRepository(BaseFMPRepository, FactorValueProviderPort):
    """Stores FMP financial statements as raw fundamental factor values and serves them as of a decision time."""

    def __init__(self, fmp_client, factory=None, limit: Optional[int] = None):
        super().__init__(fmp_client, factory)
        self.statements = {s: (cls(fmp_client, factory) if limit is None else cls(fmp_client, factory, limit=limit))
                           for s, cls in STATEMENT_REPOSITORIES.items()}
        self._loaded: Dict[Tuple[int, str, str], int] = {}     # (entity id, statement, frequency) -> values stored
        self._factors: Dict[Tuple[str, str, str], CompanyShareFactor] = {}
        self._currencies: Dict[str, Optional[int]] = {}

    # -- raw series --
    def raw_factor(self, statement: str, frequency: str, name: str) -> Optional[CompanyShareFactor]:
        """The raw series of one FMP field (created on first use)."""
        key = (statement, frequency, name)
        if key not in self._factors:
            repo = self.factory.get_local_repository("CompanyShareFactor")
            factor = repo._create_or_get(
                CompanyShareFactor, name, group=GROUP, subgroup=statement, frequency=frequency,
                data_type=METADATA_FIELDS.get(name, "numeric"), source=SOURCE,
                definition=f"FMP {statement.replace('_', ' ')} ({FREQUENCY_LABEL[frequency]}): {name}")
            if factor is None:
                return None
            self._factors[key] = factor
        return self._factors[key]

    def currency_id(self, iso_code: Optional[str]) -> Optional[int]:
        """The stored Currency of a reported currency code, or None (logged once: not created here - a currency
        needs its country)."""
        if not iso_code:
            return None
        if iso_code not in self._currencies:
            repo = self.factory.get_local_repository("Currency")
            currency = repo.get_by_iso_code(iso_code) if repo is not None and hasattr(repo, "get_by_iso_code") else None
            self._currencies[iso_code] = getattr(currency, "id", None)
            if currency is None:
                logger.warning(f"FMP: reported currency {iso_code} is not a stored Currency - its values keep the "
                               f"share's currency id; the 'reportedCurrency' series has the reported one")
        return self._currencies[iso_code]

    def factor_values(self, entity, records: Iterable[StatementRecord]) -> List[FactorValue]:
        """One value per (record, field), stamped at the record's publication; missing fields are not stored.
        Amounts carry the reported currency (FactorValue.currency_id); share counts and the filing's data do not."""
        entity_type = type(entity).__name__.removesuffix("Model")
        rows = []
        for record in records:
            currency_id = self.currency_id(record.reported_currency)
            items = [(n, v, None) for n, v in record.metadata().items() if v is not None]
            items += [(n, repr(float(v)), None if n in SHARE_COUNT_FIELDS else currency_id)
                      for n, v in record.values.items() if v is not None]
            for name, value, value_currency in items:
                factor = self.raw_factor(record.statement, record.frequency, name)
                if factor is None:
                    continue
                rows.append(FactorValue(id=None, factor_id=factor.id, entity=None, entity_id=entity.id,
                                        entity_type=entity_type, date=record.available_at, value=value,
                                        currency_id=value_currency))
        return rows

    def store(self, entity, records: Iterable[StatementRecord]) -> int:
        return self.factory.get_local_repository("FactorValue").add_bulk(self.factor_values(entity, records))

    # -- loading --
    def load_statements(self, entity, statement: str, frequency: str, force: bool = False) -> int:
        """Fetch and store one statement's history for a share (once per session unless force). Returns the number
        of values inserted. A failed request is logged and stores nothing."""
        key = (entity.id, statement, frequency)
        if key in self._loaded and not force:
            return 0
        symbol = self.symbol_of(entity)
        if not symbol or statement not in self.statements or frequency not in PERIOD_REQUESTS:
            return 0
        try:
            records = self.statements[statement].fetch(symbol, frequency)
        except FMPError as e:
            logger.error(f"FMP {statement} {frequency} {symbol}: {e}")
            self._loaded[key] = 0           # not asked again in this session: the answer would be the same
            return 0
        stored = self.store(entity, records)
        self._loaded[key] = stored
        logger.info(f"FMP {statement} {frequency} {symbol}: {len(records)} periods, {stored} values stored")
        return stored

    def load_company(self, entity, statements: Optional[Iterable[str]] = None,
                     frequencies: Iterable[str] = (QUARTERLY, ANNUAL)) -> Dict[str, int]:
        """Every statement at every frequency for one share: {'<statement> <frequency>': values stored}."""
        return {f"{s} {f}": self.load_statements(entity, s, f)
                for s in (statements or self.statements) for f in frequencies}

    # -- the resolution service's provider hook --
    def fetch_factor_value(self, factor_entity, entity, time_date, **kwargs) -> Optional[FactorValue]:
        """FactorValueProviderPort: the value of a raw FMP series known at time_date, loading the statement first
        when needed. Serves source 'fmp' fundamental series only (None for any other series)."""
        if (entity is None or getattr(factor_entity, "source", None) != SOURCE
                or getattr(factor_entity, "group", None) != GROUP):
            return None
        statement, frequency = getattr(factor_entity, "subgroup", None), getattr(factor_entity, "frequency", None)
        if statement not in self.statements or frequency not in PERIOD_REQUESTS:
            return None
        self.load_statements(entity, statement, frequency)
        return self.value_as_of(factor_entity, entity, time_date)

    def value_as_of(self, factor_entity, entity, time_date) -> Optional[FactorValue]:
        """The latest stored value published by time_date, within the series' max age (point in time)."""
        policy = factor_entity.point_in_time_policy() if hasattr(factor_entity, "point_in_time_policy") else None
        if policy is None:
            return None
        if isinstance(time_date, str):
            when = datetime.fromisoformat(time_date)
        elif isinstance(time_date, datetime):
            when = time_date
        else:
            when = datetime.combine(time_date, datetime.min.time()) if isinstance(time_date, date) else None
        if when is None:
            return None
        when = when.replace(tzinfo=None)
        repo = self.factory.get_local_repository("FactorValue")
        entity_type = type(entity).__name__.removesuffix("Model")
        rows = repo.get_values_as_of(factor_entity.id, entity.id, when.strftime("%Y-%m-%d %H:%M:%S"), 1,
                                     entity_type=entity_type)
        if not rows:
            return None
        stamp = rows[-1].date.replace(tzinfo=None) if getattr(rows[-1].date, "tzinfo", None) else rows[-1].date
        return rows[-1] if (when - stamp).total_seconds() <= policy["max_age"] else None
