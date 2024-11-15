# src/domain/entities/company.py

class Company:
    def __init__(self, name,legal_name,countryId,industryId,start_date,end_date=None):
        self.name = name
        self.legal_name = legal_name
        self.countryId = countryId
        self.industryId = industryId
        self.start_date = start_date
        self.end_date = end_date

        

