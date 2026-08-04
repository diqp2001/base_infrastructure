Here's a clear and concise CLAUDE.md file for the src/tests/ folder that explains the test structure and guidelines for your base_infrastructure repo.

# CLAUDE.md – Tests Structure and Philosophy

This folder contains all tests for the `base_infrastructure` project. Tests are separated by purpose to support clarity, scalability, and proper software layering.

---

## 🧪 Test Structure Overview

src/tests/
├── unit/ # Unit tests (fast, isolated)
│ ├── domain/ # Test domain logic (pure)
│ ├── application/ # Test use-case logic with mocks
│ └── infrastructure/ # Test database adapters or models
│
├── context/ # Context/integration tests (real workflows)
│ └── project_managers/
│ └── spatiotemporal_momentum_manager/
│
└── init.py


---

## ✅ Unit Tests

- Located under: `tests/unit/`
- Purpose: test **smallest components in isolation**
- Should avoid side effects (e.g., no DB, no file writes)
- Use mocks to simulate dependencies
- Fast and deterministic

Example:
python
def test_momentum_factor_normalization():
    factor = MomentumFactor(values=[1.2, -0.3, 0.5])
    normalized = factor.normalize()
    assert abs(sum(normalized)) < 1e-6

---

## Repository Tests (unit/ and context/)

### Directory layout

```
src/tests/
├── unit/
│   ├── __init__.py
│   ├── test_base_local_repository.py   # BaseLocalRepository CRUD methods
│   └── test_model_repository.py        # ModelRepository domain-level CRUD
├── context/
│   ├── __init__.py
│   └── test_backtest_repository_integration.py  # full-stack FK + cascade tests
```

### What each file covers

| File | Class under test | Scope |
|------|-----------------|-------|
| `unit/test_base_local_repository.py` | `BaseLocalRepository` | Calls base-class methods directly (`add`, `get`, `update`, `delete`, `get_all`, `_get_next_available_id`) using `ModelRepository` as the concrete implementation. Overriding methods in `ModelRepository` are bypassed via `BaseLocalRepository.method(self.repo, ...)`. |
| `unit/test_model_repository.py` | `ModelRepository` | Exercises the domain-level interface: `add(Model)`, `get_by_id`, `get_by_name`, `get_all`, `update(Model)`, `delete(id)`, `_create_or_get`. |
| `context/test_backtest_repository_integration.py` | `ModelRepository` + `BacktestRepository` + `UniverseRepository` | Tests FK integrity (backtest requires a valid model), `get_by_model_id`, and idempotency of `_create_or_get` across repositories. SQLite FK enforcement is enabled via `PRAGMA foreign_keys=ON`. |

### In-memory SQLite pattern

All repository tests follow this setUp/tearDown pattern — no external database required:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.models import ModelBase
# Import backtest ORM models explicitly — they are NOT in models/__init__.py
from src.infrastructure.models.backtest.model import ModelModel
from src.infrastructure.models.backtest.backtest import BacktestModel

class TestFoo(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")          # fresh in-memory DB
        ModelBase.metadata.create_all(self.engine)        # create all tables
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.repo = ModelRepository(self.session)

    def tearDown(self):
        self.session.rollback()
        self.session.close()
        self.engine.dispose()                             # destroys the in-memory DB
```

Key points:
- `from src.infrastructure.models import ModelBase` must come first; it imports all
  shared models (FactorModel etc.) so FK targets are registered before backtest models.
- Backtest ORM models (`ModelModel`, `BacktestModel`, `UniverseModel`,
  `BacktestFactorBacktestModel`) are NOT imported by `models/__init__.py` and must
  be imported explicitly so their tables appear in `ModelBase.metadata`.
- Each test method gets a completely fresh engine → fresh database → no cross-test state.

### Running tests

```bash
# All tests
python -m unittest discover tests

# Single file (from project root)
python -m unittest src.tests.unit.test_base_local_repository
python -m unittest src.tests.unit.test_model_repository
python -m unittest src.tests.context.test_backtest_repository_integration

# All unit or context tests
python -m unittest discover src/tests/unit
python -m unittest discover src/tests/context
```
