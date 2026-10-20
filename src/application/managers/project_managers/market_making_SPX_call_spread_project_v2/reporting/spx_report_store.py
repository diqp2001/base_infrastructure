"""
SPX v2 report store — the latest run's report on disk, so any process (the Flask dashboard) can show it
after the run that produced it ended. Same files as the Spatio-Temporal Momentum projects:

  <results_dir>/progress.json     live progress (MMProgressTracker persist_path)
  <results_dir>/results.json      the run summary (project manager)
  <results_dir>/data_report.txt   missing data and why
  <results_dir>/report.pkl        SPXReport (tables and series)
  <results_dir>/report.pdf        the rendered PDF

Rebuild the report of the last run from its files (no new backtest):

    python -m src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.reporting.spx_report_store
"""

from __future__ import annotations

import json
import os
import pickle
from typing import Optional

PROGRESS_FILE = "progress.json"
RESULTS_FILE = "results.json"
DATA_REPORT_FILE = "data_report.txt"
REPORT_FILE = "report.pkl"
PDF_FILE = "report.pdf"


def progress_path(results_dir: str) -> str:
    return os.path.join(results_dir, PROGRESS_FILE)


def save_report(report, results_dir: str, render_pdf: bool = True) -> None:
    """Write the report (and its PDF) atomically; the previous run's files are replaced."""
    os.makedirs(results_dir, exist_ok=True)
    tmp = os.path.join(results_dir, f"{REPORT_FILE}.{os.getpid()}.tmp")
    with open(tmp, "wb") as f:
        pickle.dump(report, f)
    os.replace(tmp, os.path.join(results_dir, REPORT_FILE))
    if render_pdf:
        from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.reporting.spx_report_renderer import (
            build_pdf,
        )
        tmp_pdf = os.path.join(results_dir, f"{PDF_FILE}.{os.getpid()}.tmp")
        with open(tmp_pdf, "wb") as f:
            f.write(build_pdf(report))
        os.replace(tmp_pdf, os.path.join(results_dir, PDF_FILE))


def build_from_files(results_dir: str):
    """SPXReport of the run stored in results_dir (results.json + data_report.txt), or None."""
    from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.reporting.spx_report import (
        build_report,
    )
    path = os.path.join(results_dir, RESULTS_FILE)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        summary = json.load(f)
    data_path = os.path.join(results_dir, DATA_REPORT_FILE)
    text = open(data_path, encoding="utf-8").read() if os.path.exists(data_path) else None
    return build_report(summary, text)


def report_mtime(results_dir: str) -> Optional[float]:
    path = os.path.join(results_dir, REPORT_FILE)
    return os.path.getmtime(path) if os.path.exists(path) else None


def load_report(results_dir: str):
    path = os.path.join(results_dir, REPORT_FILE)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def pdf_path(results_dir: str) -> Optional[str]:
    path = os.path.join(results_dir, PDF_FILE)
    return path if os.path.exists(path) else None


if __name__ == "__main__":
    from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2 import config

    directory = config.get_config()["results_dir"]
    report = build_from_files(directory)
    if report is None:
        raise SystemExit(f"No run results in {directory}")
    save_report(report, directory)
    print(f"Report written: {os.path.join(directory, PDF_FILE)}")
