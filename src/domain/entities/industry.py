# src/domain/entities/industry.py
from typing import List

class Industry:
    def __init__(self, name: str, sector_id: int, description: str = "", key_metrics: List[str] = []):
        """
        Initialize an Industry object with essential details.
        
        :param name: The name of the industry (e.g., 'Technology', 'Finance')
        :param sector: The broader sector the industry belongs to (e.g., 'Information Technology', 'Financials')
        :param description: A short description of the industry (optional).
        :param key_metrics: Key performance indicators relevant to the industry (e.g., ['Market Cap', 'Revenue Growth'])
        """
        self.name = name
        self.sector_id = sector_id
        self.description = description
        self.key_metrics = key_metrics
        

    

    def add_key_metric(self, metric: str):
        """
        Add a key metric for the industry.
        
        :param metric: Metric to add
        """
        if metric not in self.key_metrics:
            self.key_metrics.append(metric)

    def get_industry_info(self):
        """
        Returns a summary of the industry.
        """
        return {
            'name': self.name,
            'sector_id': self.sector_id,
            'description': self.description,
            'key_metrics': self.key_metrics
        }

    def __repr__(self):
        return f"Industry({self.name}, {self.sector_id}, {self.description}, {self.key_metrics})"
