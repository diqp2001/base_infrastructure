from typing import List, Optional
from src.domain.entities.finance.account import Account


class AccountPort:
    """Port interface for Account entity operations following repository pattern."""

    def get_by_id(self, id: int) -> Optional[Account]:
        pass

    def get_by_account_id(self, account_id: str) -> Optional[Account]:
        pass

    def get_all(self) -> List[Account]:
        pass

    def add(self, entity: Account) -> Optional[Account]:
        pass

    def update(self, entity: Account) -> Optional[Account]:
        pass

    def delete(self, id: int) -> bool:
        pass