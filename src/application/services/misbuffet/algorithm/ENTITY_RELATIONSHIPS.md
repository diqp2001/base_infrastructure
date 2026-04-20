# ENTITY_RELATIONSHIPS.md - Unified Portfolio Management Entity Relationships

## Overview

This document explains how the core domain entities interact within the UnifiedPortfolioManager system, replacing the dual portfolio tracking approach with a unified repository-backed system.

## Core Entity Relationships

### 📊 **Portfolio Entities**

#### **Portfolio** (Base Entity)
```python
class Portfolio:
    id: int                  # Primary key
    name: str               # Portfolio name
    start_date: date        # Portfolio creation date  
    end_date: Optional[date] # Portfolio end date (None for active)
```

#### **PortfolioCompanyShare** (Specialized Portfolio)
```python
class PortfolioCompanyShare(Portfolio):
    # Inherits all Portfolio fields
    # Specialized for equity-only portfolios
```

**Key Relationships:**
- 📈 **One-to-Many** with Holdings: `Portfolio → [Holding]`
- 📋 **One-to-Many** with Orders: `Portfolio → [Order]`  
- 💼 **One-to-Many** with Transactions: `Portfolio → [Transaction]`

---

### 💰 **Transaction Entity**

```python
class Transaction:
    id: int                 # Primary key
    portfolio_id: int       # Foreign key → Portfolio.id
    holding_id: int         # Foreign key → Holding.id
    order_id: int          # Foreign key → Order.id
    
    # Core transaction data
    date: datetime
    transaction_type: TransactionType
    transaction_id: str     # Business transaction ID
    account_id: str
    trade_date: date
    value_date: date
    settlement_date: date
    status: TransactionStatus
    spread: float
    currency_id: int
    exchange_id: int
    external_transaction_id: Optional[str]
```

**Entity Relationships:**
- **Belongs to Portfolio** → `Transaction.portfolio_id` references `Portfolio.id`
- **Belongs to Holding** → `Transaction.holding_id` references `Holding.id`  
- **Executes Order** → `Transaction.order_id` references `Order.id`

**Business Logic:**
- Transactions represent **completed executions** of orders
- One order can have multiple transactions (partial fills)
- Transactions update the quantity in associated Holdings

---

### 📋 **Order Entity**

```python
class Order:
    id: int                 # Primary key
    portfolio_id: int       # Foreign key → Portfolio.id
    holding_id: int        # Foreign key → Holding.id
    
    # Order specification
    order_type: OrderType  # MARKET, LIMIT, STOP, STOP_LIMIT
    side: OrderSide       # BUY, SELL
    quantity: float
    created_at: datetime
    status: OrderStatus   # PENDING, SUBMITTED, FILLED, CANCELLED, etc.
    account_id: str
    
    # Optional order details
    price: Optional[float]              # For limit orders
    stop_price: Optional[float]         # For stop orders
    filled_quantity: float = 0.0       # Amount already filled
    average_fill_price: Optional[float] # Average execution price
    external_order_id: Optional[str]    # QCAlgorithm order ID
```

**Entity Relationships:**
- **Belongs to Portfolio** → `Order.portfolio_id` references `Portfolio.id`
- **Targets Holding** → `Order.holding_id` references `Holding.id`
- **Generates Transactions** → `Order → [Transaction]` (when filled)

**Business Logic:**
- Orders represent **intent to trade** a specific holding
- Orders can be partially filled, creating multiple transactions
- QCAlgorithm order tickets are mapped to domain orders

---

### 📈 **Holding Entities**

#### **Holding** (Base Entity)
```python
class Holding:
    id: int                    # Primary key
    asset: FinancialAsset      # The underlying financial instrument
    container: object          # Container (Portfolio) holding this asset
    position: Position         # Position details (quantity, type)
    start_date: datetime       # When holding started
    end_date: Optional[datetime] # When holding ended (None for active)
```

#### **PortfolioCompanyShareHolding** (Specialized Holding)
```python
class PortfolioCompanyShareHolding(PortfolioHolding):
    asset: CompanyShare              # Specialized asset type
    portfolio: PortfolioCompanyShare # Specialized portfolio type
    position: Position              # Position details
    # Inherits other fields from Holding
```

**Entity Relationships:**
- **Belongs to Portfolio** → `Holding.container` references Portfolio
- **Contains Position** → `Holding.position` references Position
- **Has Transactions** → `Holding ← [Transaction]` (via holding_id)
- **Has Orders** → `Holding ← [Order]` (via holding_id)

**Business Logic:**
- Holdings represent **ownership positions** in specific assets within a portfolio
- One portfolio can have multiple holdings of the same asset type
- Holdings track **when** an asset was held (start_date/end_date)

---

### 🎯 **Position Entity**

```python
class Position:
    id: int                  # Primary key
    quantity: int            # Number of units held
    position_type: PositionType # LONG, SHORT
```

**Entity Relationships:**
- **One-to-One** with Holding → `Holding.position` references Position
- **Updated by Transactions** → Transaction executions modify quantity

**Business Logic:**
- Position represents the **current quantity and direction** of a holding
- Quantity is updated when transactions execute
- PositionType indicates whether the position is LONG (bullish) or SHORT (bearish)

---

## Complete Entity Interaction Flow

### 📋 **Order Execution Workflow**

1. **Portfolio Registration**
   ```python
   portfolio = Portfolio(name="SPX_Strategy", start_date=today)
   ```

2. **Order Creation**
   ```python
   order = Order(
       portfolio_id=portfolio.id,
       holding_id=target_holding.id,  # Asset we want to trade
       order_type=OrderType.MARKET,
       side=OrderSide.BUY,
       quantity=100
   )
   ```

3. **Transaction Recording** (when order fills)
   ```python
   transaction = Transaction(
       portfolio_id=portfolio.id,
       holding_id=order.holding_id,
       order_id=order.id,
       # ... execution details
   )
   ```

4. **Position Update**
   ```python
   holding.position.quantity += transaction_quantity
   ```

### 🔄 **Data Flow Relationships**

```
Portfolio
    ├── Holdings (1:N)
    │   ├── Position (1:1) 
    │   ├── FinancialAsset (1:1)
    │   └── Transactions (1:N) ← Updates position
    │
    ├── Orders (1:N)
    │   └── Transactions (1:N) ← Executes orders
    │
    └── Transactions (1:N)
        ├── References Portfolio (N:1)
        ├── References Holding (N:1)
        └── References Order (N:1)
```

### 💻 **Repository Pattern Integration**

Each entity is managed through its repository:
- **PortfolioRepository** → Creates/retrieves portfolios
- **HoldingRepository** → Manages asset holdings within portfolios  
- **OrderRepository** → Tracks trading orders
- **TransactionRepository** → Records trade executions
- **PositionRepository** → Updates position quantities

### 🎯 **UnifiedPortfolioManager Integration**

The UnifiedPortfolioManager orchestrates these entities:

1. **Portfolio Value Calculation** → Aggregates holding market values
2. **Position Tracking** → Retrieves active holdings with non-zero quantities
3. **Order Management** → Converts QCAlgorithm orders to domain entities
4. **Transaction Recording** → Captures trade executions and updates holdings
5. **State Reporting** → Provides unified view across all entities

---

## Key Design Principles

### ✅ **Single Source of Truth**
- Domain entities replace custom tracking dictionaries
- Repository pattern ensures data consistency
- All portfolio operations flow through unified system

### ✅ **Clean Entity Separation**
- **Portfolio** → Container identification
- **Holding** → Asset ownership within portfolio
- **Position** → Current quantity and direction
- **Order** → Trading intent
- **Transaction** → Completed trade execution

### ✅ **Referential Integrity**
- Foreign key relationships enforce data consistency
- Transactions must reference valid portfolio, holding, and order
- Orders must reference valid portfolio and holding

### ✅ **Temporal Tracking**
- Holdings have start_date/end_date for lifecycle management
- Orders have created_at for chronological ordering
- Transactions have trade_date, value_date, settlement_date for trade lifecycle

This unified system replaces the previous dual tracking approach (QCAlgorithm portfolio + custom dictionaries) with a single, repository-backed entity system that maintains complete referential integrity and provides comprehensive portfolio management capabilities.