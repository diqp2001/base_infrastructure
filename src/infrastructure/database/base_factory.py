
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
from src.infrastructure.database.settings import get_database_url
from src.infrastructure.models import ModelBase as Base



class BaseFactory:
    """
    Factory for creating independent Base classes and sessionmakers for multiple projects.
    """
    def __init__(self, db_type: str):
        database_url = get_database_url(db_type)
        self.engine = create_engine(database_url)
        self.Base = Base
        
        

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.SessionLocal = SessionLocal()
        self.Base.metadata.create_all(bind=self.engine)
        self._migrate_schema()
        self.SessionLocal.commit()
        for table in self.Base.metadata.tables:
            print(f'Table in metadata {table}')

    def _migrate_schema(self):
        """Add columns to existing tables that create_all cannot alter."""
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()

            if 'factor_values' in existing_tables:
                existing_cols = {c['name'] for c in inspector.get_columns('factor_values')}
                if 'currency_id' not in existing_cols:
                    dialect = self.engine.dialect.name
                    if dialect == 'sqlite':
                        sql = "ALTER TABLE factor_values ADD COLUMN currency_id INTEGER"
                    else:
                        sql = "ALTER TABLE factor_values ADD currency_id INTEGER NULL"
                    with self.engine.connect() as conn:
                        conn.execute(text(sql))
                        conn.commit()
                    print("Migrated: added currency_id to factor_values")

                # unique (factor_id, entity_id, entity_type, date): created only when no duplicates exist
                from src.infrastructure.database.factor_value_dedup import ensure_unique_key
                report = ensure_unique_key(self.engine)
                if report.index_created:
                    print("Migrated: unique index on factor_values (factor_id, entity_id, entity_type, date)")
                elif not report.index_existed:
                    print(f"Schema migration warning: {report.summary()}\n  -> run "
                          f"'python -m src.infrastructure.database.factor_value_dedup' (dry run, then --apply)")
                if 'value_numeric' not in existing_cols:          # numeric copy of value (schema change approved)
                    self._add_value_numeric()
            if 'positions' in existing_tables:
                quantity = next((c for c in inspector.get_columns('positions') if c['name'] == 'quantity'), None)
                if quantity is not None and self.engine.dialect.name != 'sqlite'                         and 'INT' in str(quantity['type']).upper():
                    with self.engine.begin() as conn:            # cash keeps cents (schema change approved)
                        conn.execute(text("ALTER TABLE positions ALTER COLUMN quantity DECIMAL(18, 4) NOT NULL"))
                    print("Migrated: positions.quantity INTEGER -> DECIMAL(18, 4)")
            if 'factor_value_provenance' in existing_tables:
                provenance_cols = {c['name'] for c in inspector.get_columns('factor_value_provenance')}
                if 'selection' not in provenance_cols:          # BI-026 column on a BI-025 table
                    sql = ("ALTER TABLE factor_value_provenance ADD COLUMN selection VARCHAR(255)"
                           if self.engine.dialect.name == 'sqlite'
                           else "ALTER TABLE factor_value_provenance ADD selection VARCHAR(255) NULL")
                    with self.engine.connect() as conn:
                        conn.execute(text(sql))
                        conn.commit()
                    print("Migrated: added selection to factor_value_provenance")
        except Exception as e:
            print(f"Schema migration warning: {e}")

    def _add_value_numeric(self):
        """Add factor_values.value_numeric and backfill it from the string value (unparsable -> NULL)."""
        sqlite = self.engine.dialect.name == 'sqlite'
        with self.engine.begin() as conn:
            conn.execute(text("ALTER TABLE factor_values ADD COLUMN value_numeric FLOAT" if sqlite
                              else "ALTER TABLE factor_values ADD value_numeric FLOAT NULL"))
        with self.engine.begin() as conn:
            if sqlite:
                conn.execute(text("UPDATE factor_values SET value_numeric = CAST(value AS REAL) "
                                  "WHERE trim(value) GLOB '*[0-9]*' AND CAST(value AS REAL) || '' <> ''"))
            else:
                conn.execute(text("UPDATE factor_values SET value_numeric = TRY_CAST(value AS FLOAT) "
                                  "WHERE value_numeric IS NULL"))
        print("Migrated: added factor_values.value_numeric (backfilled from value)")

    def initialize_database_and_create_all_tables(self):
        self.Base.metadata.create_all(bind=self.engine)
        

    def drop_all_tables(self):
        self.Base.metadata.drop_all(self.engine)
        self.SessionLocal.commit()

    
