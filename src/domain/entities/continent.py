from typing import Optional, List

class Continent:
    """
    Domain entity for a Continent.
    Represents a high-level geographical and political region.
    """

    def __init__(self, id: int, name: str):
        """
        Initialize a Continent entity.
        
        :param id: Unique identifier for the continent.
        :param name: Name of the continent (e.g., 'Asia', 'Europe').
        :param abbreviation: Optional abbreviation for the continent (e.g., 'AS', 'EU').
        """
        self.id = id
        self.name = name

   
    def __repr__(self) -> str:
        return f"Continent(id={self.id}, name='{self.name}')"
