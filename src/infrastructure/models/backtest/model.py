from sqlalchemy import Column, Integer, String
from src.infrastructure.models import ModelBase as Base


class ModelModel(Base):
    __tablename__ = 'models'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)

    def __repr__(self):
        return f"<Model(id={self.id}, name='{self.name}')>"
