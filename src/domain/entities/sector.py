from typing import List

class Sector:
    def __init__(self, name: str, description: str = "", sector_id: int = "",):
        """
        Initialize a Sector object with essential details.

        :param name: The name of the sector (e.g., 'Information Technology', 'Healthcare').
        :param description: A short description of the sector (optional).
        :param industries: List of Industry IDs belonging to the sector.
        """
        self.name = name
        self.description = description
        self.sector_id = sector_id

  
    def get_sector_info(self):
        """
        Returns a summary of the sector.
        """
        return {
            'name': self.name,
            'description': self.description,
            'sector_id': self.sector_id
        }

    def __repr__(self):
        return f"Sector({self.name}, {self.description}, {self.sector_id})"
