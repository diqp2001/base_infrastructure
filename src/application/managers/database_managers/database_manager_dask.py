# file: database_manager_dask.py

import dask.dataframe as dd
from .database_manager import DatabaseManager

class DatabaseManagerDask(DatabaseManager):
    """
    A manager for working with Dask DataFrames and SQL databases.
    """
    
    def read_table(self, table_name: str, chunksize: int = None):
        """
        Read a table from the database into a Dask DataFrame.

        Parameters:
        - table_name: Name of the table to read.
        - chunksize: Number of rows per partition, default is database-dependent.
        
        Returns:
        - A Dask DataFrame.
        """
        return dd.read_sql_table(table_name, self.engine, index_col='id', chunksize=chunksize)

    def write_table(self, dask_df: dd.DataFrame, table_name: str, if_exists: str = 'append'):
        """
        Write a Dask DataFrame to a SQL table.

        Parameters:
        - dask_df: The Dask DataFrame to write.
        - table_name: Name of the table to write to.
        - if_exists: Behavior if the table exists ('fail', 'replace', 'append').
        """
        dask_df.to_sql(
            table_name, 
            con=self.engine, 
            index=False, 
            if_exists=if_exists, 
            chunksize=1000, 
            method='multi'
        )