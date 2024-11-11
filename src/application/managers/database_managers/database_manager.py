# database_manager.py

from typing import Dict, List, Union
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.infrastructure.database.connections import get_database_session
from config.config_data_source_manager import QUERIES, get_query

class DatabaseManager:
    def __init__(self, db_type='sqlite'):
        self.db_type = db_type
        self.session: Session = get_database_session(db_type)

    def execute_config_query(self, query_key: str) -> list[dict]:
        """
        Executes a query from config_data_source_manager based on a query key.
        
        :param query_key: The key for the query in QUERIES.
        :return: List of dictionaries representing each row.
        """
        query = QUERIES.get(query_key)
        if query is None:
            raise ValueError(f"No query found for key '{query_key}'.")

        try:
            result = self.session.execute(text(query))
            return [dict(row) for row in result]
        except Exception as e:
            self.session.rollback()
            print(f"Error executing config query: {e}")
            return []

    def insert_from_select_config(self, source_query_key: str, target_table: str) -> None:
        """
        Executes an `INSERT INTO ... SELECT ...` query using a query from the config.
        
        :param source_query_key: The key for the source query in QUERIES.
        :param target_table: Name of the target table where data should be inserted.
        """
        source_query = QUERIES.get(source_query_key)
        if source_query is None:
            raise ValueError(f"No query found for key '{source_query_key}'.")

        insert_query = f"INSERT INTO {target_table} {source_query}"

        try:
            self.session.execute(text(insert_query))
            self.session.commit()
            print(f"Data successfully inserted into {target_table} from source query.")
        except Exception as e:
            self.session.rollback()
            print(f"Error executing insert from select: {e}")

    def fetch_dataframe_with_dynamic_table(
        self,
        query_key: str,
        table_name: str,
        columns: List[str] = None,
        filters: Dict[str, Union[str, int, float]] = None,
        top_n: int = None
    ) -> pd.DataFrame:
        """
        Fetches data with a dynamic table name and optional filters.

        :param query_key: Key in QUERIES to retrieve the query template.
        :param table_name: The table to dynamically insert into the query.
        :param columns: Optional list of columns to retrieve.
        :param filters: Optional dictionary for filtering results.
        :param top_n: Optional limit on the number of rows.
        :return: DataFrame of query results or empty on error.
        """
        try:
            # Construct the dynamic query with table name and columns
            columns_str = ', '.join(columns) if columns else '*'
            source_query = get_query(query_key, table_name=table_name, columns=columns_str)

            # Add optional filter conditions
            if filters:
                filter_conditions = " AND ".join([f"{col} = :{col}" for col in filters.keys()])
                source_query += f" WHERE {filter_conditions}"
            
            # Add limit for top rows
            if top_n:
                source_query += f" LIMIT {top_n}"

            # Execute the query
            df = pd.read_sql(text(source_query), con=self.session.bind, params=filters)
            return df
        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()
    def close_session(self):
        self.session.close()

