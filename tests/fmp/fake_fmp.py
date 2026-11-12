"""A fake Financial Modeling Prep /stable API for the tests: three fiscal years (2023-2025, calendar quarters) of one
company's statements, answered like FMP (newest first, `limit` rows per period). In memory only - nothing is
downloaded and no database other than the tests' in-memory SQLite is written."""

from datetime import date, datetime, timedelta
from urllib.parse import urlparse

SYMBOL = "ACME"
QUARTER_ENDS = [date(y, m, d) for y in (2023, 2024, 2025) for m, d in ((3, 31), (6, 30), (9, 30), (12, 31))]


def accepted(i: int) -> datetime:
    """10-Q 35 days after the quarter, 10-K (Q4 / FY) 60 days after the year, at 16:05 New York."""
    end = QUARTER_ENDS[i]
    return datetime.combine(end + timedelta(days=60 if i % 4 == 3 else 35), datetime.min.time()).replace(hour=16, minute=5)


def income(i):
    revenue, cost, op = 1000.0 + 50 * i, 600.0 + 20 * i, 200.0 + 10 * i
    net = 150.0 + 5 * i
    return {"revenue": revenue, "costOfRevenue": cost, "grossProfit": revenue - cost, "operatingIncome": op,
            "ebit": op, "ebitda": op + 50.0, "depreciationAndAmortization": 50.0, "incomeTaxExpense": 40.0,
            "incomeBeforeTax": net + 40.0, "netIncome": net, "eps": net / 100.0, "epsDiluted": net / 110.0,
            "weightedAverageShsOut": 100.0, "weightedAverageShsOutDil": 110.0, "operatingExpenses": 400.0 + 30 * i,
            "costAndExpenses": 1000.0 + 50 * i}


def balance(i):
    return {"totalAssets": 5000.0 + 100 * i, "totalStockholdersEquity": 2000.0 + 50 * i,
            "totalEquity": 2010.0 + 50 * i, "minorityInterest": 10.0, "totalDebt": 1000.0, "longTermDebt": 800.0,
            "shortTermDebt": 200.0, "cashAndCashEquivalents": 300.0, "netDebt": 700.0}


def cash_flow(i):
    ocf = 250.0 + 5 * i
    return {"operatingCashFlow": ocf, "netCashProvidedByOperatingActivities": ocf, "capitalExpenditure": -50.0,
            "freeCashFlow": ocf - 50.0, "netIncome": 150.0 + 5 * i}


STATEMENTS = {"income-statement": income, "balance-sheet-statement": balance, "cash-flow-statement": cash_flow}
STOCKS = {"balance-sheet-statement"}


def row(endpoint, i, period):
    end = QUARTER_ENDS[i]
    if period == "FY":
        quarters = range(i - 3, i + 1)
        values = (STATEMENTS[endpoint](i) if endpoint in STOCKS else
                  {k: sum(STATEMENTS[endpoint](q)[k] for q in quarters) for k in STATEMENTS[endpoint](i)})
    else:
        values = STATEMENTS[endpoint](i)
    stamp = accepted(i)
    return {"date": end.isoformat(), "symbol": SYMBOL, "reportedCurrency": "USD", "cik": "0000000001",
            "filingDate": stamp.date().isoformat(), "acceptedDate": stamp.strftime("%Y-%m-%d %H:%M:%S"),
            "fiscalYear": str(end.year), "period": period, **values}


def rows(endpoint, period):
    if period == "FY":
        out = [row(endpoint, i, "FY") for i in range(3, len(QUARTER_ENDS), 4)]
    else:
        out = [row(endpoint, i, period) for i in range(len(QUARTER_ENDS)) if f"Q{i % 4 + 1}" == period]
    return sorted(out, key=lambda r: r["date"], reverse=True)


class Response:
    def __init__(self, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else str(payload)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    """requests.Session stand-in: answers the three statement endpoints for SYMBOL; records every call."""

    def __init__(self, data=None, symbols=(SYMBOL,)):
        self.calls = []
        self.data = data
        self.symbols = symbols

    def get(self, url, params=None, timeout=None):
        params = dict(params or {})
        self.calls.append((url, params))
        endpoint = urlparse(url).path.rsplit("/", 1)[-1]
        if endpoint not in STATEMENTS:
            return Response(404, {"Error Message": "unknown endpoint"})
        if params.get("symbol") not in self.symbols:
            return Response(402, text="Premium Query Parameter: 'Special Endpoint : This value set for 'symbol' is "
                                      "not available under your current subscription")
        out = (self.data or rows)(endpoint, params.get("period"))
        return Response(200, out[: int(params.get("limit", 5))])
