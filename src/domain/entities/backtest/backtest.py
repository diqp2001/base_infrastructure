from datetime import date
from typing import Optional
from src.domain.entities.entity import Entity


class Backtest(Entity):
    def __init__(self, id: Optional[int], name: str, model_id: int, creation_date: date):
        super().__init__(id)
        self.name = name
        self.model_id = model_id
        self.creation_date = creation_date

    def __repr__(self):
        return f"Backtest(id={self.id}, name='{self.name}', model_id={self.model_id})"
