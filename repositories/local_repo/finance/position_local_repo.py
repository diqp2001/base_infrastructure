# Position Local Repository
# Mirrors src/infrastructure/models/finance/position.py

class PositionLocalRepository:
    """Local repository for position model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, position):
        """Save position to local storage"""
        self.data_store.append(position)
        
    def find_by_id(self, position_id):
        """Find position by ID"""
        for position in self.data_store:
            if getattr(position, 'id', None) == position_id:
                return position
        return None
        
    def find_all(self):
        """Find all positions"""
        return self.data_store.copy()