from typing import Optional
from sqlalchemy.orm import Session

from infrastructure.repositories.financial_asset_base_repository import FinancialAssetBaseRepository
from src.infrastructure.models.finance.financial_assets.share import Share as ShareModel
from src.domain.entities.finance.financial_assets.share import Share as ShareEntity
from application.services.database_service import DatabaseService


class ShareRepository(FinancialAssetBaseRepository[ShareEntity, ShareModel]):
    def __init__(self, session: Session):
        super().__init__(session)
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class used by this repository."""
        return ShareModel
    
    def _to_entity(self, infra_obj: ShareModel) -> ShareEntity:
        """Convert ORM model to domain entity."""
        if not infra_obj:
            return None
        return ShareEntity(
            id=infra_obj.id,
            ticker=infra_obj.ticker,
            exchange_id=infra_obj.exchange_id,
            company_id=infra_obj.company_id,
            start_date=infra_obj.start_date,
            end_date=infra_obj.end_date
        )
    
    def _to_model(self, entity: ShareEntity) -> ShareModel:
        """Convert domain entity to ORM model."""
        model = ShareModel(
            ticker=entity.ticker,
            exchange_id=entity.exchange_id,
            company_id=entity.company_id,
            start_date=entity.start_date,
            end_date=entity.end_date
        )
        if hasattr(entity, 'id') and entity.id is not None:
            model.id = entity.id
        return model

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