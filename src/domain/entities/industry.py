from typing import Optional
from src.domain.entities.entity import Entity
from src.domain.entities.sector import Sector


class Industry(Entity):
    def __init__(self, id: Optional[int], name: str, sector_id: int, description: str = ""):
        super().__init__(id)
        self.name = name
        self.sector_id = sector_id
        self.description = description

    def __repr__(self):
        return f"Industry(id={self.id}, name={self.name}, sector_id={self.sector_id}, description={self.description})"
