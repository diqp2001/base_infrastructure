# Company Local Repository
# Mirrors src/infrastructure/models/finance/company.py

class CompanyLocalRepository:
    """Local repository for company model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, company):
        """Save company to local storage"""
        self.data_store.append(company)
        
    def find_by_id(self, company_id):
        """Find company by ID"""
        for company in self.data_store:
            if getattr(company, 'id', None) == company_id:
                return company
        return None
        
    def find_all(self):
        """Find all companies"""
        return self.data_store.copy()