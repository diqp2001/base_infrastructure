from typing import Optional
from src.domain.entities.entity import Entity


class Continent(Entity):
    """
    Domain entity for a Continent.
    Represents a high-level geographical and political region.
    """

    def __init__(self, id: Optional[int], name: str):
        super().__init__(id)
        self.name = name

    def __repr__(self) -> str:
        return f"Continent(id={self.id}, name='{self.name}')"
