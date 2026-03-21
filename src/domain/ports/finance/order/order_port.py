from typing import List, Optional
from src.domain.entities.finance.order.order import Order


class OrderPort:
    """Port interface for Order entity operations following repository pattern."""

    def get_by_id(self, id: int) -> Optional[Order]:
        pass

    def get_by_external_order_id(self, external_order_id: str) -> Optional[Order]:
        pass

    def get_by_account_id(self, account_id: str) -> List[Order]:
        pass

    def get_by_portfolio_id(self, portfolio_id: int) -> List[Order]:
        pass

    def get_active_orders(self) -> List[Order]:
        pass

    def get_all(self) -> List[Order]:
        pass

    def add(self, entity: Order) -> Optional[Order]:
        pass

    def update(self, entity: Order) -> Optional[Order]:
        pass

    def delete(self, id: int) -> bool:
        pass