from sqlalchemy import Column, Date, Integer, String, Text
from src.infrastructure.models import ModelBase as Base


class UniverseModel(Base):
    __tablename__ = 'universes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    creation_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Universe(id={self.id}, name='{self.name}')>"
