import math
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionImpliedVolFactor(CompanySharePortfolioOptionFactor):
    """Portfolio implied volatility derived from implied correlation and constituent option IVs.

    Formula (equal-weight, N constituents):
        A         = (1/N²) * Σ σᵢ²
        B         = (1/N * Σ σᵢ)² − A      [= (Σ wᵢ σᵢ)² − Σ wᵢ² σᵢ²]
        σ_port    = sqrt(A + ρ̄ * B)

    Dependencies:
        CompanyShareOptionImpliedCorrFactor  → ρ̄ (scalar, implied average correlation)
        CompanyShareOptionImpliedVolFactor   → [σ₁ … σ_N] (per-constituent IVs, DependencySpec list)

    Falls back to equal-weight average when ρ̄ is None or unavailable.
    """

    def __init__(
        self,
        name: str = "implied_vol",
        group: str = "volatility",
        subgroup: Optional[str] = "implied",
        data_type: Optional[str] = "numeric",
        source: Optional[str] = "calculated",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        frequency: Optional[str] = "1d",
        **kwargs,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            frequency=frequency,
            **kwargs,
        )

    @property
    def calculate_dependencies(self) -> list:
        from src.domain.entities.factor.dependency_spec import DependencySpec
        from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor import CompanyShareOptionImpliedVolFactor
        return [
            "CompanyShareOptionImpliedCorrFactor",
            DependencySpec(
                factor_type=CompanyShareOptionImpliedVolFactor,
                group="volatility",
                subgroup="implied",
            ),
        ]

    def calculate(self, dependencies: dict) -> Optional[float]:
        rho_raw = dependencies.get("CompanyShareOptionImpliedCorrFactor")
        ivs_raw = dependencies.get("CompanyShareOptionImpliedVolFactor")

        ivs: List[float] = [float(v) for v in (ivs_raw if isinstance(ivs_raw, list) else [ivs_raw]) if v is not None]
        N = len(ivs)
        if N == 0:
            return None

        # Fallback: equal-weight average when correlation is unavailable
        if rho_raw is None or N == 1:
            return sum(ivs) / N

        rho = float(rho_raw)
        w = 1.0 / N
        A = (w ** 2) * sum(s ** 2 for s in ivs)
        B = (w * sum(ivs)) ** 2 - A

        variance = A + rho * B
        if variance <= 0:
            return sum(ivs) / N  # fallback to average on degenerate case

        return math.sqrt(variance)
