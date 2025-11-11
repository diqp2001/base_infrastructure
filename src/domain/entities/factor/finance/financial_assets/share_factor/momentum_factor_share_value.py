from dataclasses import dataclass
import pandas as pd
from typing import Optional
from application.managers.data_managers.data_manager import DataManager
from application.managers.data_managers.data_manager_price import DataManagerPrice
from application.managers.database_managers.database_manager import DatabaseManager
from domain.entities.factor.finance.financial_assets.share_factor.share_factor_value import ShareFactorValue
from domain.entities.factor.finance.financial_assets.share_factor.momentum_factor_share import MomentumFactorShare


@dataclass
class MomentumFactorShareValue(ShareFactorValue):
    """
    Domain entity representing momentum factor values for shares.
    Extends ShareFactorValue with momentum-specific calculation and storage logic.
    """

    factor: Optional[MomentumFactorShare] = None
    def __init__(self, database_manager: DatabaseManager):
        self.data_manager = DataManagerPrice(database_manager)

    def __post_init__(self):

        super().__post_init__()

    def calculate(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Calculate momentum-related features for a given equity time series.
        """
        try:
            # Assuming self.add_deep_momentum_features is inherited or mixed in
            result_df = self.data_manager.add_deep_momentum_features(data=data, column_name=column_name)
            return result_df
        except Exception as e:
            print(f"⚠️  Error calculating momentum features for {self.name}: {e}")
            return pd.DataFrame()

    def store_values(self, data: pd.DataFrame, column_name: str) -> pd.DataFrame:
        """
        Compute and return the momentum factor values for storage.

        Args:
            data: DataFrame containing price or return data.
            column_name: Name of the column used for momentum computation.

        Returns:
            DataFrame with calculated momentum features and metadata ready for storage.
        """
        if self.factor is None:
            print("❌ No MomentumFactorShare instance linked to this MomentumFactorShareValue.")
            return pd.DataFrame()

        try:
            calculated_df = self.calculate(data=data, column_name=column_name)

            # Add metadata columns
            calculated_df["factor_id"] = self.factor_id
            calculated_df["entity_id"] = self.entity_id
            calculated_df["date"] = calculated_df.index if "date" not in calculated_df.columns else calculated_df["date"]

            return calculated_df

        except Exception as e:
            print(f"❌ Error storing momentum factor values: {e}")
            return pd.DataFrame()
