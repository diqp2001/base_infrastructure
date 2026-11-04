"""
US banks universe of the 10-minute Spatio-Temporal Momentum project (owner's list, 2026-10-26): 26 large and
regional US banks, card issuers and custody / asset-management banks.

Today's list applied to the whole history (survivorship bias, as for every universe in this code base). A ticker
without IBKR data is reported by the preload and simply not eligible; it is never replaced silently.

2026-10-29 (owner's decision): BK -> BNY, the ticker IBKR now lists Bank of New York Mellon under ("No security
definition" for BK). CMA (Comerica) has no IBKR contract either and is not eligible; it stays listed.
"""

BANK_UNIVERSE = {
    "AXP": "American Express",
    "BAC": "Bank of America",
    "BNY": "Bank of New York Mellon (was BK; IBKR lists it as BNY, 2026-10-29)",
    "BLK": "BlackRock",
    "C": "Citigroup",
    "CFG": "Citizens Financial Group",
    "COF": "Capital One Financial",
    "FITB": "Fifth Third Bancorp",
    "GS": "Goldman Sachs",
    "HBAN": "Huntington Bancshares",
    "JPM": "JPMorgan Chase",
    "KEY": "KeyCorp",
    "MTB": "M&T Bank",
    "MS": "Morgan Stanley",
    "NTRS": "Northern Trust",
    "PNC": "PNC Financial Services",
    "RF": "Regions Financial",
    "SCHW": "Charles Schwab",
    "STT": "State Street",
    "SYF": "Synchrony Financial",
    "TFC": "Truist Financial",
    "USB": "U.S. Bancorp",
    "WFC": "Wells Fargo",
    "ZION": "Zions Bancorporation",
    "CMA": "Comerica",
    "FHN": "First Horizon",
}

BANK_UNIVERSE_TICKERS = list(BANK_UNIVERSE)
