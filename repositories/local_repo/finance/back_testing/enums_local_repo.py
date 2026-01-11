# Enums Local Repository
# Mirrors src/infrastructure/models/finance/back_testing/enums.py

class EnumsLocalRepository:
    """Local repository for enums model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, enum_item):
        """Save enum item to local storage"""
        self.data_store.append(enum_item)
        
    def find_by_id(self, enum_item_id):
        """Find enum item by ID"""
        for enum_item in self.data_store:
            if getattr(enum_item, 'id', None) == enum_item_id:
                return enum_item
        return None
        
    def find_all(self):
        """Find all enum items"""
        return self.data_store.copy()