"""
Mapper for FinancialAssetTimeSeries domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.time_series.financial_asset_time_series import FinancialAssetTimeSeries as DomainFinancialAssetTimeSeries
from src.infrastructure.models.time_series.finance.financial_asset_time_series import FinancialAssetTimeSeriesModel as ORMFinancialAssetTimeSeries


class FinancialAssetTimeSeriesMapper:
    """Mapper for FinancialAssetTimeSeries domain entity and ORM model."""

    @staticmethod
    def to_domain(orm_obj: ORMFinancialAssetTimeSeries) -> DomainFinancialAssetTimeSeries:
        """Convert ORM model to domain entity."""
        domain_entity = DomainFinancialAssetTimeSeries(
            id=orm_obj.id,
            name=orm_obj.name,
            financial_asset_id=getattr(orm_obj, 'financial_asset_id', None),
            description=getattr(orm_obj, 'description', None)
        )
        
        # Set data properties if available
        if hasattr(orm_obj, 'data_json') and orm_obj.data_json:
            domain_entity.set_data_json(orm_obj.data_json)
        if hasattr(orm_obj, 'data_binary') and orm_obj.data_binary:
            domain_entity.set_data_binary(orm_obj.data_binary)
        if hasattr(orm_obj, 'rows_count') and orm_obj.rows_count:
            domain_entity.set_rows_count(orm_obj.rows_count)
        if hasattr(orm_obj, 'columns_count') and orm_obj.columns_count:
            domain_entity.set_columns_count(orm_obj.columns_count)
        if hasattr(orm_obj, 'columns_info') and orm_obj.columns_info:
            domain_entity.set_columns_info(orm_obj.columns_info)
        
        return domain_entity

    @staticmethod
    def to_orm(domain_obj: DomainFinancialAssetTimeSeries, orm_obj: Optional[ORMFinancialAssetTimeSeries] = None) -> ORMFinancialAssetTimeSeries:
        """Convert domain entity to ORM model."""
        if orm_obj is None:
            orm_obj = ORMFinancialAssetTimeSeries(
                name=domain_obj.name,
                financial_asset_id=getattr(domain_obj, 'financial_asset_id', None),
                description=getattr(domain_obj, 'description', None)
            )
        
        # Map basic fields
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        orm_obj.financial_asset_id = getattr(domain_obj, 'financial_asset_id', None)
        
        # Map optional attributes if they exist
        if hasattr(domain_obj, 'description'):
            orm_obj.description = domain_obj.description
        if hasattr(domain_obj, 'data_json'):
            orm_obj.data_json = domain_obj.data_json
        if hasattr(domain_obj, 'data_binary'):
            orm_obj.data_binary = domain_obj.data_binary
        if hasattr(domain_obj, 'rows_count'):
            orm_obj.rows_count = domain_obj.rows_count
        if hasattr(domain_obj, 'columns_count'):
            orm_obj.columns_count = domain_obj.columns_count
        if hasattr(domain_obj, 'columns_info'):
            orm_obj.columns_info = domain_obj.columns_info
        
        # Set timestamps if they exist on the model
        if hasattr(orm_obj, 'created_date') and not orm_obj.created_date:
            orm_obj.created_date = datetime.utcnow()
        if hasattr(orm_obj, 'updated_date'):
            orm_obj.updated_date = datetime.utcnow()
        
        return orm_obj