"""
Point-in-time constituents of DIA (SPDR Dow Jones Industrial Average ETF = the DJIA, price-weighted).

Sources: S&P Dow Jones Indices announcements; Wikipedia "Historical components of the Dow Jones Industrial Average"
(checked 2026-11-16); cross-checked against DIA's own holdings file of 2026-11-05 (the same 30 names, each with the
same share count). Base = the 30 members after the 2020-08-31 change; a change is effective before the open of its
date. A backtest cannot start before BASE_DATE (add the earlier changes to go back further).
"""

from datetime import date

from src.application.services.dispersion.index_membership import IndexMembership, MembershipChange, Split

ETF = 'DIA'
BASE_DATE = date(2020, 8, 31)
BASE_MEMBERS = (
    'AAPL', 'AMGN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO', 'CVX', 'DIS', 'DOW', 'GS', 'HD', 'HON', 'IBM', 'INTC',
    'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT',
)
CHANGES = (
    MembershipChange(date(2024, 2, 26), added=('AMZN',), removed=('WBA',)),
    MembershipChange(date(2024, 11, 8), added=('NVDA', 'SHW'), removed=('INTC', 'DOW')),
    MembershipChange(date(2026, 6, 29), added=('GOOGL',), removed=('VZ',)),
)
# GICS sector of every member since BASE_DATE (current classification; the March 2023 GICS change moved V from
# Information Technology to Financials - the current one is used for every date). Used to scale fundamentals
# sector-neutrally (stm_dataset.cross_sectional_zscore(groups=...)).
SECTORS = {
    'AAPL': 'Information Technology', 'CRM': 'Information Technology', 'CSCO': 'Information Technology',
    'IBM': 'Information Technology', 'INTC': 'Information Technology', 'MSFT': 'Information Technology',
    'NVDA': 'Information Technology',
    'AMGN': 'Health Care', 'JNJ': 'Health Care', 'MRK': 'Health Care', 'UNH': 'Health Care',
    'AXP': 'Financials', 'GS': 'Financials', 'JPM': 'Financials', 'TRV': 'Financials', 'V': 'Financials',
    'BA': 'Industrials', 'CAT': 'Industrials', 'HON': 'Industrials', 'MMM': 'Industrials',
    'AMZN': 'Consumer Discretionary', 'HD': 'Consumer Discretionary', 'MCD': 'Consumer Discretionary',
    'NKE': 'Consumer Discretionary',
    'KO': 'Consumer Staples', 'PG': 'Consumer Staples', 'WBA': 'Consumer Staples', 'WMT': 'Consumer Staples',
    'DIS': 'Communication Services', 'GOOGL': 'Communication Services', 'VZ': 'Communication Services',
    'CVX': 'Energy',
    'DOW': 'Materials', 'SHW': 'Materials',
}
# splits of a member while in the index after BASE_DATE (price-weighted: the traded price sets the weight)
SPLITS = (
    Split('WMT', date(2024, 2, 26), 3.0),
)


def build_membership(universe_name: str = 'DIA point-in-time constituents') -> IndexMembership:
    return IndexMembership(ETF, BASE_DATE, BASE_MEMBERS, CHANGES, SPLITS, universe_name=universe_name)
