"""DeltaCalculationMethodFactory — name/config-based instantiation of delta methods."""

from __future__ import annotations

from typing import Any, Dict, List, Type

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.bs_minimum_variance_delta import (
    BSMinimumVarianceDelta,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.continuous_rl_hedge_delta import (
    ContinuousRLHedgeDelta,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.delta_calculation_method import (
    DeltaCalculationMethod,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.discrete_rl_hedge_delta import (
    DiscreteRLHedgeDelta,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.vol_forecast_triggered_bs_delta import (
    VolForecastTriggeredBSDelta,
)


class DeltaCalculationMethodFactory:
    """Instantiates DeltaCalculationMethod objects by string name.

    Built-in names
    --------------
    'bs_minimum_variance'    → BSMinimumVarianceDelta
    'discrete_rl'            → DiscreteRLHedgeDelta
    'continuous_rl'          → ContinuousRLHedgeDelta
    'vol_forecast_triggered_bs' → VolForecastTriggeredBSDelta

    Custom methods can be registered at run-time via `register()`.
    All keyword arguments passed to `create()` are forwarded verbatim to
    the class constructor.
    """

    _registry: Dict[str, Type[DeltaCalculationMethod]] = {
        "bs_minimum_variance": BSMinimumVarianceDelta,
        "discrete_rl": DiscreteRLHedgeDelta,
        "continuous_rl": ContinuousRLHedgeDelta,
        "vol_forecast_triggered_bs": VolForecastTriggeredBSDelta,
    }

    @classmethod
    def create(cls, method_name: str, **kwargs: Any) -> DeltaCalculationMethod:
        """Return a new instance of the named method.

        Raises
        ------
        ValueError
            If `method_name` is not registered.
        """
        klass = cls._registry.get(method_name)
        if klass is None:
            raise ValueError(
                f"Unknown delta calculation method '{method_name}'. "
                f"Available: {cls.available_methods()}"
            )
        return klass(**kwargs)

    @classmethod
    def register(
        cls,
        name: str,
        method_class: Type[DeltaCalculationMethod],
    ) -> None:
        """Register a custom DeltaCalculationMethod subclass under `name`.

        Raises
        ------
        TypeError
            If `method_class` is not a subclass of DeltaCalculationMethod.
        """
        if not (isinstance(method_class, type) and issubclass(method_class, DeltaCalculationMethod)):
            raise TypeError(
                f"method_class must be a subclass of DeltaCalculationMethod, got {method_class!r}"
            )
        cls._registry[name] = method_class

    @classmethod
    def available_methods(cls) -> List[str]:
        """Return a sorted list of all registered method names."""
        return sorted(cls._registry.keys())
