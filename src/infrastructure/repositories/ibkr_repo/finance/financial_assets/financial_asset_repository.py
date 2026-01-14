from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from decimal import Decimal



from src.infrastructure.repositories.ibkr_repo.base_ibkr_repository import BaseIBKRRepository, EntityType, ModelType
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class IBKRFinancialAssetRepository(BaseIBKRRepository[EntityType, ModelType], ABC):
    """
    Base repository for all financial asset types (shares, bonds, currencies, etc.).
    Extends BaseRepository with financial asset specific functionality.
    """
    def __init__(self, ib_client):
        """Initialize IndexRepository with database session."""

        super().__init__(ib_client)

    # --- Financial Asset Specific Methods ---