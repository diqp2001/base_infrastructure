# Forward Contract Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/forward_contract.py

class ForwardContractLocalRepository:
    """Local repository for forward contract model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, forward_contract):
        """Save forward contract to local storage"""
        self.data_store.append(forward_contract)
        
    def find_by_id(self, forward_contract_id):
        """Find forward contract by ID"""
        for forward_contract in self.data_store:
            if getattr(forward_contract, 'id', None) == forward_contract_id:
                return forward_contract
        return None
        
    def find_all(self):
        """Find all forward contracts"""
        return self.data_store.copy()