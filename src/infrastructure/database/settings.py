import os
from sqlalchemy import URL

# SQL Server connection used by DatabaseService("sql_server") / BaseFactory.
#
# Resolution order:
#   1. DB_ODBC_CONNECTION_STRING  - a complete ODBC connection string, used as is;
#   2. DB_HOST (alias DB_SERVER) + DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_DRIVER,
#      DB_TRUST_SERVER_CERTIFICATE
#      - SQL authentication, e.g. the Linux dev container -> "sqlserver" compose service;
#   3. nothing set - the original Windows configuration below (local default instance,
#      Windows integrated authentication, ODBC Driver 17).


def _odbc_value(value: str) -> str:
    """Brace-quote an ODBC attribute value so ';', '{' or '}' in it (e.g. a password) are safe."""
    return "{" + value.replace("}", "}}") + "}"


def _sql_auth_connection_string(server: str, user: str, password: str) -> str:
    port = os.getenv("DB_PORT", "1433")
    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    trust = os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes")
    return (
        f"DRIVER={_odbc_value(driver)};"
        f"SERVER={server},{port};"
        f"DATABASE={os.getenv('DB_NAME', 'base_infra')};"
        f"UID={user};"
        f"PWD={_odbc_value(password)};"
        f"Encrypt=yes;TrustServerCertificate={trust}"
    )


def _sql_server_connection_string() -> str:
    explicit = os.getenv("DB_ODBC_CONNECTION_STRING")
    if explicit:
        return explicit

    server = os.getenv("DB_HOST") or os.getenv("DB_SERVER")
    if server:
        return _sql_auth_connection_string(server, os.getenv('DB_USER', 'sa'), os.getenv('DB_PASSWORD', ''))

    # Original Windows configuration (unchanged)
    connection_string_1 = "driver=ODBC+Driver+17+for+SQL+Server;"
    connection_string_2 = "Server=localhost;"
    connection_string_3 = "Database=base_infra;trusted_connection=yes;TrustServerCertificate=yes"
    return f"{connection_string_1}{connection_string_2}{connection_string_3}"


connection_string = _sql_server_connection_string()

SSMS_url= URL.create("mssql+pyodbc",query={"odbc_connect":connection_string})
DATABASES = {

    'sql_server': SSMS_url
}


def get_database_url(db_type='sqlite'):
    return DATABASES.get(db_type)


def get_readonly_database_url():
    """SQL Server URL for read-only consumers (monitoring dashboard), or None if not configured.

    Uses the dedicated read-only login DB_READONLY_USER / DB_READONLY_PASSWORD (member of
    db_datareader only, created by the sqlserver-init compose service), so read-only access is
    enforced by SQL Server itself, not only by the application.
    """
    server = os.getenv("DB_HOST") or os.getenv("DB_SERVER")
    user = os.getenv("DB_READONLY_USER")
    if not server or not user:
        return None
    password = os.getenv("DB_READONLY_PASSWORD", "")
    return URL.create("mssql+pyodbc",
                      query={"odbc_connect": _sql_auth_connection_string(server, user, password)})
