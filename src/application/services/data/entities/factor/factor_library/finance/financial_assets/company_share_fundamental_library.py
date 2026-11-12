"""
Company financial statement factors of a CompanyShare (group 'fundamental'), see company_share_fundamental_factor:
    raw FMP fields     CompanyShareFactor, subgroup income_statement | balance_sheet | cash_flow, source 'fmp',
                       name = the FMP field (and the filing's data: date, filingDate, acceptedDate, fiscalYear, period,
                       reportedCurrency, cik)
    calculated         CompanyShareFundamental{Profitability, Leverage, Growth, Valuation}Factor (name = the measure,
                       '_ttm' for trailing twelve months on quarterly statements)
each at the quarterly ('1q') and the annual ('1y') frequency. Keys: '<subgroup>.<name>.<frequency>'.
"""

from typing import Dict

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
    CompanyShareFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_factor import (
    ANNUAL, GROUP, METADATA_FIELDS, QUARTERLY, STATEMENT_FIELDS,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_growth_factor import (
    CompanyShareFundamentalGrowthFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_leverage_factor import (
    CompanyShareFundamentalLeverageFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_profitability_factor import (
    CompanyShareFundamentalProfitabilityFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.fundamental.company_share_fundamental_valuation_factor import (
    CompanyShareFundamentalValuationFactor,
)

FREQUENCIES = (QUARTERLY, ANNUAL)
CALCULATED_FACTORS = (CompanyShareFundamentalProfitabilityFactor, CompanyShareFundamentalLeverageFactor,
                      CompanyShareFundamentalGrowthFactor, CompanyShareFundamentalValuationFactor)
_LABEL = {QUARTERLY: "quarterly", ANNUAL: "annual"}

COMPANY_SHARE_FUNDAMENTAL_LIBRARY: Dict[str, Dict] = {}

for _statement, _fields in STATEMENT_FIELDS.items():
    for _field in tuple(_fields) + tuple(METADATA_FIELDS):
        for _frequency in FREQUENCIES:
            COMPANY_SHARE_FUNDAMENTAL_LIBRARY[f"{_statement}.{_field}.{_frequency}"] = {
                "class": CompanyShareFactor, "name": _field, "group": GROUP, "subgroup": _statement,
                "frequency": _frequency, "data_type": METADATA_FIELDS.get(_field, "numeric"), "source": "fmp",
                "description": f"FMP {_statement.replace('_', ' ')} ({_LABEL[_frequency]}): {_field}, stored at the "
                               f"filing's publication",
                "dependencies": {}, "parameters": {"statement": _statement, "field": _field},
            }

for _cls in CALCULATED_FACTORS:
    for _frequency in FREQUENCIES:
        for _name in _cls.factor_names() + (_cls.factor_names(ttm=True) if _frequency == QUARTERLY else []):
            _factor = _cls(_name, frequency=_frequency)
            if not _factor.usable:
                continue
            COMPANY_SHARE_FUNDAMENTAL_LIBRARY[f"{_cls.KIND}.{_name}.{_frequency}"] = {
                "class": _cls, "name": _name, "group": GROUP, "subgroup": _cls.KIND, "frequency": _frequency,
                "data_type": "numeric", "source": "calculated",
                "description": f"{_factor.definition} ({_LABEL[_frequency]} statements)",
                "dependencies": {}, "parameters": {"measure": _factor.measure, "ttm": _factor.ttm},
            }
