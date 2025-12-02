import os

DATABASES = {
    'sqlite': "sqlite:///./test.db",
    'sqlite_CrossSectionalMLStockReturns': "sqlite:///./CrossSectionalMLStockReturns.db",
    'sql_server': os.getenv("SQL_SERVER_URL", 
                           "mssql+pyodbc://localhost/MSSQLSERVER?"
                           "driver=ODBC+Driver+17+for+SQL+Server&"
                           "trusted_connection=yes&"
                           "TrustServerCertificate=yes"),
    # Add additional database configurations as needed
}

def get_database_url(db_type='sqlite'):
    return DATABASES.get(db_type)