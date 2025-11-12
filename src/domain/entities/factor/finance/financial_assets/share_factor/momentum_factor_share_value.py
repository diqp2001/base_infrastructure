# domain/entities/factor/finance/financial_assets/share_factor/momentum_factor_share_value.py

from dataclasses import dataclass
import pandas as pd
from decimal import Decimal
from typing import Optional, List
from application.managers.data_managers.data_manager_price import DataManagerPrice
from application.managers.database_managers.database_manager import DatabaseManager
from domain.entities.factor.finance.financial_assets.share_factor.share_factor_value import ShareFactorValue
from domain.entities.factor.finance.financial_assets.share_factor.momentum_factor_share import ShareMomentumFactor
from infrastructure.repositories.mappers.factor.finance.financial_assets.share_factor_value_mapper import ShareFactorValueMapper


@dataclass
class ShareMomentumFactorValue(ShareFactorValue):
    """
    Domain entity representing a single momentum factor value for a share.
    Handles calculation for a given period and ORM conversion.
    """

    factor: Optional[ShareMomentumFactor] = None

    def __init__(self, database_manager: DatabaseManager, factor: ShareMomentumFactor):
        self.data_manager = DataManagerPrice(database_manager)
        self.factor = factor

    def calculate(self, data: pd.DataFrame, column_name: str, period: int) -> pd.DataFrame:
        """
        Calculate momentum returns over a given period.
        """
        try:
            return self.data_manager.add_deep_momentum_feature(data=data, column_name=column_name, period_offset=period)
        except Exception as e:
            print(f"⚠️  Error calculating momentum ({period}-day) features: {e}")
            return pd.DataFrame()

    
    def store_factor_values(
        self,
        repository,
        factor,
        share,
        data: pd.DataFrame,
        column_name: str,
        period: int,
        overwrite: bool
    ) -> int:
        """
        Compute and store momentum factor values using repository pattern.
        Same approach as _store_momentum_features method.
        """
        try:
            # Calculate momentum factor values
            initial_col = set(data.columns)
            calculated_df = self.calculate(data=data, column_name=column_name, period=period)
            if calculated_df.empty:
                return 0

            feature_col = list(set(calculated_df.columns) - initial_col)[0]

            # Use repository's _store_factor_values method (same as _store_momentum_features)
            values_stored = repository._store_factor_values(
                factor, share, calculated_df, feature_col, overwrite
            )

            return values_stored

        except Exception as e:
            print(f"❌ Error storing momentum factor values ({period}-day): {e}")
            return 0

    def store_package_momentum_factors(
        self,
        repository,
        factor,
        share,
        data: pd.DataFrame,
        column_name: str,
        period: int,
        overwrite: bool
    ) -> int:
        """
        Compute and store momentum factor values for a single period.
        Returns count of stored values.
        """
        return self.store_factor_values(
            repository=repository,
            factor=factor,
            share=share,
            data=data,
            column_name=column_name,
            period=period,
            overwrite=overwrite
        )
