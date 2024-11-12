import os

DATABASES = {
    'sqlite': "sqlite:///./test.db",
    'sqlite_CrossSectionalMLStockReturns': "sqlite:///./CrossSectionalMLStockReturns.db",
    'sql_server': os.getenv("SQL_SERVER_URL"),
    # Add additional database configurations as needed
}

def get_database_url(db_type='sqlite'):
    return DATABASES.get(db_type)