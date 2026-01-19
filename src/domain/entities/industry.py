# src/domain/entities/industry.py
from typing import List

from src.domain.entities.sector import Sector

class Industry:
    def __init__(self, id: int, name: str, sector_id: int, description: str = ""):
        """
        Initialize an Industry object with essential details.
        
        :param id: The unique identifier for the industry.
        :param name: The name of the industry (e.g., 'Technology', 'Finance')
        :param sector_id: The broader sector the industry belongs to (e.g., 'Information Technology', 'Financials')
        :param description: A short description of the industry (optional).
        :param key_metrics: Key performance indicators relevant to the industry (e.g., ['Market Cap', 'Revenue Growth'])
        """
        self.id = id
        self.name = name
        self.sector_id = sector_id
        self.description = description
        

    

    

    

    def __repr__(self):
        return f"Industry(id={self.id}, name={self.name}, sector_id={self.sector_id}, description={self.description})"
