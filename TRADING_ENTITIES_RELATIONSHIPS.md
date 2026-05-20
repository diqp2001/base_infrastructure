# Trading Entities Relationships Documentation

## Order → Transaction → Position → Holding → Portfolio Hierarchy

This document explains the hierarchical relationships between trading entities and their corresponding factor calculations in the base_infrastructure project.

---

## 1. 🔄 Trading Entity Hierarchy Flow

### **Order (Instruction)**
- **Definition**: An instruction to buy or sell a financial instrument
- **Key Factors**: 
  - Order Quantity Factor (how many shares to trade)
  - Order Price Factor (limit price or market order)
- **Relationships**: 
  - Belongs to a Portfolio (`portfolio_id`)
  - Targets a specific Holding (`holding_id`)
  - Can result in zero or multiple Transactions when executed

### **Transaction (Execution)**
- **Definition**: The actual execution/fulfillment of an order (partial or complete)
- **Key Factors**:
  - Transaction Quantity Factor (actual shares traded)
  - Transaction Price Factor (actual execution price)
- **Relationships**:
  - Originates from an Order (`order_id`)
  - Belongs to a Portfolio (`portfolio_id`)
  - Targets a specific Holding (`holding_id`)
  - Creates or modifies Positions

### **Position (Net Holdings)**
- **Definition**: Net quantity of shares after accounting for all transactions
- **Key Factors**:
  - Position Quantity Factor (net shares owned: buys - sells)
  - Position Price Factor (average cost basis or current market price)
- **Relationships**:
  - Aggregates multiple Transactions
  - Feeds into Holdings calculation
  - Can be LONG (positive quantity) or SHORT (negative quantity)

### **Holding (Portfolio Asset)**
- **Definition**: A financial asset held within a portfolio container
- **Key Factors**:
  - Holding Quantity Factor (total position in the asset)
  - Holding Value Factor (quantity × current price)
- **Relationships**:
  - Contains Position information
  - Links to a FinancialAsset (what is being held)
  - Belongs to a Portfolio container
  - Has start/end dates for lifecycle management

### **Portfolio (Asset Container)**
- **Definition**: Collection of multiple holdings representing an investment strategy
- **Key Factors**:
  - Portfolio Value Factor (sum of all holding values)
  - Portfolio Return Factor
  - Portfolio Risk Metrics
- **Relationships**:
  - Contains multiple Holdings
  - Aggregates value across all positions

---

## 2. 💰 Factor Value Calculation Dependencies

### **Portfolio Value = Sum(Holding Values)**
```python
# Portfolio Value Factor Dependencies
dependencies = {
    "holding_values": {
        "class": CompanySharePortfolioHoldingValueFactor,
        "parameters": {"independent_factor_related_entity_key": "holding_id"}
    }
}
```

### **Holding Value = Sum(Position Values)**
```python
# Holding Value Factor Dependencies  
dependencies = {
    "position_values": {
        "class": CompanySharePositionValueFactor,
        "parameters": {"independent_factor_related_entity_key": "position_id"}
    }
}
```

### **Position Value = Sum(Transaction Values)**
```python
# Position Value Factor Dependencies
dependencies = {
    "transaction_values": {
        "class": CompanyShareTransactionValueFactor,
        "parameters": {"independent_factor_related_entity_key": "transaction_id"}
    }
}
```

### **Transaction Value = Order Execution Results**
```python
# Transaction Value Factor Dependencies
dependencies = {
    "order_quantity": {
        "class": CompanyShareOrderQuantityFactor,
        "parameters": {"lag": 0}
    },
    "order_price": {
        "class": CompanyShareOrderPriceFactor, 
        "parameters": {"lag": 0}
    }
}
```

---

## 3. 🔗 Factor Dependency Chain

The factor calculation system creates a dependency chain where higher-level factors depend on lower-level factors:

```
Order Factors (quantity, price)
    ↓ (creates/influences)
Transaction Factors (executed quantity, execution price)  
    ↓ (aggregates to)
Position Factors (net quantity, average price)
    ↓ (feeds into)
Holding Factors (total quantity, market value)
    ↓ (sums to)
Portfolio Factors (total value, performance metrics)
```

---

## 4. 🏗️ Implementation Pattern

### **Repository Enhanced _create_or_get Pattern**

Each factor repository implements dependency creation using this pattern:

```python
def _create_or_get(self, entity_symbol, **kwargs):
    """Enhanced factor creation with automatic dependency resolution"""
    
    # 1. Create factor if doesn't exist
    factor = self._get_or_create_factor(**kwargs)
    
    # 2. Resolve dependencies from configuration
    dependencies = self._get_factor_dependencies_config()
    
    # 3. Create dependency factors
    for dep_name, dep_config in dependencies.items():
        entity_class = dep_config.get('class')
        repo = self.factory.get_local_repository(entity_class)
        
        dependency_entity = repo._create_or_get(
            entity_class,
            primary_key=dep_config.get("name"),
            group=dep_config.get("group"),
            subgroup=dep_config.get("subgroup"),
            # ... other parameters
        )
        
        # 4. Create dependency relationship
        repo_factor_dependency = self.factory.get_local_repository(FactorDependency)
        repo_factor_dependency._create_or_get(
            independent_factor=dependency_entity, 
            dependent_factor=factor,
            lag=dep_config.get("parameters", {}).get("lag"),
            independent_factor_related_entity_key=dep_config.get("parameters", {}).get("independent_factor_related_entity_key")
        )
    
    return factor
```

---

## 5. 📊 Factor Value Calculation

When calculating factor values, the system:

1. **Resolves Dependencies**: Finds all prerequisite factor values
2. **Calls Calculate Method**: Invokes the factor's `calculate()` method with dependency values
3. **Stores Result**: Persists the calculated value to the database

### **Example: Portfolio Value Calculation**

```python
def calculate(self, holdings_values: List[FactorValue]) -> Decimal:
    """Calculate portfolio value by summing holding values"""
    total_value = Decimal('0')
    for holding_value in holdings_values:
        total_value += holding_value.value
    return total_value
```

---

## 6. 🎯 Key Benefits

### **Automatic Dependency Resolution**
- Factors automatically create and track their dependencies
- No manual dependency management required

### **Consistent Calculation Chain**
- Values flow naturally from granular to aggregate levels  
- Portfolio values automatically reflect transaction-level changes

### **Flexible Factor Relationships**
- Support for lag parameters (using historical values)
- Entity-specific dependencies via related_entity_key

### **Database Integrity**
- All dependencies tracked in FactorDependency table
- Audit trail of calculation relationships

---

## 7. 🔄 Data Flow Example

### **New Order Placed** → **Portfolio Value Update**

1. **Order Created**: Order quantity/price factors get values
2. **Order Executed**: Transaction quantity/price factors calculated from order
3. **Position Updated**: Position factors recalculated from transaction history  
4. **Holding Refreshed**: Holding value factors updated from position changes
5. **Portfolio Recalculated**: Portfolio value factors updated from holding changes

This creates a natural flow where portfolio-level metrics automatically reflect the most granular trading activity.

---

## Implementation Status

- ✅ **Conceptual Framework**: Complete understanding of hierarchy
- ✅ **Domain Entities**: Order, Transaction, Position, Holding entities exist  
- ✅ **Factor Base Classes**: Portfolio and Holding value factors implemented
- 🚧 **Repository Enhancement**: Need to implement dependency creation in repositories
- 🚧 **Missing Factor Classes**: Position, Transaction, Order value factors need creation
- 🚧 **Factor Mappers**: Value factor mappers need implementation
- ⚠️ **Testing**: End-to-end calculation chain needs validation

---

*This document serves as the architectural guide for implementing the complete factor dependency chain in the trading system.*