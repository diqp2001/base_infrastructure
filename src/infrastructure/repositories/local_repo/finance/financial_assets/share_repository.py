
from typing import Optional
from sqlalchemy.orm import Session

from src.domain.ports.finance.financial_assets.share.share_port import SharePort
from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
from src.infrastructure.models.finance.financial_assets.share import ShareModel as ShareModel
from src.domain.entities.finance.financial_assets.share.share import Share as ShareEntity
from src.infrastructure.repositories.mappers.finance.financial_assets.share.share_mapper import ShareMapper


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
        from src.infrastructure.repositories.mappers.finance.financial_assets.share.company_share.company_share_mapper import CompanyShareMapper
        
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
                print(f"âŒ Error enhancing share {share_entity.ticker}: {str(e)}")
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

    # ---- dependency resolution shared by CompanyShare and ETFShare ----

    def _resolve_currency_id(self, iso_code: str) -> Optional[int]:
        """Currency id for an ISO code, created through the currency repository if missing."""
        try:
            repo = self.factory.currency_local_repo if self.factory else None
            currency = (repo.get_by_iso_code(iso_code) or repo._create_or_get(iso_code)) if repo else None
            return currency.id if currency else None
        except Exception as e:
            print(f"Could not resolve currency {iso_code}: {e}")
            return None

    def _resolve_exchange_dependency(self, ticker: str, exchange_name: Optional[str] = None) -> int:
        """Resolve the exchange of a share (company or ETF)."""
        try:
            # Use factory if available, otherwise create repository directly
            if self.factory:
                local_repos = self.factory.create_local_repositories()
                exchange_repo = local_repos.get('exchange')
                if not exchange_repo:
                    exchange_repo = self.factory.exchange_local_repo
            else:
                exchange_repo = self.factory.exchange_local_repo
            
            exchange_name = exchange_name or self._get_default_exchange_for_ticker(ticker)
            
            country_id = self._resolve_country_id(None)
            if country_id is None:
                return None
            exchange = exchange_repo._create_or_get(
                name=exchange_name,
                legal_name=f"{exchange_name} Stock Exchange",
                country_id=country_id
            )

            return exchange.id if exchange else None

        except Exception as e:
            print(f"Error resolving exchange dependency: {str(e)}")
            return None

    def _resolve_country_id(self, country_name: Optional[str]) -> Optional[int]:
        """A real countries row (resolved / created by name; default United States) — never a placeholder id
        that may not exist (BI-008)."""
        repo = getattr(self.factory, 'country_local_repo', None) if self.factory else None
        if repo is None:
            return None
        country = repo._create_or_get(country_name or "United States",
                                      iso_code=None if country_name else "US")
        return getattr(country, 'id', None)

    def _get_default_exchange_for_ticker(self, ticker: str) -> str:
        """Get default exchange based on ticker patterns."""
        # Simple heuristics for common exchanges
        if ticker in ['SPX', 'VIX', 'RUT']:
            return 'CBOE'
        elif len(ticker) <= 4 and ticker.isalpha():
            return 'NASDAQ'
        else:
            return 'NYSE'
