"""
StatementFactorValueRepository - ONE implementation, for every provider, of "company financial statements as factor
values" (FactorValueProviderPort). A provider only supplies its statements in canonical form
(FinancialStatementSourcePort -> StatementRecord); storage, point in time and the resolver hook are shared:

    provider statements (FMP, Eulerpool, ...) -> StatementRecord -> raw CompanyShareFactor series (group
    'fundamental', subgroup = statement, frequency 1q | 1y, source = the provider's key, name = the canonical field)
    -> factor values stamped at StatementRecord.available_at -> local FactorValueRepository (add_bulk: a stored value
    is kept, never overwritten)

FactorValueResolutionService calls fetch_factor_value for a raw series of this provider's source with no value known
at the decision time: the statement's whole history at that frequency is loaded once per (share, statement,
frequency) and session, then the value is read as of the decision time (Factor.point_in_time_policy) - a statement
published after the decision time is never returned.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, Iterable, List, Mapping, Optional, Tuple, Type

from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_factor import (
    ANNUAL, GROUP, METADATA_FIELDS, QUARTERLY,
)
from src.domain.ports.factor.factor_value_provider_port import FactorValueProviderPort
from src.domain.ports.factor.financial_statement_source_port import FinancialStatementSourcePort, StatementRecord

logger = logging.getLogger(__name__)

FREQUENCY_LABEL = {QUARTERLY: "quarterly", ANNUAL: "annual"}
SHARE_COUNT_FIELDS = frozenset({"weightedAverageShsOut", "weightedAverageShsOutDil",
                                "commonStockSharesOutstanding"})   # not amounts


class StatementFactorValueRepository(FactorValueProviderPort):
    """Stores a provider's financial statements as raw fundamental factor values and serves them as of a decision
    time. ``source`` = the provider's Factor.SOURCES key; ``statements`` = {statement: FinancialStatementSourcePort};
    ``errors`` = the provider's request errors (logged, nothing stored)."""

    def __init__(self, source: str, label: str, statements: Mapping[str, FinancialStatementSourcePort],
                 factory=None, errors: Tuple[Type[BaseException], ...] = ()):
        self.source = source
        self.label = label
        self.statements = dict(statements)
        self.factory = factory
        self.errors = tuple(errors)
        self._loaded: Dict[Tuple[int, str, str], int] = {}     # (entity id, statement, frequency) -> values stored
        self._factors: Dict[Tuple[str, str, str], CompanyShareFactor] = {}
        self._currencies: Dict[str, Optional[int]] = {}

    @staticmethod
    def symbol_of(entity) -> Optional[str]:
        """The provider's identifier of a share entity: its ticker."""
        symbol = getattr(entity, "symbol", None) or getattr(entity, "ticker", None)
        return str(symbol).strip().upper() if symbol else None

    def serves(self, statement: Optional[str], frequency: Optional[str]) -> bool:
        source = self.statements.get(statement)
        return source is not None and frequency in getattr(source, "FREQUENCIES", ())

    # -- raw series --
    def raw_factor(self, statement: str, frequency: str, name: str) -> Optional[CompanyShareFactor]:
        """The raw series of one canonical field from this provider (created on first use)."""
        key = (statement, frequency, name)
        if key not in self._factors:
            repo = self.factory.get_local_repository("CompanyShareFactor")
            factor = repo._create_or_get(
                CompanyShareFactor, name, group=GROUP, subgroup=statement, frequency=frequency,
                data_type=METADATA_FIELDS.get(name, "numeric"), source=self.source,
                definition=f"{self.label} {statement.replace('_', ' ')} ({FREQUENCY_LABEL[frequency]}): {name}")
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
                logger.warning(f"{self.label}: reported currency {iso_code} is not a stored Currency - its values "
                               f"keep the share's currency id; the 'reportedCurrency' series has the reported one")
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
        if not symbol or not self.serves(statement, frequency):
            return 0
        try:
            records = self.statements[statement].fetch(symbol, frequency)
        except self.errors as e:
            logger.error(f"{self.label} {statement} {frequency} {symbol}: {e}")
            self._loaded[key] = 0           # not asked again in this session: the answer would be the same
            return 0
        stored = self.store(entity, records)
        self._loaded[key] = stored
        logger.info(f"{self.label} {statement} {frequency} {symbol}: {len(records)} periods, {stored} values stored")
        return stored

    def load_company(self, entity, statements: Optional[Iterable[str]] = None,
                     frequencies: Iterable[str] = (QUARTERLY, ANNUAL)) -> Dict[str, int]:
        """Every statement at every frequency for one share: {'<statement> <frequency>': values stored}."""
        return {f"{s} {f}": self.load_statements(entity, s, f)
                for s in (statements or self.statements) for f in frequencies if self.serves(s, f)}

    # -- the resolution service's provider hook --
    def fetch_factor_value(self, factor_entity, entity, time_date, **kwargs) -> Optional[FactorValue]:
        """FactorValueProviderPort: the value of one of this provider's raw statement series known at time_date,
        loading the statement first when needed. Any other series -> None."""
        if (entity is None or getattr(factor_entity, "source", None) != self.source
                or getattr(factor_entity, "group", None) != GROUP):
            return None
        statement, frequency = getattr(factor_entity, "subgroup", None), getattr(factor_entity, "frequency", None)
        if not self.serves(statement, frequency):
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
