# src/domain/entities/company.py

class Company:
    def __init__(self, id: int, name: str, legal_name: str, country_id: int, industry_id: int, start_date, end_date=None):
        self.id = id
        self.name = name
        self.legal_name = legal_name
        self.country_id = country_id
        self.industry_id = industry_id
        self.start_date = start_date
        self.end_date = end_date

        

