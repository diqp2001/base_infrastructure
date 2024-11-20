
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
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
        
        '''# Ensure all models are registered
        
        company = relationship("Company", back_populates="company_stocks")
        exchange = relationship("Exchange", back_populates="company_stocks")
        
        stock = relationship("Stock", back_populates="market_information")
        
        exchange = relationship("Exchange", back_populates="stocks")
        
        country = relationship("Country", back_populates="companies")
        industry = relationship("Industry", back_populates="companies")
        industry = relationship("CompanyStock", back_populates="companies")

        country = relationship("Country", back_populates="exchanges")
        stock = relationship("Stock", back_populates="exchanges")
        company_stock = relationship("CompanyStock", back_populates="exchanges")
        
        companies = relationship("Company", back_populates="country")
        exchanges = relationship("Exchange", back_populates="country")


        # Relationship to companies
        companies = relationship("Company", back_populates="industry")
        
        # Relationship to Sector (assuming a Sector model exists)
        sector = relationship("Sector", back_populates="industries")
'''


        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.SessionLocal = SessionLocal()
        self.Base.metadata.create_all(bind=self.engine)

    def initialize_database_and_create_all_tables(self):
        self.Base.metadata.create_all(bind=self.engine)
        

    def drop_all_tables(self):
        self.Base.metadata.drop_all(self.engine)
        self.SessionLocal.commit()

    
