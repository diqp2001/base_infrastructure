from typing import List

class Sector:
    def __init__(self, name: str, description: str = "", ):
        """
        Initialize a Sector object with essential details.

        :param name: The name of the sector (e.g., 'Information Technology', 'Healthcare').
        :param description: A short description of the sector (optional).
        :param industries: List of Industry IDs belonging to the sector.
        """
        self.name = name
        self.description = description

  
    def get_sector_info(self):
        """
        Returns a summary of the sector.
        """
        return {
            'name': self.name,
            'description': self.description
        }

    def __repr__(self):
        return f"Sector({self.name}, {self.description})"
