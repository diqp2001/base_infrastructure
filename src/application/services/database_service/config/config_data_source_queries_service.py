QUERIES = {
    "select_all_from_table": "SELECT * FROM {table_name}",
    "insert_into_table": "INSERT INTO {target_table} (SELECT * FROM {source_table})",
    "select_filtered_data": """
        SELECT {columns} FROM {table_name}
        WHERE {filter_column} = :filter_value
    """,
    "select_from_multiple_tables": """
        SELECT a.id, a.name, b.value, b.date
        FROM table_a AS a
        JOIN table_b AS b ON a.id = b.a_id
    """,
    "aggregate_financial_data": """
        SELECT asset_id, AVG(value) AS avg_value, MAX(value) AS max_value, MIN(value) AS min_value
        FROM financial_data
        GROUP BY asset_id
    """,
    "fetch_recent_transactions": """
        SELECT *
        FROM transactions
        WHERE transaction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    """
    # Add more queries as needed
}
