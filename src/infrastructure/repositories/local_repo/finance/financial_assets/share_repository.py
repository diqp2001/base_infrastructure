from .financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.share import Share as ShareModel
from src.domain.entities.finance.financial_assets.share import Share as ShareEntity


class ShareRepository(FinancialAssetRepository):
    def __init__(self, db_type='sqlite'):
        super().__init__(db_type)

    
    def get_by_id(self, id: int) -> ShareEntity:
        """Fetches a Share asset by its ID."""
        try:
            return self.db.query(ShareModel).filter(ShareModel.id == id).first()
        except Exception as e:
            print(f"Error retrieving share by ID: {e}")
            return None
        finally:
            self.db.close()

    def save_list(self, list_share_entity, db) -> None:
        try:
            # Add the asset and commit
            for share_entity in list_share_entity:
                db.add(share_entity)
            db.commit()
        except Exception as e:
            db.rollback()  # Rollback in case of an error
            print(f"An error occurred while saving: {e}")
            
    def exists_by_id(self, id: int) -> bool:
        """Checks if a share exists by its ID."""
        try:
            # Query the database to check if a share with the given ID exists
            share = self.db.query(ShareModel).filter(ShareModel.id == id).first()
            return share is not None  # If no share is found, returns False
        except Exception as e:
            print(f"Error checking if share exists by ID: {e}")
            return False

    def _get_next_available_share_id(self) -> int:
        """
        Get the next available ID for share creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            # Get the highest existing ID from the database
            max_id_result = self.db.query(ShareModel.id).order_by(ShareModel.id.desc()).first()

            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist

        except Exception as e:
            print(f"Warning: Could not determine next available share ID: {str(e)}")
            return 1  # Default to 1 if query fails

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