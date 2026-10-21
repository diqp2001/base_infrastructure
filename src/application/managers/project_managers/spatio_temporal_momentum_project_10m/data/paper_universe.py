"""
Universe of the paper — Tan, Roberts & Zohren (2023), "Spatio-Temporal Momentum",
Appendix B: 46 actively-traded US equities from the Financials sector (CRSP,
random sample), backtested 1990-2022.

Some constituents stopped trading after the paper.  Each is replaced by a
listed, comparable US financial company; where a constituent's status is
uncertain (pending / recent merger) it is KEPT and a comparable is ADDED, so
the universe errs on the side of more than 46 names.  Any ticker without IBKR
data at a bar is simply not eligible, so keeping an uncertain name is harmless.
"""

# ticker -> description, exactly as listed in the paper (Appendix B)
PAPER_US_EQUITIES = {
    "AFG": "AMERICAN FINANCIAL GROUP INC NEW",
    "AFL": "AFLAC INC",
    "AJG": "GALLAGHER ARTHUR J & CO",
    "BAC": "BANK OF AMERICA CORP",
    "C": "CITIGROUP INC",
    "CADE": "CADENCE BANK",
    "CBSH": "COMMERCE BANCSHARES INC",
    "CFR": "CULLEN FROST BANKERS INC",
    "CHCO": "CITY HOLDING CO",
    "CPF": "CENTRAL PACIFIC FINANCIAL CORP",
    "CVBF": "C V B FINANCIAL CORP",
    "FITB": "FIFTH THIRD BANCORP",
    "GL": "GLOBE LIFE INC",
    "IBCP": "INDEPENDENT BANK CORP MICH",
    "INDB": "INDEPENDENT BANK CORP MA",
    "JEF": "JEFFERIES FINANCIAL GROUP INC",
    "JPM": "JPMORGAN CHASE & CO",
    "KEY": "KEYCORP NEW",
    "MCO": "MOODYS CORP",
    "MCY": "MERCURY GENERAL CORP NEW",
    "MKL": "MARKEL CORP",
    "NTRS": "NORTHERN TRUST CORP",
    "NWLI": "NATIONAL WESTERN LIFE GROUP INC",
    "PNC": "P N C FINANCIAL SERVICES GRP INC",
    "SBCF": "SEACOAST BANKING CORP FLA",
    "SCHW": "SCHWAB CHARLES CORP NEW",
    "SEIC": "S E I INVESTMENTS COMPANY",
    "SIGI": "SELECTIVE INSURANCE GROUP INC",
    "SIVB": "S V B FINANCIAL GROUP",
    "SNV": "SYNOVUS FINANCIAL CORP",
    "SRCE": "1ST SOURCE CORP",
    "STT": "STATE STREET CORP",
    "TFC": "TRUIST FINANCIAL CORP",
    "TMP": "TOMPKINS FINANCIAL CORP",
    "TRC": "TEJON RANCH CO",
    "TROW": "T ROWE PRICE GROUP INC",
    "TRST": "TRUSTCO BANK CORP NY",
    "UBSI": "UNITED BANKSHARES INC",
    "UFCS": "UNITED FIRE GROUP INC",
    "USB": "U S BANCORP DEL",
    "VALU": "VALUE LINE INC",
    "VLY": "VALLEY NATIONAL BANCORP",
    "WABC": "WESTAMERICA BANCORPORATION",
    "WFC": "WELLS FARGO & CO NEW",
    "WRB": "BERKLEY W R CORP",
    "ZION": "ZIONS BANCORPORATION N A",
}

# Delisted since the paper -> removed and REPLACED by a comparable
REPLACED = {
    "SIVB": ("WAL", "SVB Financial failed and was delisted (2023); Western Alliance Bancorporation is the "
                    "closest listed regional bank with a tech / venture-banking focus"),
    "NWLI": ("CNO", "National Western Life was acquired and delisted (2024); CNO Financial Group is a listed "
                    "US life & annuity insurer"),
}

# Status uncertain (announced / recent merger) -> KEPT, and a comparable ADDED
ADDED_ALONGSIDE = {
    "CADE": ("HBAN", "Cadence Bank agreed to be acquired by Huntington Bancshares (2025); Huntington is added "
                     "as the comparable (and acquirer) regional bank"),
    "SNV": ("PNFP", "Synovus agreed to merge with Pinnacle Financial Partners (2025); Pinnacle is added as the "
                    "comparable (and merger partner) southeastern regional bank"),
}


def paper_universe_tickers() -> list:
    """Paper order, replacements in place, additions appended at the end."""
    tickers = [REPLACED[t][0] if t in REPLACED else t for t in PAPER_US_EQUITIES]
    tickers += [comparable for comparable, _ in ADDED_ALONGSIDE.values()]
    return list(dict.fromkeys(tickers))


PAPER_UNIVERSE_TICKERS = paper_universe_tickers()
