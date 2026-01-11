# Options Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/options.py

class OptionsLocalRepository:
    """Local repository for options model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, option):
        """Save option to local storage"""
        self.data_store.append(option)
        
    def find_by_id(self, option_id):
        """Find option by ID"""
        for option in self.data_store:
            if getattr(option, 'id', None) == option_id:
                return option
        return None
        
    def find_all(self):
        """Find all options"""
        return self.data_store.copy()