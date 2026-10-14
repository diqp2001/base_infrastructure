"""
Architecture rules, enforced on every run.

- The import-linter contracts in pyproject.toml hold (dependency direction between layers).
- No NEW import cycle between sibling packages (existing ones are a committed baseline).
- Every source directory is a regular package: grimp / import-linter skip namespace packages,
  and imports into them collapse to `src` — rules would silently stop seeing that code.
"""

import keyword
import os
import subprocess
import sys
import unittest

from tests.architecture.import_cycles import BASELINE, ROOT, current_cycles, load_baseline


class LayerContractsTest(unittest.TestCase):

    def test_import_linter_contracts_hold(self):
        env = {**os.environ, "PYTHONPATH": ROOT}
        run = subprocess.run(
            [sys.executable, "-c", "from importlinter.cli import lint_imports; raise SystemExit(lint_imports(no_cache=True))"],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=600,
        )
        output = run.stdout + run.stderr
        self.assertEqual(run.returncode, 0, f"import-linter contracts broken:\n{output[-6000:]}")
        self.assertIn("0 broken", output)


class ImportCyclesTest(unittest.TestCase):

    def test_no_new_import_cycles(self):
        current, baseline = current_cycles(), load_baseline()
        new = []
        for package, groups in current.items():
            known = [set(g) for g in baseline.get(package, [])]
            for group in groups:
                if not any(set(group) <= k for k in known):
                    new.append(f"{package}: {group}")
        self.assertEqual(new, [], "new import cycle(s) between sibling packages — remove the import "
                                  "that closes the cycle (see python -m tests.architecture.import_cycles)")

    def test_baseline_is_not_stale(self):
        """A removed cycle must be removed from the baseline too (so it cannot come back unnoticed)."""
        current, baseline = current_cycles(), load_baseline()
        stale = []
        for package, groups in baseline.items():
            now = [set(g) for g in current.get(package, [])]
            for group in groups:
                if set(group) not in now:
                    stale.append(f"{package}: {group}")
        self.assertEqual(stale, [], f"cycles fixed or shrunk — regenerate {os.path.basename(BASELINE)} with "
                                    f"python -m tests.architecture.import_cycles --update")


class PackageLayoutTest(unittest.TestCase):

    def test_every_source_directory_is_a_package(self):
        missing = []
        for dirpath, dirnames, files in os.walk(os.path.join(ROOT, "src")):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            parts = os.path.relpath(dirpath, ROOT).split(os.sep)
            if not all(p.isidentifier() and not keyword.iskeyword(p) for p in parts):
                continue
            if any(f.endswith(".py") for f in files) and "__init__.py" not in files:
                missing.append(os.path.relpath(dirpath, ROOT))
        self.assertEqual(missing, [], "directories with modules but no __init__.py (invisible to the "
                                      "architecture checks)")


if __name__ == "__main__":
    unittest.main()
