# src/domain/entities/country.py
from typing import List

from src.domain.entities.continent import Continent

class Country:
    def __init__(self, id: int,name: str,iso_code:str,  continent_id: int):
        """
        Initialize a Country object with essential details.
        
        """
        self.id = id
        self.name = name
        self.iso_code = iso_code
        self.continent_id = continent_id

    

    def __repr__(self):
        return f"Country({self.name})"
