from typing import Optional
from src.domain.entities.entity import Entity
from src.domain.entities.country import Country


class Exchange(Entity):
    def __init__(self, id: Optional[int], name: str, legal_name: str,
                 country_id: int, start_date, end_date=None):
        super().__init__(id)
        self.name = name
        self.legal_name = legal_name
        self.country_id = country_id
        self.start_date = start_date
        self.end_date = end_date

    def __repr__(self):
        return f"Exchange({self.name})"
