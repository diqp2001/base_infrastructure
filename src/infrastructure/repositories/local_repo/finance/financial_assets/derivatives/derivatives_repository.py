# Derivatives Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/derivatives.py
from typing import Optional
from sqlalchemy.orm import Session

from domain.ports.finance.financial_assets.derivatives.derivative_port import DerivativePort
from infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from infrastructure.models.finance.financial_assets.derivative.derivatives import Derivatives as DerivativesModel
from src.domain.entities.finance.financial_assets.derivatives import Derivatives as DerivativesEntity
class DerivativesRepository(FinancialAssetRepository, DerivativePort):
    """Local repository for derivatives model"""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.data_store = []
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Derivatives."""
        return DerivativesModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Derivatives."""
        return DerivativesEntity
    
    def save(self, derivative):
        """Save derivative to local storage"""
        self.data_store.append(derivative)
        
    def find_by_id(self, derivative_id):
        """Find derivative by ID"""
        for derivative in self.data_store:
            if getattr(derivative, 'id', None) == derivative_id:
                return derivative
        return None
        
    def find_all(self):
        """Find all derivatives"""
        return self.data_store.copy()

    def get_or_create(self, ticker: str, name: Optional[str] = None, underlying_asset_id: Optional[int] = None, 
                      exchange_id: Optional[int] = None, currency_id: Optional[int] = None, **kwargs) -> Optional[DerivativesEntity]:
        """
        Get or create a derivative with dependency resolution.
        Extends the base FinancialAssetRepository get_or_create with derivative-specific functionality.
        
        Args:
            ticker: Derivative ticker symbol (primary identifier)
            name: Derivative name (optional, defaults to ticker if not provided)
            underlying_asset_id: Underlying asset ID (required for derivatives)
            exchange_id: Exchange ID (optional, will use default if not provided)
            currency_id: Currency ID (optional, will use default USD if not provided)
            **kwargs: Additional fields specific to the derivative type
            
        Returns:
            Domain derivative entity or None if creation failed
        """
        try:
            # First try to get existing derivative by ticker
            existing = self.get_by_ticker(ticker)
            if existing:
                return existing
            
            # Resolve underlying asset dependency if not provided
            if not underlying_asset_id:
                from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
                share_repo = CompanyShareRepository(self.session)
                default_share = share_repo.get_or_create("SPY", "SPDR S&P 500 ETF Trust")
                underlying_asset_id = default_share.id if default_share else 1
            
            # Use parent class get_or_create with derivative-specific parameters
            return super().get_or_create(
                ticker=ticker,
                name=name,
                exchange_id=exchange_id,
                currency_id=currency_id,
                underlying_asset_id=underlying_asset_id,
                **kwargs
            )
            
        except Exception as e:
            print(f"Error in get_or_create for derivative {ticker}: {e}")
            return None