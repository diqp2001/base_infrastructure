"""
Mappers for symbol domain entities.
Handles bidirectional conversion between domain entities and ORM models.
"""
from decimal import Decimal
from typing import Optional
import json

from src.domain.entities.back_testing.symbol import Symbol as DomainSymbol, SymbolProperties as DomainSymbolProperties, SymbolMapping as DomainSymbolMapping
from src.domain.entities.back_testing.enums import SecurityType, Market
from src.infrastructure.models.back_testing.symbol_model import Symbol as ORMSymbol, SymbolProperties as ORMSymbolProperties, SymbolMapping as ORMSymbolMapping


class SymbolMapper:
    """Mapper for Symbol domain entity ↔ ORM model conversion."""
    
    @staticmethod
    def to_domain(orm_symbol: ORMSymbol) -> DomainSymbol:
        """Convert ORM Symbol to domain Symbol."""
        try:
            return DomainSymbol(
                value=orm_symbol.value,
                id=orm_symbol.id,
                security_type=SecurityType(orm_symbol.security_type),
                market=Market(orm_symbol.market)
            )
        except (ValueError, TypeError) as e:
            # Handle invalid enum values gracefully
            return DomainSymbol(
                value=orm_symbol.value,
                id=orm_symbol.id,
                security_type=SecurityType.BASE,
                market=Market.USA
            )
    
    @staticmethod
    def to_orm(domain_symbol: DomainSymbol) -> ORMSymbol:
        """Convert domain Symbol to ORM Symbol."""
        return ORMSymbol(
            id=domain_symbol.id,
            value=domain_symbol.value,
            security_type=domain_symbol.security_type.value,
            market=domain_symbol.market.value
        )
    
    @staticmethod
    def update_orm(orm_symbol: ORMSymbol, domain_symbol: DomainSymbol) -> ORMSymbol:
        """Update ORM Symbol with domain Symbol data."""
        orm_symbol.value = domain_symbol.value
        orm_symbol.security_type = domain_symbol.security_type.value
        orm_symbol.market = domain_symbol.market.value
        return orm_symbol


class SymbolPropertiesMapper:
    """Mapper for SymbolProperties domain entity ↔ ORM model conversion."""
    
    @staticmethod
    def to_domain(orm_props: ORMSymbolProperties) -> DomainSymbolProperties:
        """Convert ORM SymbolProperties to domain SymbolProperties."""
        exchange_hours = None
        if orm_props.exchange_hours:
            try:
                exchange_hours = orm_props.exchange_hours if isinstance(orm_props.exchange_hours, dict) else json.loads(orm_props.exchange_hours)
            except (json.JSONDecodeError, TypeError):
                exchange_hours = None
        
        return DomainSymbolProperties(
            time_zone=orm_props.time_zone,
            exchange_hours=exchange_hours,
            lot_size=orm_props.lot_size,
            tick_size=Decimal(str(orm_props.tick_size)) if orm_props.tick_size else Decimal('0.01'),
            minimum_price_variation=Decimal(str(orm_props.minimum_price_variation)) if orm_props.minimum_price_variation else Decimal('0.01'),
            contract_multiplier=orm_props.contract_multiplier,
            minimum_order_size=orm_props.minimum_order_size,
            maximum_order_size=orm_props.maximum_order_size,
            price_scaling=Decimal(str(orm_props.price_scaling)) if orm_props.price_scaling else Decimal('1'),
            margin_requirement=Decimal(str(orm_props.margin_requirement)) if orm_props.margin_requirement else Decimal('0.25'),
            short_able=orm_props.short_able
        )
    
    @staticmethod
    def to_orm(domain_props: DomainSymbolProperties, symbol_id: str) -> ORMSymbolProperties:
        """Convert domain SymbolProperties to ORM SymbolProperties."""
        exchange_hours_json = None
        if domain_props.exchange_hours:
            try:
                exchange_hours_json = domain_props.exchange_hours if isinstance(domain_props.exchange_hours, dict) else json.dumps(domain_props.exchange_hours)
            except (TypeError, ValueError):
                exchange_hours_json = None
        
        return ORMSymbolProperties(
            symbol_id=symbol_id,
            time_zone=domain_props.time_zone,
            exchange_hours=exchange_hours_json,
            lot_size=domain_props.lot_size,
            tick_size=float(domain_props.tick_size),
            minimum_price_variation=float(domain_props.minimum_price_variation),
            contract_multiplier=domain_props.contract_multiplier,
            minimum_order_size=domain_props.minimum_order_size,
            maximum_order_size=domain_props.maximum_order_size,
            price_scaling=float(domain_props.price_scaling),
            margin_requirement=float(domain_props.margin_requirement),
            short_able=domain_props.short_able
        )
    
    @staticmethod
    def update_orm(orm_props: ORMSymbolProperties, domain_props: DomainSymbolProperties) -> ORMSymbolProperties:
        """Update ORM SymbolProperties with domain SymbolProperties data."""
        exchange_hours_json = None
        if domain_props.exchange_hours:
            try:
                exchange_hours_json = domain_props.exchange_hours if isinstance(domain_props.exchange_hours, dict) else json.dumps(domain_props.exchange_hours)
            except (TypeError, ValueError):
                exchange_hours_json = None
        
        orm_props.time_zone = domain_props.time_zone
        orm_props.exchange_hours = exchange_hours_json
        orm_props.lot_size = domain_props.lot_size
        orm_props.tick_size = float(domain_props.tick_size)
        orm_props.minimum_price_variation = float(domain_props.minimum_price_variation)
        orm_props.contract_multiplier = domain_props.contract_multiplier
        orm_props.minimum_order_size = domain_props.minimum_order_size
        orm_props.maximum_order_size = domain_props.maximum_order_size
        orm_props.price_scaling = float(domain_props.price_scaling)
        orm_props.margin_requirement = float(domain_props.margin_requirement)
        orm_props.short_able = domain_props.short_able
        return orm_props


class SymbolMappingMapper:
    """Mapper for SymbolMapping domain entity ↔ ORM model conversion."""
    
    @staticmethod
    def to_domain(orm_mapping: ORMSymbolMapping, original_symbol: DomainSymbol, mapped_symbol: DomainSymbol) -> DomainSymbolMapping:
        """Convert ORM SymbolMapping to domain SymbolMapping."""
        return DomainSymbolMapping(
            original_symbol=original_symbol,
            mapped_symbol=mapped_symbol,
            data_provider=orm_mapping.data_provider,
            mapping_date=orm_mapping.mapping_date
        )
    
    @staticmethod
    def to_orm(domain_mapping: DomainSymbolMapping) -> ORMSymbolMapping:
        """Convert domain SymbolMapping to ORM SymbolMapping."""
        return ORMSymbolMapping(
            original_symbol_id=domain_mapping.original_symbol.id,
            mapped_symbol_id=domain_mapping.mapped_symbol.id,
            data_provider=domain_mapping.data_provider,
            mapping_date=domain_mapping.mapping_date
        )