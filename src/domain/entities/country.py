# src/domain/entities/country.py
from typing import List

class Country:
    def __init__(self, id: int,name: str,  continent_id: int):
        """
        Initialize a Country object with essential details.
        
        """
        self.id = id
        self.name = name
        self.continent_id = continent_id

    

    def __repr__(self):
        return f"Country({self.name})"
