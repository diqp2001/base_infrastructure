"""
Factor return series kept as files (CSV + JSON metadata), and the Kenneth R. French data library importer.

Store layout (``data/factor_returns/``, not committed: downloaded or imported data):
    <name>.csv          date,<FACTOR>,...   decimal returns per period (0.01 = 1 %)
    <name>.json         {"name", "kind", "frequency", "source", "unit": "decimal", "factors", "first", "last",
                         "imported_at", "notes"}

Kenneth R. French data library files are percent returns; they are converted to decimals on import. Only the
period table of the file is read (the annual table and copyright lines that follow are ignored).
"""

from __future__ import annotations

import io
import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "data" / "factor_returns"
FRENCH_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FRENCH_DATASETS: Dict[str, Dict[str, str]] = {
    "ff3_daily": {"file": "F-F_Research_Data_Factors_daily_CSV.zip", "frequency": "D",
                  "label": "Fama/French 3 Factors [Daily]"},
    "ff5_daily": {"file": "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip", "frequency": "D",
                  "label": "Fama/French 5 Factors (2x3) [Daily]"},
}
COLUMN_NAMES = {"Mkt-RF": "MKT_RF", "SMB": "SMB", "HML": "HML", "RMW": "RMW", "CMA": "CMA", "RF": "RF"}


def parse_french_csv(text: str) -> pd.DataFrame:
    """The first table of a French library CSV: header ',Mkt-RF,SMB,...', rows 'YYYYMMDD,...' (or 'YYYYMM'),
    stopping at the first line that is not a data row. Percent -> decimal."""
    lines = text.splitlines()
    header_at = next((i for i, l in enumerate(lines) if l.strip().startswith(",") and "Mkt-RF" in l), None)
    if header_at is None:
        raise ValueError("not a Kenneth R. French factor file (no ',Mkt-RF,...' header)")
    columns = [c.strip() for c in lines[header_at].split(",")[1:]]
    rows = []
    for line in lines[header_at + 1:]:
        parts = [p.strip() for p in line.split(",")]
        if not parts or not re.fullmatch(r"\d{6}|\d{8}", parts[0]):
            break
        rows.append(parts)
    if not rows:
        raise ValueError("the factor file has no data rows")
    fmt = "%Y%m%d" if len(rows[0][0]) == 8 else "%Y%m"
    index = pd.to_datetime([r[0] for r in rows], format=fmt)
    if fmt == "%Y%m":
        index = index + pd.offsets.MonthEnd(0)
    values = pd.DataFrame([[float(x) for x in r[1:len(columns) + 1]] for r in rows], index=index, columns=columns)
    values = values.rename(columns=COLUMN_NAMES) / 100.0
    values.index.name = "date"
    return values


class FactorReturnFileStore:

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root or os.getenv("FACTOR_RETURNS_DIR") or DEFAULT_ROOT)

    def _paths(self, name: str):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name or ""):
            raise ValueError(f"invalid series name '{name}'")
        return self.root / f"{name}.csv", self.root / f"{name}.json"

    def save(self, name: str, frame: pd.DataFrame, kind: str, frequency: str, source: str, notes: str = "") -> Dict:
        frame = frame.sort_index()
        csv, meta_path = self._paths(name)
        self.root.mkdir(parents=True, exist_ok=True)
        frame.to_csv(csv, index_label="date")
        meta = {"name": name, "kind": kind, "frequency": frequency, "source": source, "unit": "decimal",
                "factors": list(frame.columns), "first": str(frame.index.min().date()) if len(frame) else None,
                "last": str(frame.index.max().date()) if len(frame) else None, "rows": int(len(frame)),
                "imported_at": datetime.utcnow().isoformat(timespec="seconds"), "notes": notes}
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return meta

    def load(self, name: str) -> pd.DataFrame:
        csv, _ = self._paths(name)
        if not csv.exists():
            raise LookupError(f"factor return series '{name}' is not imported")
        frame = pd.read_csv(csv, index_col="date", parse_dates=["date"])
        return frame.astype(float)

    def metadata(self, name: str) -> Optional[Dict]:
        _, meta_path = self._paths(name)
        return json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else None

    def list(self) -> List[Dict]:
        if not self.root.exists():
            return []
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(self.root.glob("*.json"))]


class FrenchLibraryImporter:
    """Downloads a daily factor file from the Kenneth R. French data library (HTTP GET, public data)."""

    def __init__(self, store: FactorReturnFileStore, fetch=None):
        self.store = store
        self.fetch = fetch or self._fetch

    @staticmethod
    def _fetch(url: str) -> bytes:
        import requests
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.content

    def import_dataset(self, key: str) -> Dict:
        if key not in FRENCH_DATASETS:
            raise ValueError(f"unknown dataset '{key}' (use {sorted(FRENCH_DATASETS)})")
        spec = FRENCH_DATASETS[key]
        url = FRENCH_BASE + spec["file"]
        with zipfile.ZipFile(io.BytesIO(self.fetch(url))) as z:
            text = z.read(z.namelist()[0]).decode("latin-1")
        frame = parse_french_csv(text)
        return self.store.save(key, frame, kind="external", frequency=spec["frequency"],
                               source=f"Kenneth R. French data library: {spec['label']} ({url})",
                               notes="Percent returns converted to decimals. Published with a lag of about one to "
                                     "two months: recent periods may be missing.")

    def import_csv(self, name: str, text: str, frequency: str = "D", unit: str = "percent") -> Dict:
        """A user CSV: 'date' column (YYYY-MM-DD or YYYYMMDD) + one column per factor; percent or decimal."""
        frame = pd.read_csv(io.StringIO(text))
        if "date" not in [c.lower() for c in frame.columns]:
            raise ValueError("the CSV needs a 'date' column")
        date_col = next(c for c in frame.columns if c.lower() == "date")
        frame[date_col] = pd.to_datetime(frame[date_col].astype(str), format="mixed")
        frame = frame.set_index(date_col).rename(columns=COLUMN_NAMES).astype(float)
        if unit == "percent":
            frame = frame / 100.0
        elif unit != "decimal":
            raise ValueError("unit must be 'percent' or 'decimal'")
        return self.store.save(name, frame, kind="external", frequency=frequency, source="CSV import",
                               notes=f"Imported values were in {unit}.")
