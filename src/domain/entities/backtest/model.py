from typing import Optional
from src.domain.entities.entity import Entity


class Model(Entity):
    def __init__(self, id: Optional[int], name: str):
        super().__init__(id)
        self.name = name

    def __repr__(self):
        return f"Model(id={self.id}, name='{self.name}')"
