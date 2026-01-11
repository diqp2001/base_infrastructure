# Industry Local Repository
# Mirrors src/infrastructure/models/industry.py

class IndustryLocalRepository:
    """Local repository for industry model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, industry):
        """Save industry to local storage"""
        self.data_store.append(industry)
        
    def find_by_id(self, industry_id):
        """Find industry by ID"""
        for industry in self.data_store:
            if getattr(industry, 'id', None) == industry_id:
                return industry
        return None
        
    def find_all(self):
        """Find all industries"""
        return self.data_store.copy()