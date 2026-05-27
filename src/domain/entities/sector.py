from typing import Optional
from src.domain.entities.entity import Entity


class Sector(Entity):
    def __init__(self, id: Optional[int], name: str, description: str = ""):
        super().__init__(id)
        self.name = name
        self.description = description

    def get_sector_info(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }

    def __repr__(self):
        return f"Sector(id={self.id}, name={self.name}, description={self.description})"
