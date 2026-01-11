# Sector Local Repository
# Mirrors src/infrastructure/models/sector.py

class SectorLocalRepository:
    """Local repository for sector model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, sector):
        """Save sector to local storage"""
        self.data_store.append(sector)
        
    def find_by_id(self, sector_id):
        """Find sector by ID"""
        for sector in self.data_store:
            if getattr(sector, 'id', None) == sector_id:
                return sector
        return None
        
    def find_all(self):
        """Find all sectors"""
        return self.data_store.copy()