class Order:
    def __init__(self, symbol: str, quantity: int):
        self.symbol = symbol
        self.quantity = quantity

class MarketOrder(Order):
    pass

class LimitOrder(Order):
    def __init__(self, symbol: str, quantity: int, limit_price: float):
        super().__init__(symbol, quantity)
        self.limit_price = limit_price

class OrderEvent:
    def __init__(self, order: Order, status: str):
        self.order = order
        self.status = status
