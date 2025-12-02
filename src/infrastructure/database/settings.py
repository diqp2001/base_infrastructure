import os
from sqlalchemy import URL

connection_string_1 = "driver=ODBC+Driver+17+for+SQL+Server;"
connection_string_2 = "Server=localhost;"
connection_string_3 = "Database=base_infra;trusted_connection=yes;TrustServerCertificate=yes"
connection_string = f"{connection_string_1}{connection_string_2}{connection_string_3}"
        
SSMS_url= URL.create("mssql+pyodbc",query={"odbc_connect":connection_string})
DATABASES = {
    'sqlite': "sqlite:///./test.db",
    'sqlite_CrossSectionalMLStockReturns': "sqlite:///./CrossSectionalMLStockReturns.db",
    'sql_server': SSMS_url
}


def get_database_url(db_type='sqlite'):
    return DATABASES.get(db_type)