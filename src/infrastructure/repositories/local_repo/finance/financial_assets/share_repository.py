
from typing import Optional
from sqlalchemy.orm import Session

from src.domain.ports.finance.financial_assets.share.share_port import SharePort
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.share import ShareModel as ShareModel
from src.domain.entities.finance.financial_assets.share.share import Share as ShareEntity
from src.infrastructure.repositories.mappers.finance.financial_assets.share_mapper import ShareMapper


class ShareRepository(FinancialAssetRepository,SharePort):
    def __init__(self, session: Session, factory, mapper: ShareMapper = None):
        """Initialize ShareRepository with database session."""
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or ShareMapper()
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class used by this repository."""
        return ShareModel
    
    @property
    def entity_class(self):
        """Return the domain entity class for Share."""
        return ShareEntity
    
    def _to_entity(self, infra_obj: ShareModel) -> ShareEntity:
        """Convert ORM model to domain entity."""
        if not infra_obj:
            return None
        return self.mapper.to_domain(infra_obj)
    
    def _to_model(self, entity: ShareEntity) -> ShareModel:
        """Convert domain entity to ORM model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)

    # Legacy method support - inherits from base
    def get_by_id(self, id: int) -> ShareEntity:
        """Fetches a Share asset by its ID.""" 
        model = self.get(id)
        return self._to_entity(model) if model else None

    def exists_by_id(self, id: int) -> bool:
        """Checks if a share exists by its ID."""
        return self.get(id) is not None

    def enhance_with_csv_data(self, share_entities, stock_data_cache, database_manager=None):
        """
        Enhance share entities with basic market data from CSV files (fundamental data removed).
        This functionality was moved from TestProjectDataManager for better separation.
        
        Args:
            share_entities: List of share entities to enhance
            stock_data_cache: Dictionary of ticker -> DataFrame with historical data
            database_manager: Optional database manager for saving CSV data to tables
        
        Returns:
            List of enhanced share entities
        """
        from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_mapper import CompanyShareMapper
        
        enhanced_entities = []
        
        for share_entity in share_entities:
            try:
                # Use mapper to enhance with market data
                enhanced_entity = CompanyShareMapper.enhance_with_csv_data(
                    domain_obj=share_entity,
                    stock_data_cache=stock_data_cache,
                    database_manager=database_manager
                )
                enhanced_entities.append(enhanced_entity)
                
            except Exception as e:
                print(f"❌ Error enhancing share {share_entity.ticker}: {str(e)}")
                # Include unenhanced entity to maintain list integrity
                enhanced_entities.append(share_entity)
        
        return enhanced_entities
    
    def get_by_ticker(self, ticker: str) -> Optional[ShareEntity]:
        """Get share by ticker symbol."""
        try:
            model = self.session.query(self.model_class).filter(
                self.model_class.ticker == ticker
            ).first()
            return self._to_entity(model) if model else None
        except Exception as e:
            print(f"Error retrieving share by ticker {ticker}: {e}")
            return None
    
    def get_or_create(self, ticker: str, name: str = None, exchange_id: int = None, 
                      company_id: int = None, **kwargs) -> Optional[ShareEntity]:
        """
        Get or create a share by ticker with dependency resolution.
        
        Args:
            ticker: Share ticker symbol
            name: Share name (optional, will default if not provided)
            exchange_id: Exchange ID (optional, will use default if not provided)
            company_id: Company ID (optional)
            **kwargs: Additional fields for the share
            
        Returns:
            Share entity or None if creation failed
        """
        try:
            # First try to get existing share
            existing = self.get_by_ticker(ticker)
            if existing:
                return existing
            
            # Create new share if it doesn't exist
            print(f"Creating new share: {ticker}")
            
            # Set default values
            if not name:
                name = f"Share {ticker.upper()}"
            
            if not exchange_id:
                # Get or create a default exchange
                exchange_local_repo = self.factory.exchange_local_repo
                default_exchange = exchange_local_repo.get_or_create("NASDAQ", name="NASDAQ")
                exchange_id = default_exchange.id if default_exchange else 1
            
            new_share = ShareEntity(
                id=None,
                name=name,
                symbol=ticker.upper(),
                exchange_id=exchange_id
            )
            
            return self.add(new_share)
            
        except Exception as e:
            print(f"Error in get_or_create for share {ticker}: {e}")
            return None
    
    def add(self, share: ShareEntity) -> ShareEntity:
        """Add a new share to the database."""
        try:
            model = self._to_model(share)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_entity(model)
        except Exception as e:
            self.session.rollback()
            print(f"Error adding share: {e}")
            return None