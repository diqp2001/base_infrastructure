""" 
base_infra/
│
├── venv/                    # Virtual environment folder
│
├── .vscode/                 # VSCode configuration folder
│   └── launch.json          # JSON file to configure VSCode launch options
│
├── tests/                   # Unit tests folder
│   ├── __init__.py
│   └── test_*.py            # All unit test files prefixed with 'test_'
│
├── config.json              # JSON configuration file for application settings
│
├── .git/                    # Git repository folder (if initialized)
│
└── src/                     # Main source code folder
    ├── application/         # Application layer for business logic
    ├── infrastructure/      # Infrastructure layer for external systems or dependencies
    └── domain/              # Domain layer encapsulating core business logic



Detailed Infrastructure
src/
│
├── application/             # Application layer for business logic
│   └── services/            # Contains service classes or modules that coordinate domain operations
│
├── infrastructure/          # Infrastructure layer for external systems or dependencies
│   ├── models/              # Database or persistence models (e.g., SQLAlchemy models)
│   └── repositories/        # Repository implementations for data access
│
├── domain/                  # Domain layer encapsulating core business logic
│   ├── entities/            # Core domain entities (like Stock, Bond, Company)
│   └── ports/               # Interfaces or abstract classes for repositories, services, etc.


src/
└── infrastructure/
    ├── database/
    │   ├── base.py                # Base classes for SQLAlchemy
    │   ├── settings.py            # Database connection settings, environment variables, etc.
    │   ├── connections.py         # Logic for establishing database connections
    │   ├── initializer.py         # Database setup and initialization code
    │   ├── sqlite_utilities.py    # SQLite-specific utilities
    │   └── sql_server_utilities.py # SQL Server-specific utilities
    ├── models/                    # Contains SQLAlchemy models
    │   ├── __init__.py            # To make models a package
    │   ├── stock.py               # Stock model
    │   ├── bond.py                # Bond model
    │   └── company.py             # Company model
    └── repositories/              # Contains repository classes for interacting with the models

Key Takeaways:
domain/entities/financial_assets contains the pure business logic and domain models that don't have database-related code. It represents the conceptual idea of financial assets, stocks, bonds, etc.

infrastructure/models/financial_assets contains the SQLAlchemy models that are tied to the database and define the schema. These are the "data structures" that get stored in the database.

infrastructure/repositories/financial_assets contains the data access logic, where you interact with the database (e.g., querying, saving, or updating records).
""" 
