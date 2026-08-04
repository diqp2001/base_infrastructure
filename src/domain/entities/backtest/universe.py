from datetime import date
from typing import Optional
from src.domain.entities.entity import Entity


class Universe(Entity):
    def __init__(self, id: Optional[int], name: str, creation_date: date, description: Optional[str] = None):
        super().__init__(id)
        self.name = name
        self.creation_date = creation_date
        self.description = description

    def __repr__(self):
        return f"Universe(id={self.id}, name='{self.name}')"
