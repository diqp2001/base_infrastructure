class FinancialAsset:
    def __init__(self, id, start_date):
        self.id = id
        self.start_date = start_date

    @property
    def asset_type(self):
        raise NotImplementedError("This method should be implemented by subclass.")
    
    def __repr__(self):
        return f"<{self.asset_type}>"