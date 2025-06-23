# CLAUDE.md

## 🧠 Contributor Logic, Architecture, and Unified Development Essentials

Welcome to the `base_infrastructure` project! This guide outlines key conventions and architectural decisions to ensure all contributors align with the vision and structure of the codebase.

---

## 1. 🔧 Project Structure (DDD-Oriented)

We use **Domain-Driven Design (DDD)** principles to separate concerns:

src/
├── domain/ # Core business logic (independent of frameworks)
│ ├── entities/ # Pure domain models (no SQLAlchemy)
│ └── ports/ # Interfaces for repository/service contracts
├── infrastructure/
│ ├── models/ # ORM models (SQLAlchemy)
│ └── repositories/ # Concrete implementations of domain ports
├── application/
│ └── services/ # Use cases, orchestrating domain and infra
tests/


---

## 2. 📏 Code Conventions

- **Language**: Python 3.11+
- **ORM**: SQLAlchemy (v2-style)
- **Testing**: `unittest` with `test_*.py` naming in `/tests`
- **Imports**: Use absolute imports within `src/`

> ✨ Tip: Run `python -m unittest discover tests` to execute all tests.

---

## 3. ✅ Contribution Guidelines

- Fork and branch from `main`
- Follow feature/bugfix branch naming:

- Keep PRs under ~300 lines when possible
- Include/modify relevant unit tests
- Keep domain logic pure: no SQLAlchemy in `domain/`

---

## 4. 🧪 Testing Philosophy

- Domain logic: tested in isolation (no DB)
- Infrastructure: tested using mocks or local SQLite
- Use `@dataclass` for entities when appropriate

---

## 5. 📦 Virtual Environment Setup

"""
bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
"""
