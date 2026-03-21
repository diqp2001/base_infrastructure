from typing import List, Optional
from src.domain.entities.finance.transaction.transaction import Transaction


class TransactionPort:
    """Port interface for Transaction entity operations following repository pattern."""

    def get_by_id(self, id: int) -> Optional[Transaction]:
        pass

    def get_by_transaction_id(self, transaction_id: str) -> Optional[Transaction]:
        pass

    def get_by_external_transaction_id(self, external_transaction_id: str) -> Optional[Transaction]:
        pass

    def get_by_account_id(self, account_id: str) -> List[Transaction]:
        pass

    def get_by_portfolio_id(self, portfolio_id: int) -> List[Transaction]:
        pass

    def get_by_order_id(self, order_id: int) -> List[Transaction]:
        pass

    def get_all(self) -> List[Transaction]:
        pass

    def add(self, entity: Transaction) -> Optional[Transaction]:
        pass

    def update(self, entity: Transaction) -> Optional[Transaction]:
        pass

    def delete(self, id: int) -> bool:
        pass