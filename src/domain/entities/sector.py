from typing import List

class Sector:
    def __init__(self, id: int, name: str, description: str = ""):
        """
        Initialize a Sector object with essential details.

        :param id: The unique identifier for the sector.
        :param name: The name of the sector (e.g., 'Information Technology', 'Healthcare').
        :param description: A short description of the sector (optional).
        """
        self.id = id
        self.name = name
        self.description = description

  
    def get_sector_info(self):
        """
        Returns a summary of the sector.
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }

    def __repr__(self):
        return f"Sector(id={self.id}, name={self.name}, description={self.description})"
