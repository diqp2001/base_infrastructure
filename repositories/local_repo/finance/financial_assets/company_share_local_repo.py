# Company Share Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/company_share.py

class CompanyShareLocalRepository:
    """Local repository for company share model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, company_share):
        """Save company share to local storage"""
        self.data_store.append(company_share)
        
    def find_by_id(self, company_share_id):
        """Find company share by ID"""
        for company_share in self.data_store:
            if getattr(company_share, 'id', None) == company_share_id:
                return company_share
        return None
        
    def find_all(self):
        """Find all company shares"""
        return self.data_store.copy()