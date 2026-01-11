# Financial Statement Local Repository
# Mirrors src/infrastructure/models/finance/financial_statements/financial_statement.py

class FinancialStatementRepository:
    """Local repository for financial statement model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, financial_statement):
        """Save financial statement to local storage"""
        self.data_store.append(financial_statement)
        
    def find_by_id(self, financial_statement_id):
        """Find financial statement by ID"""
        for statement in self.data_store:
            if getattr(statement, 'id', None) == financial_statement_id:
                return statement
        return None
        
    def find_all(self):
        """Find all financial statements"""
        return self.data_store.copy()