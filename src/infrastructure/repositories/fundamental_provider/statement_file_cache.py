"""
A file cache in front of a FinancialStatementSourcePort: one JSON file per (symbol, frequency) of a statement, so a
research run over hundreds of companies asks the provider once (later runs read the files). Nothing goes to the
database. The cached records are the provider's StatementRecords unchanged (point-in-time stamps included).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import date, datetime
from typing import List

from src.domain.ports.factor.financial_statement_source_port import FinancialStatementSourcePort, StatementRecord


def _encode(record: StatementRecord) -> dict:
    d = asdict(record)
    for k in ("period_end", "filing_date", "accepted_at", "available_by"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    return d


def _decode(d: dict) -> StatementRecord:
    d = dict(d)
    d["period_end"] = date.fromisoformat(d["period_end"])
    d["filing_date"] = date.fromisoformat(d["filing_date"]) if d.get("filing_date") else None
    d["accepted_at"] = datetime.fromisoformat(d["accepted_at"]) if d.get("accepted_at") else None
    d["available_by"] = datetime.fromisoformat(d["available_by"]) if d.get("available_by") else None
    return StatementRecord(**d)


class FileCachedStatementSource(FinancialStatementSourcePort):

    def __init__(self, source: FinancialStatementSourcePort, folder: str):
        self.source = source
        self.folder = folder
        self.STATEMENT = getattr(source, "STATEMENT", None)
        self.FREQUENCIES = tuple(getattr(source, "FREQUENCIES", ()))

    def _path(self, symbol: str, frequency: str) -> str:
        safe = symbol.replace("/", "_").replace(" ", "_")
        return os.path.join(self.folder, str(self.STATEMENT), frequency, f"{safe}.json")

    def fetch(self, symbol: str, frequency: str) -> List[StatementRecord]:
        path = self._path(symbol, frequency)
        try:
            with open(path, encoding="utf-8") as f:
                return [_decode(r) for r in json.load(f)]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        records = self.source.fetch(symbol, frequency)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([_encode(r) for r in records], f)
        return records

    def __getattr__(self, name):                 # anything else the provider exposes (e.g. errors)
        return getattr(self.source, name)
