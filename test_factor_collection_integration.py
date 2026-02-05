"""
Test script for factor collection entities integration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.factor_serie_collection import FactorSerieCollection
from src.domain.entities.factor.factor_value_collection import FactorValueCollection


def test_factor_serie_collection():
    """Test FactorSerieCollection entity."""
    print("Testing FactorSerieCollection...")
    
    # Create test factors
    factor1 = Factor(name="test_factor_1", group="test", subgroup="momentum", factor_id=1)
    factor2 = Factor(name="test_factor_2", group="test", subgroup="technical", factor_id=2)
    
    # Create collection
    collection = FactorSerieCollection(factors=[factor1, factor2])
    
    # Test methods
    assert len(collection) == 2
    assert collection.get_factor_by_name("test_factor_1") == factor1
    assert len(collection.get_factors_by_group("test")) == 2
    assert len(collection.get_factors_by_subgroup("momentum")) == 1
    assert collection.get_factor_ids() == [1, 2]
    
    print("✓ FactorSerieCollection tests passed")


def test_factor_value_collection():
    """Test FactorValueCollection entity."""
    print("Testing FactorValueCollection...")
    
    # Create test factor values
    fv1 = FactorValue(id=1, factor_id=1, entity_id=100, date=datetime(2024, 1, 1), value="10.5")
    fv2 = FactorValue(id=2, factor_id=2, entity_id=100, date=datetime(2024, 1, 1), value="20.3")
    fv3 = FactorValue(id=3, factor_id=1, entity_id=101, date=datetime(2024, 1, 2), value="15.7")
    
    # Create collection
    collection = FactorValueCollection(factor_values=[fv1, fv2, fv3])
    
    # Test methods
    assert len(collection) == 3
    assert len(collection.get_values_by_factor_id(1)) == 2
    assert len(collection.get_values_by_entity_id(100)) == 2
    assert len(collection.get_values_by_factor_and_entity(1, 100)) == 1
    assert collection.get_unique_factor_ids() == [1, 2]
    assert collection.get_unique_entity_ids() == [100, 101]
    
    print("✓ FactorValueCollection tests passed")


def test_integration():
    """Test overall integration."""
    print("Testing integration...")
    
    # Test imports
    from src.domain.ports.factor.factor_serie_collection_port import FactorSerieCollectionPort
    from src.domain.ports.factor.factor_value_collection_port import FactorValueCollectionPort
    from src.infrastructure.repositories.mappers.factor.factor_serie_collection_mapper import FactorSerieCollectionMapper
    from src.infrastructure.repositories.mappers.factor.factor_value_collection_mapper import FactorValueCollectionMapper
    
    print("✓ All imports successful")
    
    # Test mapper functionality
    factor1 = Factor(name="mapper_test", group="test", subgroup="test", factor_id=1)
    collection = FactorSerieCollectionMapper.from_factor_list([factor1])
    assert collection is not None
    assert len(collection) == 1
    
    fv1 = FactorValue(id=1, factor_id=1, entity_id=100, date=datetime(2024, 1, 1), value="10.5")
    value_collection = FactorValueCollectionMapper.from_factor_value_list([fv1])
    assert value_collection is not None
    assert len(value_collection) == 1
    
    print("✓ Mapper integration tests passed")


if __name__ == "__main__":
    test_factor_serie_collection()
    test_factor_value_collection()
    test_integration()
    print("All tests completed successfully!")