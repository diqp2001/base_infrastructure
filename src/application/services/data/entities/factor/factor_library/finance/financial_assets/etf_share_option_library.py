"""
ETF share option factors: the option's raw quote series (ETFShareOptionFactor, group 'price', subgroup 'quote', one per
quote field, stored at the screen's quote time) and the dispersion strategy factors valued on the ETF option:
    ETFShareOptionNetPremiumFactor           premium_<measure>
    ETFShareOptionReversePremiumFactor       reverse_premium_<measure>
    ETFShareOptionImpliedCorrelationFactor   implied_correlation_<measure>
    ETFShareOptionScenarioPayoffFactor       scenario_<scenario>_<measure>
"""

from typing import Dict

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (
    ETFShareOptionFactor, QUOTE_FIELDS, QUOTE_SUBGROUP,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_implied_correlation_factor import (
    ETFShareOptionImpliedCorrelationFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_net_premium_factor import (
    ETFShareOptionNetPremiumFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_reverse_premium_factor import (
    ETFShareOptionReversePremiumFactor,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_scenario_payoff_factor import (
    ETFShareOptionScenarioPayoffFactor,
)

STRATEGY_FACTORS = (ETFShareOptionNetPremiumFactor, ETFShareOptionReversePremiumFactor,
                    ETFShareOptionImpliedCorrelationFactor, ETFShareOptionScenarioPayoffFactor)

ETF_SHARE_OPTION_LIBRARY: Dict[str, Dict] = {
    _field: {
        "class": ETFShareOptionFactor, "name": _field, "group": "price", "subgroup": QUOTE_SUBGROUP, "frequency": "1d",
        "data_type": "numeric", "source": "ibkr",
        "description": f"ETF option quote at the screen's time: {_field.replace('_', ' ')}",
        "dependencies": {}, "parameters": {"field": _field},
    }
    for _field in QUOTE_FIELDS
}

for _cls in STRATEGY_FACTORS:
    for _measure in _cls.MEASURES:
        _name = _cls.factor_name(_measure)
        ETF_SHARE_OPTION_LIBRARY[_name] = {
            "class": _cls, "name": _name, "group": "dispersion", "subgroup": _cls.KIND, "frequency": "1d",
            "data_type": "numeric", "source": "calculated",
            "description": f"ETF option dispersion strategy, {_cls.KIND.replace('_', ' ')}: {_measure.replace('_', ' ')} "
                           f"(the ETF option sold, the constituent options replicating its holdings bought)",
            "dependencies": {}, "parameters": {"measure": _measure},
        }
