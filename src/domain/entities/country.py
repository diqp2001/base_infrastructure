# src/domain/entities/country.py
from typing import List

class Country:
    def __init__(self, name: str, code: str, region: str, population: int, gdp: float, currency: str, languages: List[str]):
        """
        Initialize a Country object with essential details.
        
        :param name: Name of the country (e.g., 'United States')
        :param code: Country code (e.g., 'US')
        :param region: Geographical region (e.g., 'North America')
        :param population: Population of the country (e.g., 331002651 for the US)
        :param gdp: Gross Domestic Product (GDP) in USD (e.g., 21.43 trillion for the US)
        :param currency: Currency used in the country (e.g., 'USD')
        :param languages: List of languages spoken in the country (e.g., ['English'])
        """
        self.name = name
        self.code = code
        self.region = region
        self.population = population
        self.gdp = gdp
        self.currency = currency
        self.languages = languages

    def add_language(self, language: str):
        """
        Add a language spoken in the country.
        
        :param language: Language to add
        """
        if language not in self.languages:
            self.languages.append(language)

    def remove_language(self, language: str):
        """
        Remove a language spoken in the country.
        
        :param language: Language to remove
        """
        if language in self.languages:
            self.languages.remove(language)

    def get_country_info(self):
        """
        Returns a summary of the country.
        """
        return {
            'name': self.name,
            'code': self.code,
            'region': self.region,
            'population': self.population,
            'gdp': self.gdp,
            'currency': self.currency,
            'languages': self.languages
        }

    def __repr__(self):
        return f"Country({self.name}, {self.code}, {self.region}, {self.population}, {self.gdp}, {self.currency}, {self.languages})"
