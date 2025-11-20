# database_service.py

from typing import Dict, List, Union
import pandas as pd
import dask.dataframe as dd
from sqlalchemy.orm import Session,sessionmaker
from sqlalchemy import Tuple, create_engine, text
from application.services.database_service.config.config_data_source_service import get_query
from application.services.database_service.config.config_data_source_queries_service import QUERIES
from domain.database import Database
from infrastructure.database.settings import get_database_url



class DatabaseService:
    def __init__(self, db_type='sqlite'):
     
        self.db_type = db_type
        self.db = Database(self.db_type)
        self.session: Session  = self.db.SessionLocal

    def set_local_db(self):
        self.db = Database(self.db_type)
        self.session: Session  = self.db.SessionLocal

    def set_ext_db(self):
        database_url = get_database_url(self.db_type)
        self.engine = create_engine(database_url)
        Session  = sessionmaker(bind=self.engine)
        self.session = Session()




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
            print(f'SQL Statement executed succesfully at the {self.db_type}')
        except Exception as e:
            self.session.rollback()
            print(f"Error executing config query: {e}")
            return []
    def execute_query(self, query:str):
        try:
            self.session.execute(text(query))
            self.session.commit()
            print(f'SQL Statement executed succesfully at the {self.db_type}')

        except Exception as e:
            self.session.rollback()
            print(f'Error executing query: {e}')

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
        filters: Dict[str,  Union[str, int, float]] = None,
        top_n: int = None
    ) -> pd.DataFrame:
        """
        Fetches data with a dynamic table name and optional filters.

        :param query_key: Key in QUERIES to retrieve the query template.
        :param table_name: The table to dynamically insert into the query.
        :param columns: Optional list of columns to retrieve.
        :param filters: Optional dictionary for filtering results.
        filters = {
                    "age": (">", 30),         # Select rows where 'age' is greater than 30
                    "salary": ("<=", 100000), # Select rows where 'salary' is less than or equal to 100000
                    "department": ("=", "HR"), # Select rows where 'department' is equal to 'HR'
                    "hire_date": (">=", "2022-01-01")  # Select rows where 'hire_date' is on or after January 1, 2022
                    }

        :param top_n: Optional limit on the number of rows.
        :return: DataFrame of query results or empty on error.
        """
        try:
            # Construct the dynamic query with table name and columns
            columns_str = ', '.join(columns) if columns else '*'
            source_query = get_query(query_key, table_name=table_name, columns=columns_str)
            # Add optional filter conditions
            if filters:
                filter_conditions = " AND ".join([f"{col} {op} :{col}" for col, (op, _) in filters.items()])
                source_query += f" WHERE {filter_conditions}"
                filter_values = {col: value for col, (_, value) in filters.items()}
            else:
                filter_values = {}

            # Add limit for top rows
            if top_n:
                source_query += f" LIMIT {top_n}"

            # Execute the query
            df = pd.read_sql(text(source_query), con=self.session.bind, params=filter_values)
            print(f'SQL Statement executed succesfully at the {self.db_type}')
            return df
        except Exception as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()
        
    
        
    def csv_to_db(self, file_path: str, table_name: str, if_exists: str = 'replace', index: bool = False):
        """
        Reads a CSV file and loads it into a specified database table.

        :param file_path: Path to the CSV file.
        :param table_name: Name of the database table to load the data into.
        :param if_exists: Behavior if the table already exists ('replace', 'append', 'fail').
        :param index: Whether to write row names (index) in the database.
        """
        try:
            data = pd.read_csv(file_path)
            data.to_sql(table_name, con=self.session.bind, if_exists=if_exists, index=index)
            print(f"CSV data loaded into '{table_name}' table successfully.")
        except Exception as e:
            print(f"Error loading CSV to database: {e}")

    def excel_to_db(self, file_path: str, table_name: str, sheet_name: Union[str, int] = 0, if_exists: str = 'replace', index: bool = False):
        """
        Reads an Excel file and loads it into a specified database table.

        :param file_path: Path to the Excel file.
        :param table_name: Name of the database table to load the data into.
        :param sheet_name: Name or index of the sheet to read.
        :param if_exists: Behavior if the table already exists ('replace', 'append', 'fail').
        :param index: Whether to write row names (index) in the database.
        """
        try:
            data = pd.read_excel(file_path, sheet_name=sheet_name)
            data.to_sql(table_name, con=self.session.bind, if_exists=if_exists, index=index)
            print(f"Excel data loaded into '{table_name}' table successfully.")
        except Exception as e:
            print(f"Error loading Excel to database: {e}")

    def close_session(self):
        self.session.close()

    def csv_to_dataframe(self, file_path: str) -> pd.DataFrame:
        """
        Reads a CSV file into a Pandas DataFrame.
        
        :param file_path: Path to the CSV file.
        :return: DataFrame containing the CSV data.
        """
        try:
            df = pd.read_csv(file_path)
            print(f"CSV data loaded into DataFrame successfully.")
            return df
        except Exception as e:
            print(f"Error loading CSV to DataFrame: {e}")
            return pd.DataFrame()

    def excel_to_dataframe(self, file_path: str, sheet_name: Union[str, int] = 0) -> pd.DataFrame:
        """
        Reads an Excel file into a Pandas DataFrame.
        
        :param file_path: Path to the Excel file.
        :param sheet_name: Name or index of the sheet to read.
        :return: DataFrame containing the Excel data.
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            print(f"Excel data loaded into DataFrame successfully.")
            return df
        except Exception as e:
            print(f"Error loading Excel to DataFrame: {e}")
            return pd.DataFrame()
        
    def dataframe_replace_table(self, df: pd.DataFrame, table_name: str) -> None:
        """
        Replaces the existing database table with new data.

        :param df: The DataFrame containing the data to load.
        :param table_name: The name of the database table.
        """
        try:
            df.to_sql(name=table_name, con=self.session.bind, if_exists='replace', index=False)
            print(f"Table '{table_name}' successfully replaced with new data.")
        except Exception as e:
            print(f"Error replacing table '{table_name}': {e}")

    def dataframe_append_to_table(self, df: pd.DataFrame, table_name: str) -> None:
        """
        Appends data to an existing database table.

        :param df: The DataFrame containing the data to append.
        :param table_name: The name of the database table.
        """
        try:
            df.to_sql(name=table_name, con=self.session.bind, if_exists='append', index=False)
            print(f"Data successfully appended to table '{table_name}'.")
        except Exception as e:
            print(f"Error appending data to table '{table_name}': {e}")

    def fetch_dask_dataframe_with_sql_query(
        self,
        query: str,
        index_col: str,
        **kwargs
    ) -> dd.DataFrame:
        """
        Fetches a Dask DataFrame from a SQL query.

        :param query: The SQL query to execute or the table name.
        :param index_col: Column to use as the DataFrame index. Should be indexed in the SQL database.
        :param kwargs: Additional keyword arguments for customization.
        :return: Dask DataFrame.
        """
        try:
            df = dd.read_sql(sql=query, con=self.connection_string, index_col=index_col, **kwargs)
            print("Dask DataFrame successfully loaded from SQL.")
            return df
        except Exception as e:
            print(f"Error loading Dask DataFrame from SQL: {e}")
            return dd.from_pandas(pd.DataFrame(), npartitions=1)

    def csv_to_dask_dataframe(self, file_path: str) -> dd.DataFrame:
        """
        Reads a CSV file into a Dask DataFrame.

        :param file_path: Path to the CSV file.
        :return: Dask DataFrame.
        """
        try:
            df = dd.read_csv(file_path)
            print(f"CSV data loaded into Dask DataFrame successfully.")
            return df
        except Exception as e:
            print(f"Error loading CSV into Dask DataFrame: {e}")
            return dd.from_pandas(pd.DataFrame(), npartitions=1)

    def dask_dataframe_replace_table(self, df: dd.DataFrame, table_name: str) -> None:
        """
        Replaces the existing database table with new data using a Dask DataFrame.

        :param df: The Dask DataFrame containing the data to load.
        :param table_name: The name of the database table.
        """
        try:
            df.compute().to_sql(name=table_name, con=self.engine, if_exists='replace', index=False)
            print(f"Table '{table_name}' successfully replaced with new data from Dask DataFrame.")
        except Exception as e:
            print(f"Error replacing table '{table_name}': {e}")

    def dask_dataframe_append_to_table(self, df: dd.DataFrame, table_name: str) -> None:
        """
        Appends data to an existing database table using a Dask DataFrame.

        :param df: The Dask DataFrame containing the data to append.
        :param table_name: The name of the database table.
        """
        try:
            df.compute().to_sql(name=table_name, con=self.engine, if_exists='append', index=False)
            print(f"Data successfully appended to table '{table_name}' from Dask DataFrame.")
        except Exception as e:
            print(f"Error appending data to table '{table_name}': {e}")