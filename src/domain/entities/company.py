# src/domain/entities/company.py

from sqlalchemy import Column, Integer, String
from src.infrastructure.database.base import Base

class Company(Base):
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
