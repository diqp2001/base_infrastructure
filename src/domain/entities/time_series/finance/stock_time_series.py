from src.domain.entities.finance.financial_assets.stock import Stock
from src.domain.entities.time_series.finance.financial_asset_time_series import FinancialAssetTimeSeries


class StockTimeSeries(FinancialAssetTimeSeries):
    def __init__(self, data):
        """
        Initialize the StockTimeSeries object.
        :param data: Data that can be a DataFrame, numpy array, list, or dict.
        """
        super().__init__(data)
    
    def create_stock(self, stock_id, name, price, sector=None, country=None):
        """
        Create a Stock object as a domain entity.
        :param stock_id: Unique identifier for the stock.
        :param name: Name of the stock.
        :param price: Current price of the stock.
        :param sector: Sector the stock belongs to (optional).
        :param country: Country of the stock (optional).
        :return: Stock object.
        """
        return Stock(stock_id, name, sector, country)
    
    def get_unique_stocks(self):
        """
        Return a unique list of Stock objects (domain entities) in the time series.
        :return: List of unique Stock objects.
        """
        stocks = set()
        for index, row in self.time_series.iterrows():
            stock = Stock(
                row['stock_id'], 
                row['name'], 
                row.get('sector', None), 
                row.get('country', None)
            )
            stocks.add(stock)
        return list(stocks)