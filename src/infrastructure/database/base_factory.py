
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
                    with self.engine.connect() as conn:
                        conn.execute(text(
                            "ALTER TABLE factor_values ADD COLUMN currency_id INTEGER"
                        ))
                        conn.commit()
                    print("Migrated: added currency_id to factor_values")
        except Exception as e:
            print(f"Schema migration warning: {e}")

    def initialize_database_and_create_all_tables(self):
        self.Base.metadata.create_all(bind=self.engine)
        

    def drop_all_tables(self):
        self.Base.metadata.drop_all(self.engine)
        self.SessionLocal.commit()

    
