
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.database.settings import get_database_url
from src.infrastructure.models import *  # Import all models to register with Base.metadata
Base = declarative_base()
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
        # Ensure all models are registered
        import src.infrastructure.models  # Import here to ensure registration
        self.Base.metadata.create_all(bind=self.engine)

    def initialize_database_and_create_all_tables(self):
        self.Base.metadata.create_all(bind=self.engine)
        

    def drop_all_tables(self):
        self.Base.metadata.drop_all(self.engine)
        self.SessionLocal.commit()

    
