import dask.dataframe as dd
import pandas as pd
from typing import Optional, Dict, Any, List
from .database_service import DatabaseService


class DaskDatabaseService(DatabaseService):
    """
    Service for working with Dask DataFrames and SQL databases.
    Extends DatabaseService with Dask-specific operations for big data processing.
    """
    
    def __init__(self, db_type: str = 'sqlite', db_path: str = None, **kwargs):
        """
        Initialize the Dask database service.
        
        Args:
            db_type: Type of database ('sqlite', 'postgresql', 'mysql', etc.)
            db_path: Path to database file or connection string
            **kwargs: Additional database connection parameters
        """
        super().__init__(db_type, db_path, **kwargs)

    def read_table_dask(self, table_name: str, chunksize: Optional[int] = None,
                       index_col: str = 'id') -> dd.DataFrame:
        """
        Read a table from the database into a Dask DataFrame.

        Args:
            table_name: Name of the table to read
            chunksize: Number of rows per partition (database-dependent default)
            index_col: Column to use as index
        
        Returns:
            Dask DataFrame with table data
        """
        try:
            return dd.read_sql_table(
                table_name, 
                self.engine, 
                index_col=index_col, 
                chunksize=chunksize
            )
        except Exception as e:
            print(f"Error reading table {table_name} with Dask: {e}")
            raise

    def read_query_dask(self, query: str, index_col: Optional[str] = None,
                       chunksize: Optional[int] = 10000) -> dd.DataFrame:
        """
        Execute a query and return results as a Dask DataFrame.

        Args:
            query: SQL query string
            index_col: Column to use as index
            chunksize: Number of rows per partition
        
        Returns:
            Dask DataFrame with query results
        """
        try:
            return dd.read_sql_query(
                query,
                con=self.engine,
                index_col=index_col,
                chunksize=chunksize
            )
        except Exception as e:
            print(f"Error executing query with Dask: {e}")
            raise

    def write_table_dask(self, dask_df: dd.DataFrame, table_name: str, 
                        if_exists: str = 'append', chunksize: int = 1000,
                        method: str = 'multi') -> None:
        """
        Write a Dask DataFrame to a SQL table.

        Args:
            dask_df: The Dask DataFrame to write
            table_name: Name of the table to write to
            if_exists: Behavior if table exists ('fail', 'replace', 'append')
            chunksize: Number of rows to write per batch
            method: Insertion method ('multi' for faster bulk inserts)
        """
        try:
            dask_df.to_sql(
                table_name, 
                con=self.engine, 
                index=False, 
                if_exists=if_exists, 
                chunksize=chunksize, 
                method=method
            )
            print(f"Successfully wrote Dask DataFrame to table {table_name}")
        except Exception as e:
            print(f"Error writing Dask DataFrame to table {table_name}: {e}")
            raise

    def read_csv_dask(self, file_path: str, **kwargs) -> dd.DataFrame:
        """
        Read CSV file(s) into a Dask DataFrame.

        Args:
            file_path: Path to CSV file or glob pattern
            **kwargs: Additional parameters for dd.read_csv
        
        Returns:
            Dask DataFrame with CSV data
        """
        try:
            return dd.read_csv(file_path, **kwargs)
        except Exception as e:
            print(f"Error reading CSV file {file_path} with Dask: {e}")
            raise

    def read_parquet_dask(self, file_path: str, **kwargs) -> dd.DataFrame:
        """
        Read Parquet file(s) into a Dask DataFrame.

        Args:
            file_path: Path to Parquet file or directory
            **kwargs: Additional parameters for dd.read_parquet
        
        Returns:
            Dask DataFrame with Parquet data
        """
        try:
            return dd.read_parquet(file_path, **kwargs)
        except Exception as e:
            print(f"Error reading Parquet file {file_path} with Dask: {e}")
            raise

    def write_parquet_dask(self, dask_df: dd.DataFrame, file_path: str, 
                          compression: str = 'snappy', **kwargs) -> None:
        """
        Write a Dask DataFrame to Parquet format.

        Args:
            dask_df: Dask DataFrame to write
            file_path: Output file path or directory
            compression: Compression algorithm ('snappy', 'gzip', 'brotli')
            **kwargs: Additional parameters for to_parquet
        """
        try:
            dask_df.to_parquet(file_path, compression=compression, **kwargs)
            print(f"Successfully wrote Dask DataFrame to Parquet: {file_path}")
        except Exception as e:
            print(f"Error writing Parquet file {file_path}: {e}")
            raise

    def compute_and_store(self, dask_df: dd.DataFrame, table_name: str,
                         if_exists: str = 'append') -> pd.DataFrame:
        """
        Compute a Dask DataFrame and store it in the database.

        Args:
            dask_df: Dask DataFrame to compute and store
            table_name: Target table name
            if_exists: Behavior if table exists
        
        Returns:
            Computed pandas DataFrame
        """
        try:
            # Compute the Dask DataFrame
            computed_df = dask_df.compute()
            
            # Store in database
            self.execute_dataframe_insert(computed_df, table_name, if_exists=if_exists)
            
            return computed_df
        except Exception as e:
            print(f"Error computing and storing DataFrame: {e}")
            raise

    def get_table_partitions(self, table_name: str, partition_col: str,
                           n_partitions: int = 4) -> dd.DataFrame:
        """
        Read a table with custom partitioning.

        Args:
            table_name: Name of the table
            partition_col: Column to partition on
            n_partitions: Number of partitions to create
        
        Returns:
            Partitioned Dask DataFrame
        """
        try:
            # Get min/max values for partitioning
            query = f"SELECT MIN({partition_col}), MAX({partition_col}) FROM {table_name}"
            result = self.execute_query(query)
            
            if result.empty:
                raise ValueError(f"No data found in table {table_name}")
                
            min_val, max_val = result.iloc[0]
            
            # Create partitioned read
            return dd.read_sql_table(
                table_name,
                con=self.engine,
                index_col=partition_col,
                divisions=[min_val + i * (max_val - min_val) / n_partitions 
                          for i in range(n_partitions + 1)]
            )
        except Exception as e:
            print(f"Error creating partitioned read for table {table_name}: {e}")
            raise

    def parallel_apply(self, dask_df: dd.DataFrame, func, meta=None, **kwargs) -> dd.DataFrame:
        """
        Apply a function to a Dask DataFrame in parallel.

        Args:
            dask_df: Input Dask DataFrame
            func: Function to apply
            meta: Metadata for the result DataFrame
            **kwargs: Additional arguments for the apply function
        
        Returns:
            Transformed Dask DataFrame
        """
        try:
            return dask_df.apply(func, axis=1, meta=meta, **kwargs)
        except Exception as e:
            print(f"Error applying function in parallel: {e}")
            raise

    def aggregate_and_store(self, dask_df: dd.DataFrame, agg_funcs: Dict[str, str],
                          group_by: List[str], table_name: str,
                          if_exists: str = 'replace') -> pd.DataFrame:
        """
        Perform aggregation on Dask DataFrame and store results.

        Args:
            dask_df: Input Dask DataFrame
            agg_funcs: Dictionary of {column: aggregation_function}
            group_by: List of columns to group by
            table_name: Target table for results
            if_exists: Behavior if table exists
        
        Returns:
            Aggregated pandas DataFrame
        """
        try:
            # Perform aggregation
            if group_by:
                aggregated = dask_df.groupby(group_by).agg(agg_funcs)
            else:
                aggregated = dask_df.agg(agg_funcs)
            
            # Compute and store
            return self.compute_and_store(aggregated, table_name, if_exists)
        except Exception as e:
            print(f"Error in aggregate and store: {e}")
            raise

    def merge_dask_dataframes(self, left_df: dd.DataFrame, right_df: dd.DataFrame,
                            on: str, how: str = 'inner', **kwargs) -> dd.DataFrame:
        """
        Merge two Dask DataFrames.

        Args:
            left_df: Left Dask DataFrame
            right_df: Right Dask DataFrame
            on: Column name to merge on
            how: Type of merge ('inner', 'outer', 'left', 'right')
            **kwargs: Additional merge parameters
        
        Returns:
            Merged Dask DataFrame
        """
        try:
            return dd.merge(left_df, right_df, on=on, how=how, **kwargs)
        except Exception as e:
            print(f"Error merging Dask DataFrames: {e}")
            raise

    def repartition_dataframe(self, dask_df: dd.DataFrame, 
                            partition_size: str = "100MB") -> dd.DataFrame:
        """
        Repartition a Dask DataFrame for optimal performance.

        Args:
            dask_df: Dask DataFrame to repartition
            partition_size: Target size per partition
        
        Returns:
            Repartitioned Dask DataFrame
        """
        try:
            return dask_df.repartition(partition_size=partition_size)
        except Exception as e:
            print(f"Error repartitioning DataFrame: {e}")
            raise

    def get_memory_usage(self, dask_df: dd.DataFrame) -> Dict[str, Any]:
        """
        Get memory usage information for a Dask DataFrame.

        Args:
            dask_df: Dask DataFrame to analyze
        
        Returns:
            Dictionary with memory usage information
        """
        try:
            # Get basic info
            info = {
                'npartitions': dask_df.npartitions,
                'columns': list(dask_df.columns),
                'dtypes': dict(dask_df.dtypes)
            }
            
            # Estimate memory usage (compute one partition)
            if not dask_df.empty:
                sample_partition = dask_df.get_partition(0).compute()
                info['estimated_memory_per_partition'] = sample_partition.memory_usage(deep=True).sum()
                info['estimated_total_memory'] = info['estimated_memory_per_partition'] * dask_df.npartitions
            
            return info
        except Exception as e:
            print(f"Error getting memory usage: {e}")
            return {}

    def optimize_dataframe(self, dask_df: dd.DataFrame) -> dd.DataFrame:
        """
        Optimize a Dask DataFrame for better performance.

        Args:
            dask_df: Dask DataFrame to optimize
        
        Returns:
            Optimized Dask DataFrame
        """
        try:
            # Persist in memory for repeated computations
            optimized = dask_df.persist()
            
            # Repartition if needed
            if optimized.npartitions > 100:  # Too many small partitions
                optimized = optimized.repartition(partition_size="100MB")
            
            return optimized
        except Exception as e:
            print(f"Error optimizing DataFrame: {e}")
            return dask_df