"""
Read-only monitoring of the trading infrastructure (application, IB Gateway, SQL Server,
market data, factors, jobs, logs) for the monitoring dashboard.

Nothing in this package mutates state: database access goes through a guarded read-only
engine (and a db_datareader login), IBKR access through ReadOnlyIBKRClient which refuses
every order / configuration method.
"""
