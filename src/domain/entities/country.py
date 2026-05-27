from typing import Optional
from src.domain.entities.entity import Entity
from src.domain.entities.continent import Continent


class Country(Entity):
    def __init__(self, id: Optional[int], name: str, iso_code: str, continent_id: int):
        super().__init__(id)
        self.name = name
        self.iso_code = iso_code
        self.continent_id = continent_id

    def __repr__(self):
        return f"Country({self.name})"
