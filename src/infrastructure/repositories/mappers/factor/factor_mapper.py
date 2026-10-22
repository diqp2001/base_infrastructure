"""
Mapper for converting between Factor domain entities and ORM models.
"""

from abc import abstractmethod
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor as CompanyShareOptionFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_factor import CompanyShareOptionImpliedVolFactor as CompanyShareOptionImpliedVolFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_ml_factor import CompanyShareOptionImpliedVolMlFactor as CompanyShareOptionImpliedVolMlFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_value_factor import CompanyShareOptionValueFactor as CompanyShareOptionValueFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_div_yield_factor import CompanyShareOptionImpliedDivYieldFactor as CompanyShareOptionImpliedDivYieldFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_corr_factor import CompanyShareOptionImpliedCorrFactor as CompanyShareOptionImpliedCorrFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_vol_factor import CompanyShareOptionVolFactor as CompanyShareOptionVolFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_var_factor import CompanyShareOptionVarFactor as CompanyShareOptionVarFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_value_factor import CompanySharePortfolioOptionValueFactor as CompanySharePortfolioOptionValueFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_implied_vol_factor import CompanySharePortfolioOptionImpliedVolFactor as CompanySharePortfolioOptionImpliedVolFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_implied_div_yield_factor import CompanySharePortfolioOptionImpliedDivYieldFactor as CompanySharePortfolioOptionImpliedDivYieldFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_factor import IndexFutureOptionFactor as IndexFutureOptionFactorEntity
from src.domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_factor import CompanyShareOptionPortfolioFactor as CompanyShareOptionPortfolioFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor as CompanyShareFactorEntity
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_factor import CompanySharePortfolioFactor as CompanySharePortfolioFactorEntity
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_price_return_factor import CompanySharePortfolioPriceReturnFactor
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_equal_weight_return_factor import CompanySharePortfolioEqualWeightReturnFactor
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_option import CompanyShareOption
from src.domain.entities.finance.financial_assets.derivatives.option.index_future_option import IndexFutureOption
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_portfolio_option import CompanySharePortfolioOption
from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture
from src.infrastructure.models.factor.factor import (
    FactorModel as Factormodel
)
from src.domain.entities.factor.factor import Factor as FactorEntity
from src.domain.entities.factor.continent_factor import ContinentFactor as ContinentFactorEntity
from src.domain.entities.factor.country_factor import CountryFactor as CountryFactorEntity
from src.domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor as FinancialAssetFactorEntity
from src.domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor as SecurityFactorEntity

from src.domain.entities.factor.finance.financial_assets.currency.currency_factor import CurrencyFactor as CurrencyFactorEntity
from src.domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor as EquityFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor as ShareFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor as ShareMomentumFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor as ShareTechnicalFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.share_target_factor import ShareTargetFactor as ShareTargetFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor as ShareVolatilityFactorEntity

# Import additional factor types
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor as BondFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.derivative_factor import DerivativeFactor as DerivativeFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor as OptionFactorEntity  
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor as FutureFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_factor import BondFutureFactor as BondFutureFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_forward_price_factor import BondFutureForwardPriceFactor as BondFutureForwardPriceFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_discounted_value_factor import BondFutureDiscountedValueFactor as BondFutureDiscountedValueFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_annualized_roll_yield_factor import BondFutureAnnualizedRollYieldFactor as BondFutureAnnualizedRollYieldFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_annualized_yield_factor import BondFutureAnnualizedYieldFactor as BondFutureAnnualizedYieldFactorEntity
from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor as IndexFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_factor import IndexFutureFactor as IndexFutureFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_price_return_factor import IndexFuturePriceReturnFactor as IndexFuturePriceReturnFactorEntity
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_price_return_factor import FuturePriceReturnFactor as FuturePriceReturnFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_price_return_factor import CompanySharePriceReturnFactor as CompanySharePriceReturnFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import CompanyShareMidPriceFactor as CompanyShareMidPriceFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import CompanyShareValueFactor as CompanyShareValueFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_avg_turnover_6m_factor import CompanyShareAvgTurnover6mFactor as CompanyShareAvgTurnover6mFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_monthly_price_range_factor import CompanyShareMonthlyPriceRangeFactor as CompanyShareMonthlyPriceRangeFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_vpt_52w_20d_lag_factor import CompanyShareVpt52w20dLagFactor as CompanyShareVpt52w20dLagFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_atm_implied_vol_factor import CompanyShareATMImpliedVolFactor as CompanyShareATMImpliedVolFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_lgbm_cs_quintile_rank_momentum_factor import CompanyShareLGBMCSQuintileRankMomentumFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_momentum_factor import CompanyShareSpatioTemporalMomentumFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_spatio_temporal_feature_factor import CompanyShareSpatioTemporalFeatureFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_cross_sectional_momentum_factor import CompanyShareCrossSectionalMomentumFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_return_factors import (
    CompanyShareReturn1DFactor, CompanyShareReturn5DFactor, CompanyShareReturn10DFactor,
    CompanyShareReturn20DFactor, CompanyShareReturn1MFactor, CompanyShareReturn2MFactor,
    CompanyShareReturn3MFactor, CompanyShareReturn4MFactor, CompanyShareReturn5MFactor,
    CompanyShareReturnYTDFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_ma_factors import (
    CompanySharePriceVsMA5Factor, CompanySharePriceVsMA10Factor, CompanySharePriceVsMA20Factor,
    CompanySharePriceVsMA50Factor, CompanySharePriceVsMA100Factor,
    CompanyShareMA5VsMA10Factor, CompanyShareMA10VsMA20Factor,
    CompanyShareMA20VsMA50Factor, CompanyShareMA50VsMA100Factor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_trend_factors import (
    CompanyShareTrendSlope5DFactor, CompanyShareTrendSlope10DFactor, CompanyShareTrendSlope20DFactor,
    CompanyShareTrendSlope50DFactor, CompanyShareTrendSlope100DFactor,
    CompanyShareMomentumSlope10DFactor, CompanyShareMomentumSlope20DFactor, CompanyShareMomentumSlope50DFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_momentum_change_factors import (
    CompanyShareMomentumAcceleration5D10DFactor, CompanyShareMomentumAcceleration10D20DFactor,
    CompanyShareMomentumAcceleration20D50DFactor,
    CompanyShareReturnChange5DFactor, CompanyShareReturnChange10DFactor, CompanyShareReturnChange20DFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_risk_factors import (
    CompanyShareSharpe10DFactor, CompanyShareSharpe20DFactor, CompanyShareSharpe50DFactor,
    CompanyShareSharpe100DFactor, CompanyShareSortino20DFactor, CompanyShareSortino50DFactor,
    CompanyShareSortino100DFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_drawdown_factors import (
    CompanyShareDistanceFrom5MHighFactor, CompanyShareDistanceFrom5MLowFactor,
    CompanyShareDrawdownFrom5MHighFactor, CompanyShareDaysSince5MHighFactor, CompanyShareDaysSince5MLowFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_composite_momentum_factors import (
    CompanyShareShortTermMomentumFactor, CompanyShareMediumTermMomentumFactor,
    CompanyShareShortVsMediumMomentumFactor, CompanyShareMomentumZScore20DFactor,
    CompanyShareMomentumZScore50DFactor, CompanyShareMomentumZScore100DFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_delta_band_factors import (
    CompanyShareZakamoulineDeltaCeilingFactor, CompanyShareZakamoulineDeltaFloorFactor,
    CompanyShareWhalleyWilmottDeltaCeilingFactor, CompanyShareWhalleyWilmottDeltaFloorFactor,
    CompanyShareZakamoulineCeilingDistanceFactor, CompanyShareZakamoulineFloorDistanceFactor,
    CompanyShareWhalleyWilmottCeilingDistanceFactor, CompanyShareWhalleyWilmottFloorDistanceFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_relative_performance_factors import (
    CompanyShareRelativeReturnVsSpy1DFactor, CompanyShareRelativeReturnVsSpy5DFactor,
    CompanyShareRelativeReturnVsSpy20DFactor, CompanyShareRelativeReturnVsSpy3MFactor,
    CompanyShareRelativeReturnVsSpy6MFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_liquidity_factors import (
    CompanyShareAvgTurnover1mFactor, CompanyShareAvgTurnover2mFactor, CompanyShareAvgTurnover3mFactor,
    CompanyShareAvgTurnover4mFactor, CompanyShareAvgTurnover5mFactor, CompanyShareTurnoverFactor,
    CompanyShareVpt16w20dLagFactor, CompanyShareMaxDailyReturn6mFactor, CompanyShareMinReturn120dFactor,
)
from src.domain.entities.factor.finance.financial_assets.currency.currency_value_factor import CurrencyValueFactor as CurrencyValueFactorEntity
from src.domain.entities.factor.finance.financial_assets.currency.currency_rate_factor import CurrencyRateFactor as CurrencyRateFactorEntity
from src.domain.entities.factor.finance.financial_assets.currency.currency_yield_factor import CurrencyYieldFactor as CurrencyYieldFactorEntity

# Import portfolio and holding value factors
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_value_factor import CompanySharePortfolioValueFactor as CompanySharePortfolioValueFactorEntity
from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_value_factor import CompanySharePortfolioHoldingValueFactor as CompanySharePortfolioHoldingValueFactorEntity
from src.domain.entities.factor.finance.holding.company_share_option_portfolio.company_share_option_portfolio_holding_value_factor import CompanyShareOptionPortfolioHoldingValueFactor as CompanyShareOptionPortfolioHoldingValueFactorEntity
from src.domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_value_factor import CompanyShareOptionPortfolioValueFactor as CompanyShareOptionPortfolioValueFactorEntity
from src.domain.entities.factor.finance.holding.company_share_option_portfolio_portfolio.company_share_option_portfolio_portfolio_holding_value_factor import CompanyShareOptionPortfolioPortfolioHoldingValueFactor as CompanyShareOptionPortfolioPortfolioHoldingValueFactorEntity

# Import position, transaction, and order factors
from src.domain.entities.factor.finance.position.company_share_position_value_factor import CompanySharePositionValueFactor as CompanySharePositionValueFactorEntity
from src.domain.entities.factor.finance.transaction.company_share_transaction_value_factor import CompanyShareTransactionValueFactor as CompanyShareTransactionValueFactorEntity
from src.domain.entities.factor.finance.order.company_share_order_quantity_factor import CompanyShareOrderQuantityFactor as CompanyShareOrderQuantityFactorEntity
from src.domain.entities.factor.finance.order.company_share_order_price_factor import CompanyShareOrderPriceFactor as CompanyShareOrderPriceFactorEntity

# Import portfolio value factor
from src.domain.entities.factor.finance.portfolio.portfolio_value_factor import PortfolioValueFactor as PortfolioValueFactorEntity
from src.domain.entities.factor.constituent_score_factor import ConstituentScoreFactor as ConstituentScoreFactorEntity

# Import corresponding entity types for mapping
from src.domain.entities.continent import Continent
from src.domain.entities.country import Country
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from src.domain.entities.finance.financial_assets.security import Security
from src.domain.entities.finance.financial_assets.index.index import Index
from src.domain.entities.finance.financial_assets.index.index_bond import IndexBond
from src.domain.entities.finance.financial_assets.index.index_company_share import IndexCompanyShare
from src.domain.entities.finance.financial_assets.index.index_company_share_portfolio import IndexCompanySharePortfolio
from src.domain.entities.finance.financial_assets.currency import Currency
from src.domain.entities.finance.financial_assets.equity import Equity
from src.domain.entities.finance.financial_assets.share.share import Share
from src.domain.entities.finance.financial_assets.bond import Bond
from src.domain.entities.finance.financial_assets.derivatives.derivative import Derivative
from src.domain.entities.finance.financial_assets.derivatives.option.option import Option
from src.domain.entities.finance.financial_assets.derivatives.future.future import Future
from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture


# Factor Entity to Entity Type Mapping Dictionary
FACTOR_ENTITY_MAPPING = {
    # Geographic factors
    ContinentFactorEntity: Continent,
    CountryFactorEntity: Country,
    
    # Financial asset factors
    FinancialAssetFactorEntity: FinancialAsset,
    SecurityFactorEntity: Security,
    IndexFactorEntity: Index,
    CurrencyFactorEntity: Currency,
    EquityFactorEntity: Equity,
    
    # Share factors
    ShareFactorEntity: Share,
    ShareMomentumFactorEntity: Share,
    ShareTechnicalFactorEntity: Share,
    ShareTargetFactorEntity: Share,
    ShareVolatilityFactorEntity: Share,
    
    # Bond factors
    BondFactorEntity: Bond,
    
    # Derivative factors
    DerivativeFactorEntity: Derivative,
    OptionFactorEntity: Option,
    FutureFactorEntity: Future,
    IndexFutureFactorEntity: IndexFuture,
}
ENTITY_FACTOR_MAPPING = {
    Continent: [
        ContinentFactorEntity
    ],
    
    Country: [
        CountryFactorEntity
    ],
    
    FinancialAsset: [
        FinancialAssetFactorEntity
    ],
    
    Security: [
        SecurityFactorEntity
    ],
    
    Index: [
        IndexFactorEntity
    ],

    IndexBond: [
        IndexFactorEntity
    ],

    IndexCompanyShare: [
        IndexFactorEntity
    ],

    IndexCompanySharePortfolio: [
        IndexFactorEntity
    ],
    
    Currency: [
        CurrencyFactorEntity
    ],
    
    Equity: [
        EquityFactorEntity
    ],
    
    Share: [
        ShareFactorEntity
    ],
    CompanyShare: [
        CompanyShareFactorEntity
    ],
    IndexFutureOption: [
        IndexFutureOptionFactorEntity
    ],
    CompanyShareOption: [
        CompanyShareOptionFactorEntity
    ],
    CompanySharePortfolioOption: [
        CompanyShareOptionPortfolioFactorEntity
    ],
    CompanySharePortfolio: [
        CompanySharePortfolioFactorEntity
    ],
    
    Bond: [
        BondFactorEntity
    ],
    
    Derivative: [
        DerivativeFactorEntity
    ],
    
    Option: [
        OptionFactorEntity
    ],
    
    Future: [
        FutureFactorEntity
    ],

    BondFuture: [
        BondFutureFactorEntity
    ],

    IndexFuture: [
        IndexFutureFactorEntity
    ],

}

# Backtest entities are registered at runtime via local import to avoid circular deps.

# Discriminator string → factor domain class.  Used by the resolution service to
# recover the true class when type(factor_entity) returns GenericFactor (missing elif).
DISCRIMINATOR_CLASS_MAP: dict = {
    'continent': ContinentFactorEntity,
    'country': CountryFactorEntity,
    'financial_asset': FinancialAssetFactorEntity,
    'security': SecurityFactorEntity,
    'index': IndexFactorEntity,
    'index_factor': IndexFactorEntity,
    'bond_future_factor': BondFutureFactorEntity,
    'bond_future_forward_price_factor': BondFutureForwardPriceFactorEntity,
    'bond_future_discounted_value_factor': BondFutureDiscountedValueFactorEntity,
    'bond_future_annualized_roll_yield_factor': BondFutureAnnualizedRollYieldFactorEntity,
    'bond_future_annualized_yield_factor': BondFutureAnnualizedYieldFactorEntity,
    'index_future_factor': IndexFutureFactorEntity,
    'index_future_price_return_factor': IndexFuturePriceReturnFactorEntity,
    'future_price_return_factor': FuturePriceReturnFactorEntity,
    'company_share_factor': CompanyShareFactorEntity,
    'company_share_price_return_factor': CompanySharePriceReturnFactorEntity,
    'company_share_mid_price_factor': CompanyShareMidPriceFactorEntity,
    'company_share_value_factor': CompanyShareValueFactorEntity,
    'company_share_avg_turnover_6m_factor': CompanyShareAvgTurnover6mFactorEntity,
    'company_share_monthly_price_range_factor': CompanyShareMonthlyPriceRangeFactorEntity,
    'company_share_vpt_52w_20d_lag_factor': CompanyShareVpt52w20dLagFactorEntity,
    'company_share_atm_implied_vol_factor': CompanyShareATMImpliedVolFactorEntity,
    'currency_value_factor': CurrencyValueFactorEntity,
    'currency_rate_factor': CurrencyRateFactorEntity,
    'currency_yield_factor': CurrencyYieldFactorEntity,
    'index_future_option_factor': IndexFutureOptionFactorEntity,
    'company_share_option_factor': CompanyShareOptionFactorEntity,
    'company_share_option_value_factor': CompanyShareOptionValueFactorEntity,
    'company_share_option_implied_vol_factor': CompanyShareOptionImpliedVolFactorEntity,
    'company_share_option_implied_vol_ml_factor': CompanyShareOptionImpliedVolMlFactorEntity,
    'company_share_option_implied_div_yield_factor': CompanyShareOptionImpliedDivYieldFactorEntity,
    'company_share_option_implied_corr_factor': CompanyShareOptionImpliedCorrFactorEntity,
    'company_share_option_vol_factor': CompanyShareOptionVolFactorEntity,
    'company_share_option_var_factor': CompanyShareOptionVarFactorEntity,
    'company_share_portfolio_factor': CompanySharePortfolioFactorEntity,
    'company_share_portfolio_price_return_factor': CompanySharePortfolioPriceReturnFactor,
    'company_share_portfolio_equal_weight_return_factor': CompanySharePortfolioEqualWeightReturnFactor,
    'company_share_portfolio_option_factor': CompanyShareOptionPortfolioFactorEntity,
    'company_share_portfolio_option_value_factor': CompanySharePortfolioOptionValueFactorEntity,
    'company_share_portfolio_option_implied_vol_factor': CompanySharePortfolioOptionImpliedVolFactorEntity,
    'company_share_portfolio_option_implied_div_yield_factor': CompanySharePortfolioOptionImpliedDivYieldFactorEntity,
    'currency': CurrencyFactorEntity,
    'equity': EquityFactorEntity,
    'share': ShareFactorEntity,
    'share_momentum': ShareMomentumFactorEntity,
    'share_technical': ShareTechnicalFactorEntity,
    'share_target': ShareTargetFactorEntity,
    'share_volatility': ShareVolatilityFactorEntity,
    'portfolio_company_share_value': CompanySharePortfolioValueFactorEntity,
    'portfolio_company_share_holding_value': CompanySharePortfolioHoldingValueFactorEntity,
    'company_share_option_portfolio_holding_value_factor': CompanyShareOptionPortfolioHoldingValueFactorEntity,
    'company_share_option_portfolio_value_factor': CompanyShareOptionPortfolioValueFactorEntity,
    'company_share_option_portfolio_portfolio_holding_value_factor': CompanyShareOptionPortfolioPortfolioHoldingValueFactorEntity,
    'company_share_position_value_factor': CompanySharePositionValueFactorEntity,
    'company_share_transaction_value_factor': CompanyShareTransactionValueFactorEntity,
    'company_share_order_quantity_factor': CompanyShareOrderQuantityFactorEntity,
    'company_share_order_price_factor': CompanyShareOrderPriceFactorEntity,
    'portfolio_value_factor': PortfolioValueFactorEntity,
    'constituent_score_factor': ConstituentScoreFactorEntity,
    # Technical / Momentum — Returns
    'company_share_return_1d_factor': CompanyShareReturn1DFactor,
    'company_share_return_5d_factor': CompanyShareReturn5DFactor,
    'company_share_return_10d_factor': CompanyShareReturn10DFactor,
    'company_share_return_20d_factor': CompanyShareReturn20DFactor,
    'company_share_return_1m_factor': CompanyShareReturn1MFactor,
    'company_share_return_2m_factor': CompanyShareReturn2MFactor,
    'company_share_return_3m_factor': CompanyShareReturn3MFactor,
    'company_share_return_4m_factor': CompanyShareReturn4MFactor,
    'company_share_return_5m_factor': CompanyShareReturn5MFactor,
    'company_share_return_ytd_factor': CompanyShareReturnYTDFactor,
    # Technical / Momentum — Moving Averages
    'company_share_price_vs_ma_5_factor': CompanySharePriceVsMA5Factor,
    'company_share_price_vs_ma_10_factor': CompanySharePriceVsMA10Factor,
    'company_share_price_vs_ma_20_factor': CompanySharePriceVsMA20Factor,
    'company_share_price_vs_ma_50_factor': CompanySharePriceVsMA50Factor,
    'company_share_price_vs_ma_100_factor': CompanySharePriceVsMA100Factor,
    'company_share_ma_5_vs_ma_10_factor': CompanyShareMA5VsMA10Factor,
    'company_share_ma_10_vs_ma_20_factor': CompanyShareMA10VsMA20Factor,
    'company_share_ma_20_vs_ma_50_factor': CompanyShareMA20VsMA50Factor,
    'company_share_ma_50_vs_ma_100_factor': CompanyShareMA50VsMA100Factor,
    # Technical / Momentum — Trend Slopes
    'company_share_trend_slope_5d_factor': CompanyShareTrendSlope5DFactor,
    'company_share_trend_slope_10d_factor': CompanyShareTrendSlope10DFactor,
    'company_share_trend_slope_20d_factor': CompanyShareTrendSlope20DFactor,
    'company_share_trend_slope_50d_factor': CompanyShareTrendSlope50DFactor,
    'company_share_trend_slope_100d_factor': CompanyShareTrendSlope100DFactor,
    'company_share_momentum_slope_10d_factor': CompanyShareMomentumSlope10DFactor,
    'company_share_momentum_slope_20d_factor': CompanyShareMomentumSlope20DFactor,
    'company_share_momentum_slope_50d_factor': CompanyShareMomentumSlope50DFactor,
    # Technical / Momentum — Acceleration & Change
    'company_share_momentum_accel_5d_10d_factor': CompanyShareMomentumAcceleration5D10DFactor,
    'company_share_momentum_accel_10d_20d_factor': CompanyShareMomentumAcceleration10D20DFactor,
    'company_share_momentum_accel_20d_50d_factor': CompanyShareMomentumAcceleration20D50DFactor,
    'company_share_return_change_5d_factor': CompanyShareReturnChange5DFactor,
    'company_share_return_change_10d_factor': CompanyShareReturnChange10DFactor,
    'company_share_return_change_20d_factor': CompanyShareReturnChange20DFactor,
    # Technical / Momentum — Risk
    'company_share_sharpe_10d_factor': CompanyShareSharpe10DFactor,
    'company_share_sharpe_20d_factor': CompanyShareSharpe20DFactor,
    'company_share_sharpe_50d_factor': CompanyShareSharpe50DFactor,
    'company_share_sharpe_100d_factor': CompanyShareSharpe100DFactor,
    'company_share_sortino_20d_factor': CompanyShareSortino20DFactor,
    'company_share_sortino_50d_factor': CompanyShareSortino50DFactor,
    'company_share_sortino_100d_factor': CompanyShareSortino100DFactor,
    # Technical / Momentum — Drawdown / Distance
    'company_share_distance_from_5m_high_factor': CompanyShareDistanceFrom5MHighFactor,
    'company_share_distance_from_5m_low_factor': CompanyShareDistanceFrom5MLowFactor,
    'company_share_drawdown_from_5m_high_factor': CompanyShareDrawdownFrom5MHighFactor,
    'company_share_days_since_5m_high_factor': CompanyShareDaysSince5MHighFactor,
    'company_share_days_since_5m_low_factor': CompanyShareDaysSince5MLowFactor,
    # Technical / Momentum — Composite
    'company_share_short_term_momentum_factor': CompanyShareShortTermMomentumFactor,
    'company_share_medium_term_momentum_factor': CompanyShareMediumTermMomentumFactor,
    'company_share_short_vs_medium_momentum_factor': CompanyShareShortVsMediumMomentumFactor,
    'company_share_momentum_zscore_20d_factor': CompanyShareMomentumZScore20DFactor,
    'company_share_momentum_zscore_50d_factor': CompanyShareMomentumZScore50DFactor,
    'company_share_momentum_zscore_100d_factor': CompanyShareMomentumZScore100DFactor,
    'company_share_zakamouline_delta_ceiling_factor': CompanyShareZakamoulineDeltaCeilingFactor,
    'company_share_zakamouline_delta_floor_factor': CompanyShareZakamoulineDeltaFloorFactor,
    'company_share_whalley_wilmott_delta_ceiling_factor': CompanyShareWhalleyWilmottDeltaCeilingFactor,
    'company_share_whalley_wilmott_delta_floor_factor': CompanyShareWhalleyWilmottDeltaFloorFactor,
    'company_share_zakamouline_ceiling_distance_factor': CompanyShareZakamoulineCeilingDistanceFactor,
    'company_share_zakamouline_floor_distance_factor': CompanyShareZakamoulineFloorDistanceFactor,
    'company_share_whalley_wilmott_ceiling_distance_factor': CompanyShareWhalleyWilmottCeilingDistanceFactor,
    'company_share_whalley_wilmott_floor_distance_factor': CompanyShareWhalleyWilmottFloorDistanceFactor,
    'company_share_relative_return_vs_spy_1d_factor': CompanyShareRelativeReturnVsSpy1DFactor,
    'company_share_relative_return_vs_spy_5d_factor': CompanyShareRelativeReturnVsSpy5DFactor,
    'company_share_relative_return_vs_spy_20d_factor': CompanyShareRelativeReturnVsSpy20DFactor,
    'company_share_relative_return_vs_spy_3m_factor': CompanyShareRelativeReturnVsSpy3MFactor,
    'company_share_relative_return_vs_spy_6m_factor': CompanyShareRelativeReturnVsSpy6MFactor,
    'company_share_avg_turnover_1m_factor': CompanyShareAvgTurnover1mFactor,
    'company_share_avg_turnover_2m_factor': CompanyShareAvgTurnover2mFactor,
    'company_share_avg_turnover_3m_factor': CompanyShareAvgTurnover3mFactor,
    'company_share_avg_turnover_4m_factor': CompanyShareAvgTurnover4mFactor,
    'company_share_avg_turnover_5m_factor': CompanyShareAvgTurnover5mFactor,
    'company_share_turnover_factor': CompanyShareTurnoverFactor,
    'company_share_vpt_16w_20d_lag_factor': CompanyShareVpt16w20dLagFactor,
    'company_share_max_daily_return_6m_factor': CompanyShareMaxDailyReturn6mFactor,
    'company_share_min_return_120d_factor': CompanyShareMinReturn120dFactor,
    'company_share_lgbm_cs_quintile_rank_momentum_factor': CompanyShareLGBMCSQuintileRankMomentumFactor,
    'company_share_spatio_temporal_momentum_factor': CompanyShareSpatioTemporalMomentumFactor,
    'company_share_spatio_temporal_feature_factor': CompanyShareSpatioTemporalFeatureFactor,
    'company_share_cross_sectional_momentum_factor': CompanyShareCrossSectionalMomentumFactor,
}

# Lazy entries to avoid circular imports at module load time.
try:
    from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rf_yield_factor import CompanyShareOptionRFYieldFactor as _RFYieldCls
    DISCRIMINATOR_CLASS_MAP['company_share_option_rf_yield_factor'] = _RFYieldCls
except ImportError:
    pass

try:
    from src.domain.entities.factor.backtest.backtest_factor import BacktestFactor as _BacktestCls
    DISCRIMINATOR_CLASS_MAP['backtest_factor'] = _BacktestCls
except ImportError:
    pass

# Factor families whose factor_type had no to_domain branch (they decoded as GenericFactor and
# lost calculate / calculate_dependencies). Registered lazily, like the entries above.
_LAZY_DISCRIMINATORS = {
    'company_share_option_bates_price_factor': 'src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_bates_price_factor:CompanyShareOptionBatesPriceFactor',
    'company_share_option_black_scholes_merton_price_factor': 'src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_black_scholes_merton_price_factor:CompanyShareOptionBlackScholesMertonPriceFactor',
    'company_share_option_cox_ross_rubinstein_price_factor': 'src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_cox_ross_rubinstein_price_factor:CompanyShareOptionCoxRossRubinsteinPriceFactor',
    'company_share_option_dupire_local_volatility_price_factor': 'src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_dupire_local_volatility_price_factor:CompanyShareOptionDupireLocalVolatilityPriceFactor',
    'company_share_option_heston_price_factor': 'src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_heston_price_factor:CompanyShareOptionHestonPriceFactor',
    'company_share_option_heston_slv_price_factor': 'src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_heston_slv_price_factor:CompanyShareOptionHestonSLVPriceFactor',
    'company_share_option_hull_white_price_factor': 'src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_hull_white_price_factor:CompanyShareOptionHullWhitePriceFactor',
    'company_share_option_sabr_price_factor': 'src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_sabr_price_factor:CompanyShareOptionSABRPriceFactor',
    'company_share_option_mid_price_factor': 'src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_mid_price_factor:CompanyShareOptionMidPriceFactor',
    'company_share_portfolio_holding_value_factor': 'src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_value_factor:CompanySharePortfolioHoldingValueFactor',
    'company_share_portfolio_portfolio_holding_value_factor': 'src.domain.entities.factor.finance.holding.company_share_portfolio_portfolio.company_share_portfolio_portfolio_holding_value_factor:CompanySharePortfolioPortfolioHoldingValueFactor',
    'currency_portfolio_holding_value_factor': 'src.domain.entities.factor.finance.holding.currency_portfolio_holding_value_factor:CurrencyPortfolioHoldingValueFactor',
    'currency_portfolio_portfolio_holding_value_factor': 'src.domain.entities.factor.finance.holding.currency_portfolio_portfolio.currency_portfolio_portfolio_holding_value_factor:CurrencyPortfolioPortfolioHoldingValueFactor',
    'portfolio_holding_value_factor': 'src.domain.entities.factor.finance.holding.portfolio_holding_value_factor:PortfolioHoldingValueFactor',
    'company_share_portfolio_value_factor': 'src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_value_factor:CompanySharePortfolioValueFactor',
    'currency_portfolio_value_factor': 'src.domain.entities.factor.finance.portfolio.currency_portfolio_value_factor:CurrencyPortfolioValueFactor',
}
for _disc, _target in _LAZY_DISCRIMINATORS.items():
    if _disc in DISCRIMINATOR_CLASS_MAP:
        continue
    try:
        import importlib as _importlib
        _mod, _cls = _target.split(':')
        DISCRIMINATOR_CLASS_MAP[_disc] = getattr(_importlib.import_module(_mod), _cls)
    except (ImportError, AttributeError):
        pass



def _get_entity_type_from_factor(factor) -> str:
    """
    Helper function to determine entity_type from factor type.
    This avoids circular dependency with FactorCalculationService.
    """
    factor_class_name = factor.__class__.__name__
    
    # Map factor types to entity types
    if any(share_type in factor_class_name for share_type in ['Share', 'share']):
        return 'share'
    elif any(equity_type in factor_class_name for equity_type in ['Equity', 'equity']):
        return 'equity'
    elif any(country_type in factor_class_name for country_type in ['Country', 'country']):
        return 'country'
    elif any(continent_type in factor_class_name for continent_type in ['Continent', 'continent']):
        return 'continent'
    elif any(index_type in factor_class_name for index_type in ['Index', 'index']):
        return 'index'
    elif any(currency_type in factor_class_name for currency_type in ['Currency', 'currency']):
        return 'currency'



class FactorMapper:
    """Mapper for Factor domain entity and ORM model conversion."""
    @abstractmethod
    def get_factor_model(self):
        return Factormodel
    
    @abstractmethod
    def get_factor_entity(self):
        return FactorEntity

    
    @staticmethod
    def to_domain(orm_model: Optional[Factormodel]) -> Optional[FactorEntity]:
        """Convert ORM model to domain entity based on factor_type discriminator."""
        if not orm_model:
            return None
        
        # Map based on discriminator type
        factor_type = orm_model.factor_type
        base_args = {
            'name': orm_model.name,
            'group': orm_model.group,
            'subgroup': orm_model.subgroup,
            'frequency': orm_model.frequency,
            'data_type': orm_model.data_type,
            'source': orm_model.source,
            'definition': orm_model.definition,
            'factor_id': orm_model.id,
        }
        
        if factor_type == 'continent':
            return ContinentFactorEntity(
                **base_args,
            )
        elif factor_type == 'country':
            return CountryFactorEntity(
                **base_args,
               
            )
        elif factor_type == 'financial_asset':
            return FinancialAssetFactorEntity(
                **base_args,
            )
        elif factor_type == 'security':
            return SecurityFactorEntity(
                **base_args,
                
            )
        elif factor_type in ('index', 'index_factor'):
            return IndexFactorEntity(
                **base_args,
            )
        elif factor_type == 'index_future_factor':
            return IndexFutureFactorEntity(**base_args)
        elif factor_type == 'bond_future_factor':
            return BondFutureFactorEntity(**base_args)
        elif factor_type == 'bond_future_forward_price_factor':
            return BondFutureForwardPriceFactorEntity(**base_args)
        elif factor_type == 'bond_future_discounted_value_factor':
            return BondFutureDiscountedValueFactorEntity(**base_args)
        elif factor_type == 'bond_future_annualized_roll_yield_factor':
            return BondFutureAnnualizedRollYieldFactorEntity(**base_args)
        elif factor_type == 'bond_future_annualized_yield_factor':
            return BondFutureAnnualizedYieldFactorEntity(**base_args)
        elif factor_type == 'index_future_price_return_factor':
            return IndexFuturePriceReturnFactorEntity(**base_args)
        elif factor_type == 'future_price_return_factor':
            return FuturePriceReturnFactorEntity(**base_args)
        elif factor_type == 'company_share_factor':
            return CompanyShareFactorEntity(**base_args)
        elif factor_type == 'company_share_price_return_factor':
            return CompanySharePriceReturnFactorEntity(**base_args)
        elif factor_type == 'company_share_mid_price_factor':
            return CompanyShareMidPriceFactorEntity(**base_args)
        elif factor_type == 'company_share_value_factor':
            return CompanyShareValueFactorEntity(**base_args)
        elif factor_type == 'company_share_avg_turnover_6m_factor':
            return CompanyShareAvgTurnover6mFactorEntity(**base_args)
        elif factor_type == 'company_share_monthly_price_range_factor':
            return CompanyShareMonthlyPriceRangeFactorEntity(**base_args)
        elif factor_type == 'company_share_vpt_52w_20d_lag_factor':
            return CompanyShareVpt52w20dLagFactorEntity(**base_args)
        elif factor_type == 'company_share_atm_implied_vol_factor':
            return CompanyShareATMImpliedVolFactorEntity(**base_args)
        elif factor_type == 'currency_value_factor':
            return CurrencyValueFactorEntity(**base_args)
        elif factor_type == 'currency_rate_factor':
            return CurrencyRateFactorEntity(**base_args)
        elif factor_type == 'currency_yield_factor':
            return CurrencyYieldFactorEntity(**base_args)
        elif factor_type == 'index_future_option_factor':
            return IndexFutureOptionFactorEntity(**base_args)
        elif factor_type == 'company_share_option_factor':
            return CompanyShareOptionFactorEntity(**base_args)
        elif factor_type == 'company_share_portfolio_factor':
            return CompanySharePortfolioFactorEntity(**base_args)
        elif factor_type == 'company_share_portfolio_price_return_factor':
            return CompanySharePortfolioPriceReturnFactor(**base_args)
        elif factor_type == 'company_share_portfolio_equal_weight_return_factor':
            return CompanySharePortfolioEqualWeightReturnFactor(**base_args)
        elif factor_type == 'company_share_portfolio_option_factor':
            return CompanyShareOptionPortfolioFactorEntity(**base_args)
        elif factor_type == 'company_share_portfolio_option_value_factor':
            return CompanySharePortfolioOptionValueFactorEntity(**base_args)
        elif factor_type == 'company_share_portfolio_option_implied_vol_factor':
            return CompanySharePortfolioOptionImpliedVolFactorEntity(**base_args)
        elif factor_type == 'company_share_portfolio_option_implied_div_yield_factor':
            return CompanySharePortfolioOptionImpliedDivYieldFactorEntity(**base_args)
        elif factor_type == 'company_share_option_value_factor':
            return CompanyShareOptionValueFactorEntity(**base_args)
        elif factor_type == 'company_share_option_implied_vol_factor':
            return CompanyShareOptionImpliedVolFactorEntity(**base_args)
        elif factor_type == 'company_share_option_implied_vol_ml_factor':
            return CompanyShareOptionImpliedVolMlFactorEntity(**base_args)
        elif factor_type == 'company_share_option_implied_div_yield_factor':
            return CompanyShareOptionImpliedDivYieldFactorEntity(**base_args)
        elif factor_type == 'company_share_option_rf_yield_factor':
            from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rf_yield_factor import CompanyShareOptionRFYieldFactor as CompanyShareOptionRFYieldFactorEntity
            return CompanyShareOptionRFYieldFactorEntity(**base_args)
        elif factor_type == 'company_share_option_implied_corr_factor':
            return CompanyShareOptionImpliedCorrFactorEntity(**base_args)
        elif factor_type == 'company_share_option_delta_factor':
            from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_delta_factor import CompanyShareOptionDeltaFactor as _CSODelta
            return _CSODelta(**base_args)
        elif factor_type == 'company_share_option_rho_factor':
            from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rho_factor import CompanyShareOptionRhoFactor as _CSORho
            return _CSORho(**base_args)
        elif factor_type == 'company_share_option_gamma_factor':
            from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_gamma_factor import CompanyShareOptionGammaFactor as _CSOGamma
            return _CSOGamma(**base_args)
        elif factor_type == 'company_share_option_vega_factor':
            from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_vega_factor import CompanyShareOptionVegaFactor as _CSOVega
            return _CSOVega(**base_args)
        elif factor_type == 'company_share_option_vol_factor':
            return CompanyShareOptionVolFactorEntity(**base_args)
        elif factor_type == 'company_share_option_var_factor':
            return CompanyShareOptionVarFactorEntity(**base_args)
        elif factor_type == 'company_share_option_portfolio_holding_value_factor':
            return CompanyShareOptionPortfolioHoldingValueFactorEntity(**base_args)
        elif factor_type == 'company_share_option_portfolio_value_factor':
            return CompanyShareOptionPortfolioValueFactorEntity(**base_args)
        elif factor_type == 'company_share_option_portfolio_portfolio_holding_value_factor':
            return CompanyShareOptionPortfolioPortfolioHoldingValueFactorEntity(**base_args)
        elif factor_type == 'currency':
            return CurrencyFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'equity':
            return EquityFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'share':
            return ShareFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'share_momentum':
            return ShareMomentumFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'share_technical':
            return ShareTechnicalFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'share_target':
            return ShareTargetFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'share_volatility':
            return ShareVolatilityFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'portfolio_company_share_value':
            return CompanySharePortfolioValueFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'portfolio_company_share_holding_value':
            return CompanySharePortfolioHoldingValueFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'company_share_position_value_factor':
            return CompanySharePositionValueFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'company_share_transaction_value_factor':
            return CompanyShareTransactionValueFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'company_share_order_quantity_factor':
            return CompanyShareOrderQuantityFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'company_share_order_price_factor':
            return CompanyShareOrderPriceFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'portfolio_value_factor':
            return PortfolioValueFactorEntity(
                **base_args,

            )
        elif factor_type == 'constituent_score_factor':
            return ConstituentScoreFactorEntity(**base_args)
        elif factor_type == 'backtest_factor':
            from src.domain.entities.factor.backtest.backtest_factor import BacktestFactor
            return BacktestFactor(**base_args)
        # ── Technical / Momentum — Returns ──────────────────────────────────
        elif factor_type == 'company_share_return_1d_factor':
            return CompanyShareReturn1DFactor(**base_args)
        elif factor_type == 'company_share_return_5d_factor':
            return CompanyShareReturn5DFactor(**base_args)
        elif factor_type == 'company_share_return_10d_factor':
            return CompanyShareReturn10DFactor(**base_args)
        elif factor_type == 'company_share_return_20d_factor':
            return CompanyShareReturn20DFactor(**base_args)
        elif factor_type == 'company_share_return_1m_factor':
            return CompanyShareReturn1MFactor(**base_args)
        elif factor_type == 'company_share_return_2m_factor':
            return CompanyShareReturn2MFactor(**base_args)
        elif factor_type == 'company_share_return_3m_factor':
            return CompanyShareReturn3MFactor(**base_args)
        elif factor_type == 'company_share_return_4m_factor':
            return CompanyShareReturn4MFactor(**base_args)
        elif factor_type == 'company_share_return_5m_factor':
            return CompanyShareReturn5MFactor(**base_args)
        elif factor_type == 'company_share_return_ytd_factor':
            return CompanyShareReturnYTDFactor(**base_args)
        # ── Technical / Momentum — Moving Averages ───────────────────────────
        elif factor_type == 'company_share_price_vs_ma_5_factor':
            return CompanySharePriceVsMA5Factor(**base_args)
        elif factor_type == 'company_share_price_vs_ma_10_factor':
            return CompanySharePriceVsMA10Factor(**base_args)
        elif factor_type == 'company_share_price_vs_ma_20_factor':
            return CompanySharePriceVsMA20Factor(**base_args)
        elif factor_type == 'company_share_price_vs_ma_50_factor':
            return CompanySharePriceVsMA50Factor(**base_args)
        elif factor_type == 'company_share_price_vs_ma_100_factor':
            return CompanySharePriceVsMA100Factor(**base_args)
        elif factor_type == 'company_share_ma_5_vs_ma_10_factor':
            return CompanyShareMA5VsMA10Factor(**base_args)
        elif factor_type == 'company_share_ma_10_vs_ma_20_factor':
            return CompanyShareMA10VsMA20Factor(**base_args)
        elif factor_type == 'company_share_ma_20_vs_ma_50_factor':
            return CompanyShareMA20VsMA50Factor(**base_args)
        elif factor_type == 'company_share_ma_50_vs_ma_100_factor':
            return CompanyShareMA50VsMA100Factor(**base_args)
        # ── Technical / Momentum — Trend Slopes ──────────────────────────────
        elif factor_type == 'company_share_trend_slope_5d_factor':
            return CompanyShareTrendSlope5DFactor(**base_args)
        elif factor_type == 'company_share_trend_slope_10d_factor':
            return CompanyShareTrendSlope10DFactor(**base_args)
        elif factor_type == 'company_share_trend_slope_20d_factor':
            return CompanyShareTrendSlope20DFactor(**base_args)
        elif factor_type == 'company_share_trend_slope_50d_factor':
            return CompanyShareTrendSlope50DFactor(**base_args)
        elif factor_type == 'company_share_trend_slope_100d_factor':
            return CompanyShareTrendSlope100DFactor(**base_args)
        elif factor_type == 'company_share_momentum_slope_10d_factor':
            return CompanyShareMomentumSlope10DFactor(**base_args)
        elif factor_type == 'company_share_momentum_slope_20d_factor':
            return CompanyShareMomentumSlope20DFactor(**base_args)
        elif factor_type == 'company_share_momentum_slope_50d_factor':
            return CompanyShareMomentumSlope50DFactor(**base_args)
        # ── Technical / Momentum — Acceleration & Change ─────────────────────
        elif factor_type == 'company_share_momentum_accel_5d_10d_factor':
            return CompanyShareMomentumAcceleration5D10DFactor(**base_args)
        elif factor_type == 'company_share_momentum_accel_10d_20d_factor':
            return CompanyShareMomentumAcceleration10D20DFactor(**base_args)
        elif factor_type == 'company_share_momentum_accel_20d_50d_factor':
            return CompanyShareMomentumAcceleration20D50DFactor(**base_args)
        elif factor_type == 'company_share_return_change_5d_factor':
            return CompanyShareReturnChange5DFactor(**base_args)
        elif factor_type == 'company_share_return_change_10d_factor':
            return CompanyShareReturnChange10DFactor(**base_args)
        elif factor_type == 'company_share_return_change_20d_factor':
            return CompanyShareReturnChange20DFactor(**base_args)
        # ── Technical / Momentum — Risk ───────────────────────────────────────
        elif factor_type == 'company_share_sharpe_10d_factor':
            return CompanyShareSharpe10DFactor(**base_args)
        elif factor_type == 'company_share_sharpe_20d_factor':
            return CompanyShareSharpe20DFactor(**base_args)
        elif factor_type == 'company_share_sharpe_50d_factor':
            return CompanyShareSharpe50DFactor(**base_args)
        elif factor_type == 'company_share_sharpe_100d_factor':
            return CompanyShareSharpe100DFactor(**base_args)
        elif factor_type == 'company_share_sortino_20d_factor':
            return CompanyShareSortino20DFactor(**base_args)
        elif factor_type == 'company_share_sortino_50d_factor':
            return CompanyShareSortino50DFactor(**base_args)
        elif factor_type == 'company_share_sortino_100d_factor':
            return CompanyShareSortino100DFactor(**base_args)
        # ── Technical / Momentum — Drawdown / Distance ────────────────────────
        elif factor_type == 'company_share_distance_from_5m_high_factor':
            return CompanyShareDistanceFrom5MHighFactor(**base_args)
        elif factor_type == 'company_share_distance_from_5m_low_factor':
            return CompanyShareDistanceFrom5MLowFactor(**base_args)
        elif factor_type == 'company_share_drawdown_from_5m_high_factor':
            return CompanyShareDrawdownFrom5MHighFactor(**base_args)
        elif factor_type == 'company_share_days_since_5m_high_factor':
            return CompanyShareDaysSince5MHighFactor(**base_args)
        elif factor_type == 'company_share_days_since_5m_low_factor':
            return CompanyShareDaysSince5MLowFactor(**base_args)
        # ── Technical / Momentum — Composite ─────────────────────────────────
        elif factor_type == 'company_share_short_term_momentum_factor':
            return CompanyShareShortTermMomentumFactor(**base_args)
        elif factor_type == 'company_share_medium_term_momentum_factor':
            return CompanyShareMediumTermMomentumFactor(**base_args)
        elif factor_type == 'company_share_short_vs_medium_momentum_factor':
            return CompanyShareShortVsMediumMomentumFactor(**base_args)
        elif factor_type == 'company_share_momentum_zscore_20d_factor':
            return CompanyShareMomentumZScore20DFactor(**base_args)
        elif factor_type == 'company_share_momentum_zscore_50d_factor':
            return CompanyShareMomentumZScore50DFactor(**base_args)
        elif factor_type == 'company_share_momentum_zscore_100d_factor':
            return CompanyShareMomentumZScore100DFactor(**base_args)
        elif factor_type == 'company_share_zakamouline_delta_ceiling_factor':
            return CompanyShareZakamoulineDeltaCeilingFactor(**base_args)
        elif factor_type == 'company_share_zakamouline_delta_floor_factor':
            return CompanyShareZakamoulineDeltaFloorFactor(**base_args)
        elif factor_type == 'company_share_whalley_wilmott_delta_ceiling_factor':
            return CompanyShareWhalleyWilmottDeltaCeilingFactor(**base_args)
        elif factor_type == 'company_share_whalley_wilmott_delta_floor_factor':
            return CompanyShareWhalleyWilmottDeltaFloorFactor(**base_args)
        elif factor_type == 'company_share_zakamouline_ceiling_distance_factor':
            return CompanyShareZakamoulineCeilingDistanceFactor(**base_args)
        elif factor_type == 'company_share_zakamouline_floor_distance_factor':
            return CompanyShareZakamoulineFloorDistanceFactor(**base_args)
        elif factor_type == 'company_share_whalley_wilmott_ceiling_distance_factor':
            return CompanyShareWhalleyWilmottCeilingDistanceFactor(**base_args)
        elif factor_type == 'company_share_whalley_wilmott_floor_distance_factor':
            return CompanyShareWhalleyWilmottFloorDistanceFactor(**base_args)
        elif factor_type == 'company_share_relative_return_vs_spy_1d_factor':
            return CompanyShareRelativeReturnVsSpy1DFactor(**base_args)
        elif factor_type == 'company_share_relative_return_vs_spy_5d_factor':
            return CompanyShareRelativeReturnVsSpy5DFactor(**base_args)
        elif factor_type == 'company_share_relative_return_vs_spy_20d_factor':
            return CompanyShareRelativeReturnVsSpy20DFactor(**base_args)
        elif factor_type == 'company_share_relative_return_vs_spy_3m_factor':
            return CompanyShareRelativeReturnVsSpy3MFactor(**base_args)
        elif factor_type == 'company_share_relative_return_vs_spy_6m_factor':
            return CompanyShareRelativeReturnVsSpy6MFactor(**base_args)
        elif factor_type == 'company_share_avg_turnover_1m_factor':
            return CompanyShareAvgTurnover1mFactor(**base_args)
        elif factor_type == 'company_share_avg_turnover_2m_factor':
            return CompanyShareAvgTurnover2mFactor(**base_args)
        elif factor_type == 'company_share_avg_turnover_3m_factor':
            return CompanyShareAvgTurnover3mFactor(**base_args)
        elif factor_type == 'company_share_avg_turnover_4m_factor':
            return CompanyShareAvgTurnover4mFactor(**base_args)
        elif factor_type == 'company_share_avg_turnover_5m_factor':
            return CompanyShareAvgTurnover5mFactor(**base_args)
        elif factor_type == 'company_share_turnover_factor':
            return CompanyShareTurnoverFactor(**base_args)
        elif factor_type == 'company_share_vpt_16w_20d_lag_factor':
            return CompanyShareVpt16w20dLagFactor(**base_args)
        elif factor_type == 'company_share_max_daily_return_6m_factor':
            return CompanyShareMaxDailyReturn6mFactor(**base_args)
        elif factor_type == 'company_share_min_return_120d_factor':
            return CompanyShareMinReturn120dFactor(**base_args)
        elif factor_type == 'company_share_lgbm_cs_quintile_rank_momentum_factor':
            return CompanyShareLGBMCSQuintileRankMomentumFactor(**base_args)
        elif factor_type == 'company_share_spatio_temporal_momentum_factor':
            return CompanyShareSpatioTemporalMomentumFactor(**base_args)
        elif factor_type == 'company_share_spatio_temporal_feature_factor':
            return CompanyShareSpatioTemporalFeatureFactor(**base_args)
        elif factor_type == 'company_share_cross_sectional_momentum_factor':
            return CompanyShareCrossSectionalMomentumFactor(**base_args)
        else:
            # Known discriminator without an elif branch: build its own class so that
            # calculate / calculate_dependencies are not lost.
            mapped_cls = DISCRIMINATOR_CLASS_MAP.get(factor_type)
            if mapped_cls is not None:
                try:
                    import inspect as _inspect
                    accepted = _inspect.signature(mapped_cls.__init__).parameters
                    kwargs = {k: v for k, v in base_args.items() if k in accepted}
                    return mapped_cls(**kwargs)
                except Exception:
                    pass
            # Default to base Factor for unknown types
            # Since Factor is abstract, create a concrete implementation
            class GenericFactor(FactorEntity):
                pass
            
            return GenericFactor(**base_args)

    @staticmethod
    def to_orm(domain_entity: FactorEntity) -> Factormodel:
        """Convert domain entity to ORM model based on entity type."""
        base_data = {
            'id': domain_entity.id,
            'name': domain_entity.name,
            'group': domain_entity.group,
            'subgroup': domain_entity.subgroup,
            'frequency': domain_entity.frequency,
            'data_type': domain_entity.data_type,
            'source': domain_entity.source,
            'definition': domain_entity.definition,
        }
        
        
        # Set factor_type based on domain entity type
        if isinstance(domain_entity, CompanySharePortfolioValueFactorEntity):
            base_data['factor_type'] = 'portfolio_company_share_value'
        elif isinstance(domain_entity, CompanySharePortfolioHoldingValueFactorEntity):
            base_data['factor_type'] = 'portfolio_company_share_holding_value'
        elif isinstance(domain_entity, CompanySharePositionValueFactorEntity):
            base_data['factor_type'] = 'company_share_position_value_factor'
        elif isinstance(domain_entity, CompanyShareTransactionValueFactorEntity):
            base_data['factor_type'] = 'company_share_transaction_value_factor'
        elif isinstance(domain_entity, CompanyShareOrderQuantityFactorEntity):
            base_data['factor_type'] = 'company_share_order_quantity_factor'
        elif isinstance(domain_entity, CompanyShareOrderPriceFactorEntity):
            base_data['factor_type'] = 'company_share_order_price_factor'
        elif isinstance(domain_entity, PortfolioValueFactorEntity):
            base_data['factor_type'] = 'portfolio_value_factor'
        else:
            # Use existing logic or default
            base_data['factor_type'] = 'generic'
        
        # Default to base FactorModel for unknown types
        return Factormodel(**base_data)
    
    @staticmethod
    def to_domain_portfolio_company_share_value_factor(orm_model):
        """Convert portfolio company share value factor ORM model to domain entity."""
        if not orm_model:
            return None
            
        return CompanySharePortfolioValueFactorEntity(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )
    
    @staticmethod
    def to_domain_portfolio_company_share_holding_value_factor(orm_model):
        """Convert portfolio company share holding value factor ORM model to domain entity."""
        if not orm_model:
            return None
            
        return CompanySharePortfolioHoldingValueFactorEntity(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )
    