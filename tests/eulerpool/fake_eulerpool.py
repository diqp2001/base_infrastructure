"""A fake Eulerpool API for the tests, answering like the live one (checked 2026-11-13) - in memory only, nothing is
downloaded and no database other than the tests' in-memory SQLite is written.

One company (ACME, CIK 1, fiscal year = calendar year) with three fiscal years (2023-2025) of SEC XBRL facts:
* income statement 10-Q values are the QUARTER, cash flow 10-Q values YEAR-TO-DATE, 10-K values the year;
* one row per (tag, period end, form), from the LATEST filing that repeated it: the original 10-Q / 10-K for the
  latest period of each type, the next year's comparative (filed a year later) for the older ones;
* a 10-K also tags the third quarter's revenue as FY (selected quarterly data) and an 8-K repeats a quarter: both must
  be left out by the normalization.
The canonical values per quarter are those of tests/fmp/fake_fmp (income / balance / cash_flow)."""

from datetime import date, timedelta
from urllib.parse import unquote, urlparse

from tests.fmp.fake_fmp import QUARTER_ENDS, balance, cash_flow, income

SYMBOL = "ACME"
CIK = 1
KEY = "test-eulerpool-key"

IS_TAGS = {"revenue": "Revenues", "costOfRevenue": "CostOfRevenue", "grossProfit": "GrossProfit",
           "operatingIncome": "OperatingIncomeLoss", "netIncome": "NetIncomeLoss", "eps": "EarningsPerShareBasic",
           "epsDiluted": "EarningsPerShareDiluted", "incomeTaxExpense": "IncomeTaxExpenseBenefit"}
BS_TAGS = {"totalAssets": "Assets", "totalStockholdersEquity": "StockholdersEquity",
           "cashAndCashEquivalents": "CashAndCashEquivalentsAtCarryingValue", "longTermDebt": "LongTermDebtNoncurrent",
           "shortTermDebt": "ShortTermBorrowings"}
CF_TAGS = {"operatingCashFlow": "NetCashProvidedByUsedInOperatingActivities",
           "capitalExpenditure": "PaymentsToAcquirePropertyPlantAndEquipment"}
PER_SHARE = {"eps", "epsDiluted"}


def shares_outstanding(i: int) -> float:
    """CommonStockSharesOutstanding at quarter end i (unit 'shares': a count, not an amount); buybacks shrink it."""
    return 1_000_000_000.0 - 5_000_000.0 * i


def original_filed(i: int) -> date:
    """When the period's own filing came out: 10-Q 35 days after the quarter, 10-K 60 days after the year."""
    return QUARTER_ENDS[i] + timedelta(days=60 if i % 4 == 3 else 35)


def filed(i: int) -> date:
    """The filing date Eulerpool shows: the original for the latest period of its type, else the comparative in the
    next year's filing of the same type (a year later)."""
    return original_filed(i) if i + 4 >= len(QUARTER_ENDS) else original_filed(i + 4)


def is_value(field, i):
    return income(i)[field]


def cf_value(field, i):
    """Canonical (FMP-signed) quarter value of a cash flow field: capex is negative."""
    return cash_flow(i)[field]


def cf_tag_value(field, i):
    """The XBRL value: PaymentsToAcquire... is reported positive (cash paid)."""
    v = cf_value(field, i)
    return -v if field == "capitalExpenditure" else v


def _row(tag, end, value, fy, fp, form, filed_on, unit="USD"):
    return {"cik": CIK, "ticker": SYMBOL, "taxonomy": "us-gaap", "tag": tag, "period_end": end.isoformat(),
            "fiscal_year": fy, "fiscal_period": fp, "form": form, "val": f"{value:.4f}", "unit": unit,
            "filed": filed_on.isoformat(), "updated_at": "2026-11-08T19:13:37.862Z"}


def statement_rows(statement, fiscal_period=None):
    out = []
    for i, end in enumerate(QUARTER_ENDS):
        q = i % 4
        year_quarters = range(i - q, i - q + 4)
        if q < 3:
            fp, form = f"Q{q + 1}", "10-Q"
            if statement == "income-statement":
                values = {t: (is_value(f, i), "USD/shares" if f in PER_SHARE else "USD") for f, t in IS_TAGS.items()}
            elif statement == "cash-flow":                      # year to date
                values = {t: (sum(cf_tag_value(f, k) for k in range(i - q, i + 1)), "USD") for f, t in CF_TAGS.items()}
            else:
                values = {t: (balance(i)[f], "USD") for f, t in BS_TAGS.items()}
        else:
            fp, form = "FY", "10-K"
            if statement == "income-statement":
                values = {t: (sum(is_value(f, k) for k in year_quarters), "USD/shares" if f in PER_SHARE else "USD")
                          for f, t in IS_TAGS.items()}
            elif statement == "cash-flow":
                values = {t: (sum(cf_tag_value(f, k) for k in year_quarters), "USD") for f, t in CF_TAGS.items()}
            else:
                values = {t: (balance(i)[f], "USD") for f, t in BS_TAGS.items()}
        fy = end.year if filed(i) == original_filed(i) else end.year + 1
        if statement == "balance-sheet":
            values["CommonStockSharesOutstanding"] = (shares_outstanding(i), "shares")
        for tag, (value, unit) in values.items():
            out.append(_row(tag, end, value, fy, fp, form, filed(i), unit))
        if q == 2 and statement == "income-statement":
            # the next 10-K tags this third quarter's revenue as FY (selected quarterly data)
            out.append(_row("Revenues", end, is_value("revenue", i), end.year, "FY", "10-K", original_filed(i - q + 3)))
            # an 8-K press release (earlier than the 10-Q): never used
            out.append(_row("Revenues", end, 1.0, None, "", "8-K", end + timedelta(days=20)))
        if q == 0 and i > 0 and statement == "balance-sheet":
            # a first-quarter 10-Q also shows the previous fiscal year end's balance: a year-end instant, not a quarter
            out.append(_row("Assets", QUARTER_ENDS[i - 1], 1.0, end.year, "Q1", "10-Q", original_filed(i)))
    if fiscal_period:
        out = [r for r in out if r["fiscal_period"] == fiscal_period]
    return out


RATIOS = {"ticker": SYMBOL, "fiscal_year": 2025, "pe_ratio": None, "pb_ratio": None, "debt_to_equity": 0.5,
          "roe": 12.5, "profit_margin": 15.0}
COMPANY = {"cik": CIK, "ticker": SYMBOL, "company_name": "Acme Corp", "sic": "3571",
           "sic_description": "Electronic Computers", "state": "DE", "fiscal_year_end": "1231"}
ANNUAL_REPORT = {"ticker": SYMBOL, "as_of": "2026-02-28", "updated_at": "2026-03-01", "report": {"items": ["1", "7"]}}


class Response:
    def __init__(self, status_code=200, payload=None, text=None, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else str(payload)
        self.headers = headers or {"x-ratelimit-limit": "100000", "x-ratelimit-remaining": "99999",
                                   "x-ratelimit-window": "month"}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    """requests.Session stand-in for the Fundamentals endpoints of SYMBOL; records every call (url, params, headers)."""

    def __init__(self, symbols=(SYMBOL,), statements=None, key=KEY):
        self.calls = []
        self.symbols = symbols
        self.statements = statements or statement_rows
        self.key = key

    def get(self, url, params=None, headers=None, timeout=None):
        params = dict(params or {})
        self.calls.append((url, params, dict(headers or {})))
        if (headers or {}).get("Authorization") != f"Bearer {self.key}":
            return Response(401, {"error": "Invalid or missing API key"})
        path = urlparse(url).path.split("/api/1/", 1)[-1]
        parts = [unquote(p) for p in path.split("/")]
        if parts[:3] == ["fundamentals", "facts", "search"]:
            if "tag" not in params:
                return Response(400, {"error": "querystring must have required property 'tag'"})
            rows = [r for r in statement_rows("income-statement") if r["tag"] == params["tag"]][-1:]
            return Response(200, [{**r, "cik": None, "fiscal_year": None} for r in rows])
        if parts[:2] == ["fundamentals", "company"]:
            return Response(200, COMPANY) if parts[2] in self.symbols else Response(404, {"error": "Not found"})
        if parts[:2] == ["fundamentals", "annual-report"]:
            return Response(200, ANNUAL_REPORT) if parts[2] in self.symbols else Response(404, {"error": "Not found"})
        if parts[:2] == ["fundamentals", "financials"]:
            if parts[2] not in self.symbols:
                return Response(404, {"error": "Not found"})
            if len(parts) == 3:                 # all XBRL facts (no filing date)
                rows = [r for st in ("income-statement", "balance-sheet", "cash-flow") for r in statement_rows(st)]
                rows = [{k: v for k, v in r.items() if k not in ("filed", "updated_at")} for r in rows
                        if (not params.get("tag") or r["tag"] == params["tag"])]
                return Response(200, rows[: int(params.get("limit", 500))])
            if parts[3] == "ratios":
                return Response(200, RATIOS)
            rows = self.statements(parts[3], params.get("fiscal_period"))
            if params.get("form"):
                rows = [r for r in rows if r["form"] == params["form"]]
            return Response(200, rows[:1000])
        return Response(404, {"error": "Not found"})
