# Continent Local Repository
# Mirrors src/infrastructure/models/continent.py

class ContinentLocalRepository:
    """Local repository for continent model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, continent):
        """Save continent to local storage"""
        self.data_store.append(continent)
        
    def find_by_id(self, continent_id):
        """Find continent by ID"""
        for continent in self.data_store:
            if getattr(continent, 'id', None) == continent_id:
                return continent
        return None
        
    def find_all(self):
        """Find all continents"""
        return self.data_store.copy()