"""
Lint ratchet (BI-003): no NEW ruff findings.

The rules are in pyproject.toml [tool.ruff.lint] (pyflakes F + syntax errors E9). The findings that existed when
the gate was introduced are recorded per rule in ruff_baseline.json. This test fails when any rule has more
findings than its baseline (a new violation), and when a rule has fewer (fixed findings: lower the baseline in
the same change so the ratchet keeps the gain). Never raise a baseline to make a change pass.

    python -m ruff check src tests --select F821        # e.g. list the undefined names
"""

import collections
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASELINE = pathlib.Path(__file__).with_name("ruff_baseline.json")


def current_counts():
    try:
        import ruff  # noqa: F401  (dev dependency, requirements-dev.txt)
    except ImportError:
        pytest.fail("ruff is not installed: pip install -r requirements-dev.txt")
    result = subprocess.run([sys.executable, "-m", "ruff", "check", "src", "tests", "--output-format", "json",
                             "--no-cache", "--exit-zero"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    return collections.Counter(item["code"] for item in json.loads(result.stdout))


@pytest.fixture(scope="module")
def counts():
    return current_counts()


@pytest.fixture(scope="module")
def baseline():
    return json.loads(BASELINE.read_text(encoding="utf-8"))["counts"]


def test_no_new_lint_findings(counts, baseline):
    grown = {code: f"{baseline.get(code, 0)} -> {n}" for code, n in counts.items() if n > baseline.get(code, 0)}
    assert grown == {}, (f"new ruff findings (rule: baseline -> now): {grown}. Fix them; list them with "
                         f"`python -m ruff check src tests --select {','.join(sorted(grown))}`")


def test_baseline_is_lowered_when_findings_are_fixed(counts, baseline):
    shrunk = {code: f"{n} -> {counts.get(code, 0)}" for code, n in baseline.items() if counts.get(code, 0) < n}
    assert shrunk == {}, (f"findings fixed (rule: baseline -> now): {shrunk}. Lower those counts in "
                          f"{BASELINE.name} so the gain is kept")
