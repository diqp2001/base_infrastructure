CONFIG_TEST = {
    'DB_TYPE': 'sqlite',
    'dataset_name': "fx-currency-exchange-rates",
    'csv_fx_file': 'currency_exchange_rates_02-01-1995_-_02-05-2018.csv',
    'fx_data_folder': 'fx_data',
    # FX-specific configurations
    'currencies': ['EUR', 'GBP', 'AUD', 'USD', 'MXN', 'JPY', 'CAD'],
    'default_base_currency': 'USD',
    # Add additional database configurations as needed
}