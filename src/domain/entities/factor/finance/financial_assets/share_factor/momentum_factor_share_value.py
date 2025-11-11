# domain/entities/factor/finance/financial_assets/share_factor/momentum_factor_share_value.py

from dataclasses import dataclass
import pandas as pd
from typing import Optional, List
from application.managers.data_managers.data_manager_price import DataManagerPrice
from application.managers.database_managers.database_manager import DatabaseManager
from domain.entities.factor.finance.financial_assets.share_factor.share_factor_value import ShareFactorValue
from domain.entities.factor.finance.financial_assets.share_factor.momentum_factor_share import MomentumFactorShare
from infrastructure.repositories.mappers.factor.finance.financial_assets.share_factor_value_mapper import ShareFactorValueMapper


@dataclass
class MomentumFactorShareValue(ShareFactorValue):
    """
    Domain entity representing a single momentum factor value for a share.
    Handles calculation for a given period and ORM conversion.
    """

    factor: Optional[MomentumFactorShare] = None

    def __init__(self, database_manager: DatabaseManager, factor: MomentumFactorShare):
        self.data_manager = DataManagerPrice(database_manager)
        self.factor = factor

    def calculate(self, data: pd.DataFrame, column_name: str, period: int) -> pd.DataFrame:
        """
        Calculate momentum returns over a given period.
        """
        try:
            return self.data_manager.add_deep_momentum_feature(data=data, column_name=column_name, period=period)
        except Exception as e:
            print(f"⚠️  Error calculating momentum ({period}-day) features: {e}")
            return pd.DataFrame()

    def store_factor_values(
        self,
        data: pd.DataFrame,
        column_name: str,
        entity_id: int,
        factor_id: int,
        period: int
    ) -> List:
        """
        Compute and convert the momentum factor values to ORM models for storage.
        """
        try:
            calculated_df = self.calculate(data=data, column_name=column_name, period=period)
            if calculated_df.empty:
                return []

            feature_col = list(set(calculated_df.columns) - set(data.columns))

            calculated_df["factor_id"] = factor_id
            calculated_df["entity_id"] = entity_id
            calculated_df["date"] = calculated_df.index

            orm_objects = []
            for _, row in calculated_df.iterrows():
                domain_entity = ShareFactorValue(
                    factor_id=row["factor_id"],
                    entity_id=row["entity_id"],
                    date=row["date"],
                    value=row[feature_col],
                )
                orm_objects.append(ShareFactorValueMapper.to_orm(domain_entity))
            return orm_objects

        except Exception as e:
            print(f"❌ Error storing momentum factor values ({period}-day): {e}")
            return []

    def store_package_momentum_factors(
        self,
        data: pd.DataFrame,
        column_name: str,
        entity_id: int,
        factor_id: int,
        period: int
    ) -> List:
        """
        Compute and store momentum factor values for a single period.
        Returns list of ORM objects.
        """
        return self.store_factor_values(
            data=data,
            column_name=column_name,
            entity_id=entity_id,
            factor_id=factor_id,
            period=period
        )
