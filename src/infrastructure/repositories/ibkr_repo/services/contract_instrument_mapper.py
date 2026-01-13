"""
IBKR Contract to Instrument Mapping Service

This service handles the conversion of IBKR contracts and contract details
to domain Instrument entities, following the architecture pattern:
IBKR API → Instrument Entity → Local Repository → DB
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal

from ibapi.contract import Contract, ContractDetails

from src.domain.entities.finance.instrument.ibkr_instrument import IBKRInstrument
from src.domain.entities.finance.instrument.instrument_factor import InstrumentFactor
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset

from ..tick_types.ibkr_tick_mapping import IBKRTickType, IBKRTickFactorMapper, FactorMapping


class IBKRContractInstrumentMapper:
    """
    Service for mapping IBKR contracts to domain instrument entities.
    
    This mapper converts IBKR contract data to clean domain entities
    without any infrastructure dependencies.
    """
    
    def __init__(self):
        """Initialize the mapper."""
        self.tick_mapper = IBKRTickFactorMapper()
    
    def contract_to_instrument(
        self, 
        contract: Contract, 
        contract_details: ContractDetails,
        asset: FinancialAsset,
        timestamp: Optional[datetime] = None
    ) -> Optional[IBKRInstrument]:
        """
        Convert IBKR contract and details to IBKRInstrument domain entity.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object  
            asset: The underlying financial asset
            timestamp: When the instrument data was captured
            
        Returns:
            IBKRInstrument entity or None if conversion failed
        """
        try:
            timestamp = timestamp or datetime.now()
            
            # Extract basic contract information
            instrument = IBKRInstrument(
                id=None,  # Will be set by repository
                asset=asset,
                source="IBKR",
                date=timestamp,
                
                # IBKR Contract Details
                contract_id=getattr(contract, 'conId', None),
                symbol=getattr(contract, 'symbol', ''),
                security_type=getattr(contract, 'secType', ''),
                exchange=getattr(contract, 'exchange', ''),
                currency=getattr(contract, 'currency', ''),
                local_symbol=getattr(contract, 'localSymbol', ''),
                trading_class=getattr(contract, 'tradingClass', ''),
                
                # Contract Details Metadata
                market_name=getattr(contract_details, 'marketName', ''),
                min_tick=self._safe_decimal(getattr(contract_details, 'minTick', None)),
                price_magnifier=getattr(contract_details, 'priceMagnifier', 1),
                order_types=getattr(contract_details, 'orderTypes', ''),
                valid_exchanges=getattr(contract_details, 'validExchanges', ''),
                long_name=getattr(contract_details, 'longName', ''),
                contract_month=getattr(contract_details, 'contractMonth', ''),
                industry=getattr(contract_details, 'industry', ''),
                category=getattr(contract_details, 'category', ''),
                subcategory=getattr(contract_details, 'subcategory', ''),
                
                # Trading Rules
                min_size=self._safe_decimal(getattr(contract_details, 'minSize', None)),
                size_increment=self._safe_decimal(getattr(contract_details, 'sizeIncrement', None)),
                suggested_size_increment=self._safe_decimal(getattr(contract_details, 'suggestedSizeIncrement', None)),
                
                # Liquidity Information
                liquid_hours=getattr(contract_details, 'liquidHours', ''),
                time_zone_id=getattr(contract_details, 'timeZoneId', ''),
                
                # Additional metadata from contract details
                custom_metadata=self._extract_custom_metadata(contract, contract_details)
            )
            
            # Validate the created instrument
            if not instrument.is_valid():
                print(f"Invalid instrument created from contract {contract.symbol}")
                return None
                
            return instrument
            
        except Exception as e:
            print(f"Error converting IBKR contract to instrument: {e}")
            return None
    
    def tick_data_to_factor_values(
        self,
        instrument: IBKRInstrument,
        tick_data: Dict[int, Any],
        timestamp: Optional[datetime] = None
    ) -> List[FactorValue]:
        """
        Convert IBKR tick data to instrument factor values.
        
        Args:
            instrument: The IBKRInstrument entity
            tick_data: Dictionary of tick_type_id -> value from IBKR
            timestamp: When the tick data was captured
            
        Returns:
            List of FactorValue entities
        """
        factor_values = []
        timestamp = timestamp or datetime.now()
        
        try:
            for tick_type_id, tick_value in tick_data.items():
                try:
                    # Convert tick type ID to enum
                    tick_type = IBKRTickType(tick_type_id)
                    
                    # Get factor mapping
                    factor_mapping = self.tick_mapper.get_factor_mapping(tick_type)
                    if not factor_mapping:
                        continue
                    
                    # Create instrument factor for this tick type
                    instrument_factor = self._create_instrument_factor(
                        instrument, tick_type, factor_mapping
                    )
                    
                    # Format the tick value
                    formatted_value = self.tick_mapper.format_tick_value(tick_type, tick_value)
                    
                    # Create factor value
                    factor_value = FactorValue(
                        id=None,  # Will be set by repository
                        factor_id=instrument_factor.factor_id,
                        entity_id=instrument.id,
                        date=timestamp.date(),
                        value=formatted_value
                    )
                    
                    factor_values.append(factor_value)
                    
                except (ValueError, KeyError) as e:
                    print(f"Skipping unknown tick type {tick_type_id}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error converting tick data to factor values: {e}")
            
        return factor_values
    
    def create_factor_value_for_tick(
        self,
        instrument: IBKRInstrument,
        tick_type: IBKRTickType,
        tick_value: Any,
        timestamp: Optional[datetime] = None
    ) -> Optional[FactorValue]:
        """
        Create a single factor value for a specific tick type.
        
        Args:
            instrument: The IBKRInstrument entity
            tick_type: IBKR tick type enum
            tick_value: Value from IBKR tick data
            timestamp: When the tick data was captured
            
        Returns:
            FactorValue entity or None if creation failed
        """
        try:
            timestamp = timestamp or datetime.now()
            
            # Get factor mapping
            factor_mapping = self.tick_mapper.get_factor_mapping(tick_type)
            if not factor_mapping:
                print(f"No factor mapping found for tick type {tick_type}")
                return None
            
            # Create instrument factor for this tick type
            instrument_factor = self._create_instrument_factor(
                instrument, tick_type, factor_mapping
            )
            
            # Format the tick value
            formatted_value = self.tick_mapper.format_tick_value(tick_type, tick_value)
            
            # Create factor value
            return FactorValue(
                id=None,  # Will be set by repository
                factor_id=instrument_factor.factor_id,
                entity_id=instrument.id,
                date=timestamp.date(),
                value=formatted_value
            )
            
        except Exception as e:
            print(f"Error creating factor value for tick type {tick_type}: {e}")
            return None
    
    def get_supported_tick_types(self) -> List[IBKRTickType]:
        """Get list of tick types that can be converted to factor values."""
        return self.tick_mapper.get_supported_tick_types()
    
    def is_tick_type_supported(self, tick_type: IBKRTickType) -> bool:
        """Check if a tick type is supported for factor mapping."""
        return self.tick_mapper.is_tick_type_supported(tick_type)
    
    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        """Safely convert a value to Decimal."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None
    
    def _extract_custom_metadata(
        self, 
        contract: Contract, 
        contract_details: ContractDetails
    ) -> Dict[str, Any]:
        """
        Extract additional metadata from contract and contract details.
        
        Args:
            contract: IBKR Contract object
            contract_details: IBKR ContractDetails object
            
        Returns:
            Dictionary of custom metadata
        """
        metadata = {}
        
        # Contract metadata
        metadata['strike'] = getattr(contract, 'strike', None)
        metadata['right'] = getattr(contract, 'right', None)
        metadata['multiplier'] = getattr(contract, 'multiplier', None)
        metadata['expiry'] = getattr(contract, 'lastTradeDateOrContractMonth', None)
        
        # ContractDetails metadata
        metadata['market_rule_ids'] = getattr(contract_details, 'marketRuleIds', '')
        metadata['real_expiration_date'] = getattr(contract_details, 'realExpirationDate', '')
        metadata['last_trade_time'] = getattr(contract_details, 'lastTradeTime', '')
        metadata['stock_type'] = getattr(contract_details, 'stockType', '')
        metadata['callable'] = getattr(contract_details, 'callable', None)
        metadata['puttable'] = getattr(contract_details, 'puttable', None)
        metadata['coupon'] = getattr(contract_details, 'coupon', None)
        metadata['convertible'] = getattr(contract_details, 'convertible', None)
        metadata['maturity'] = getattr(contract_details, 'maturity', None)
        metadata['issue_date'] = getattr(contract_details, 'issueDate', None)
        metadata['next_option_date'] = getattr(contract_details, 'nextOptionDate', None)
        metadata['next_option_type'] = getattr(contract_details, 'nextOptionType', None)
        metadata['next_option_partial'] = getattr(contract_details, 'nextOptionPartial', None)
        
        # Filter out None values
        return {k: v for k, v in metadata.items() if v is not None}
    
    def _create_instrument_factor(
        self,
        instrument: IBKRInstrument,
        tick_type: IBKRTickType,
        factor_mapping: FactorMapping
    ) -> InstrumentFactor:
        """
        Create an InstrumentFactor entity for a tick type.
        
        Args:
            instrument: The IBKRInstrument entity
            tick_type: IBKR tick type enum
            factor_mapping: Factor mapping configuration
            
        Returns:
            InstrumentFactor entity
        """
        return InstrumentFactor(
            name=factor_mapping.factor_name,
            group=factor_mapping.factor_group,
            subgroup=factor_mapping.factor_subgroup,
            data_type=factor_mapping.data_type,
            source="IBKR",
            definition=factor_mapping.description,
            factor_id=None,  # Will be resolved by repository
            
            # Instrument-specific attributes
            instrument_id=instrument.id,
            asset_type=instrument.security_type,
            data_provider="IBKR",
            frequency=factor_mapping.frequency,
            currency=instrument.currency,
            last_updated=datetime.now()
        )