#!/usr/bin/env bash
# One-shot initialisation run by the sqlserver-init compose service (idempotent):
#   1. create the application database DB_NAME and the test database DB_NAME_test if they do not
#      exist (never drops anything);
#   2. if DB_READONLY_USER is set: create / update a login + database user that is only a member
#      of db_datareader, with INSERT / UPDATE / DELETE / ALTER / EXECUTE explicitly denied.
#      The monitoring dashboard connects with this login, so SQL Server enforces read-only access.
set -euo pipefail
SQLCMD=(/opt/mssql-tools18/bin/sqlcmd -C -S "${SQLSERVER_HOST:-sqlserver}" -U sa -P "${MSSQL_SA_PASSWORD}" -b)
HERE="$(cd "$(dirname "$0")" && pwd)"

"${SQLCMD[@]}" -v DB="${DB_NAME}" -i "${HERE}/create-database.sql"
echo "database ${DB_NAME} ready"

# Dedicated database for the SQL Server integration tests (pytest -m sql_server with
# DB_NAME=${DB_TEST_NAME:-base_infra_test}); the tests also create it on first use.
TEST_DB="${DB_TEST_NAME:-${DB_NAME}_test}"
"${SQLCMD[@]}" -v DB="${TEST_DB}" -i "${HERE}/create-database.sql"
echo "test database ${TEST_DB} ready"

if [ -n "${DB_READONLY_USER:-}" ]; then
    case "${DB_READONLY_PASSWORD:-}" in
        *"'"*) echo "DB_READONLY_PASSWORD must not contain single quotes" >&2; exit 1 ;;
        "")    echo "DB_READONLY_PASSWORD is empty" >&2; exit 1 ;;
    esac
    "${SQLCMD[@]}" -v DB="${DB_NAME}" RO_USER="${DB_READONLY_USER}" RO_PWD="${DB_READONLY_PASSWORD}" \
        -i "${HERE}/create-readonly-user.sql"
    echo "read-only login ${DB_READONLY_USER} ready (db_datareader only)"
fi
