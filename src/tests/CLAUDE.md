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
