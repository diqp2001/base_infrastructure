# Country Local Repository
# Mirrors src/infrastructure/models/country.py

class CountryRepository:
    """Local repository for country model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, country):
        """Save country to local storage"""
        self.data_store.append(country)
        
    def find_by_id(self, country_id):
        """Find country by ID"""
        for country in self.data_store:
            if getattr(country, 'id', None) == country_id:
                return country
        return None
        
    def find_all(self):
        """Find all countries"""
        return self.data_store.copy()