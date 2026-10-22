"""
STM report store — final results of the latest run, on disk, so any process
(the Flask dashboard) can show them after the run that produced them ended.

  <results_dir>/progress.json   live progress (STMProgressTracker persist_path)
  <results_dir>/report.pkl      STMResearchReport (tables, series, SHAP arrays)
  <results_dir>/report.pdf      the rendered PDF
"""

from __future__ import annotations

import os
import pickle
from typing import Optional

PROGRESS_FILE = "progress.json"
REPORT_FILE = "report.pkl"
PDF_FILE = "report.pdf"


def progress_path(results_dir: str) -> str:
    return os.path.join(results_dir, PROGRESS_FILE)


def save_report(report, results_dir: str, render_pdf: bool = True, pdf_builder=None) -> None:
    """Write the report (and its PDF) atomically; the previous run's files are replaced.
    ``pdf_builder(report) -> bytes`` renders the PDF (default: the STM renderer)."""
    os.makedirs(results_dir, exist_ok=True)
    tmp = os.path.join(results_dir, REPORT_FILE + ".tmp")
    with open(tmp, "wb") as f:
        pickle.dump(report, f)
    os.replace(tmp, os.path.join(results_dir, REPORT_FILE))
    if render_pdf:
        if pdf_builder is None:
            from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_report_renderer import (
                build_pdf as pdf_builder,
            )
        tmp_pdf = os.path.join(results_dir, PDF_FILE + ".tmp")
        with open(tmp_pdf, "wb") as f:
            f.write(pdf_builder(report))
        os.replace(tmp_pdf, os.path.join(results_dir, PDF_FILE))


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
