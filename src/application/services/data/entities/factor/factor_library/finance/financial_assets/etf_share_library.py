"""
ETF share factors: the ETF's own raw close (IBKR TRADES, daily bars), the ATM option leaf series of the underlyings
(atm_<right>_<field>_<m>m, from the broker's quotes) and the two ETF option dispersion factors:
    ETFShareRealizedDispersionFactor   realized_<right>_<measure>_<1..6>m   (from the closes)
    ETFShareImpliedDispersionFactor    implied_<right>_<measure>_<1..6>m    (from the ATM premium series)
"""

from typing import Dict

from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_dispersion_factor import (
    MONTHS, RIGHTS, dispersion_factor_name,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_factor import ETFShareFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_implied_dispersion_factor import (
    ATM_FIELDS, ETFShareImpliedDispersionFactor, atm_option_series_name,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_realized_dispersion_factor import (
    ETFShareRealizedDispersionFactor,
)

ETF_SHARE_LIBRARY: Dict[str, Dict] = {
    "close": {
        "class": ETFShareFactor, "name": "close", "group": "price", "subgroup": "TRADES", "frequency": "1d",
        "data_type": "numeric", "source": "ibkr", "description": "ETF share daily close (IBKR TRADES bars)",
        "dependencies": {}, "parameters": {},
    },
}

for _right in RIGHTS:
    for _months in MONTHS:
        for _field in ATM_FIELDS:
            _name = atm_option_series_name(_right, _field, _months)
            ETF_SHARE_LIBRARY[_name] = {
                "class": ETFShareFactor, "name": _name, "group": "price", "subgroup": "implied", "frequency": "1d",
                "data_type": "numeric", "source": "ibkr",
                "description": f"ATM {_right} expiring closest to {_months} month(s): {_field} "
                               f"(premium / bid / ask per unit of the underlying's price)",
                "dependencies": {}, "parameters": {"right": _right, "field": _field, "months": _months},
            }
        for _cls in (ETFShareRealizedDispersionFactor, ETFShareImpliedDispersionFactor):
            for _measure in _cls.MEASURES:
                _name = dispersion_factor_name(_cls.KIND, _right, _measure, _months)
                ETF_SHARE_LIBRARY[_name] = {
                    "class": _cls, "name": _name, "group": "dispersion", "subgroup": _cls.KIND, "frequency": "1d",
                    "data_type": "numeric", "source": "calculated",
                    "description": f"ETF {_cls.KIND} ATM {_right} {_measure.replace('_', ' ')} over {_months} "
                                   f"month(s): sum_i w_i x_i - x_ETF, per unit of each instrument's price",
                    "dependencies": {}, "parameters": {"right": _right, "measure": _measure, "months": _months},
                }
