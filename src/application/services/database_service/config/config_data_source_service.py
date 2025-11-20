# config_data_source_manager.py

from .config_data_source_queries_service import QUERIES

DATABASE_URLS = {
    "sqlite": "sqlite:///mydatabase.db",
    # Add other database URLs as needed
}

TABLE_NAMES = {
    "financial_data": "financial_data",
    "aggregated_data": "aggregated_data_table",
    # Add other table names as needed
}

def get_query(query_key: str, **kwargs) -> str:
    """
    Retrieves a query template from QUERIES and formats it with provided parameters.
    
    :param query_key: Key of the query in QUERIES dictionary.
    :param kwargs: Parameters to format the query string.
    :return: Formatted SQL query string.
    """
    source_query = QUERIES.get(query_key)
    if source_query:
        return source_query.format(**kwargs)
    else:
        raise ValueError(f"Query key '{query_key}' not found in QUERIES.")