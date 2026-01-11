# Back Testing Data Types Local Repository
# Mirrors src/infrastructure/models/finance/back_testing/back_testing_data_types.py

class BackTestingDataTypesLocalRepository:
    """Local repository for back testing data types model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, back_testing_data_type):
        """Save back testing data type to local storage"""
        self.data_store.append(back_testing_data_type)
        
    def find_by_id(self, back_testing_data_type_id):
        """Find back testing data type by ID"""
        for data_type in self.data_store:
            if getattr(data_type, 'id', None) == back_testing_data_type_id:
                return data_type
        return None
        
    def find_all(self):
        """Find all back testing data types"""
        return self.data_store.copy()