from abc import  abstractmethod
from datetime import date
from typing import Optional


class FinancialAsset():
    """
    Pure domain base class for all financial assets.
    No ORM, no persistence concerns, no discriminator column.
    """

    def __init__(
        self,
        id: Optional[int],
        name: Optional[str],symbol: Optional[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        self._id = id
        self._name = name
        self._symbol = symbol
        self._start_date = start_date
        self._end_date = end_date

    # -------- Identity --------
    @property
    def id(self) -> Optional[int]:
        return self._id

    # -------- Common attributes --------
    @property
    def name(self) -> Optional[str]:
        return self._name
    @property
    def symbol(self) -> Optional[str]:
        return self._symbol
    @property
    def start_date(self) -> Optional[date]:
        return self._start_date

    @property
    def end_date(self) -> Optional[date]:
        return self._end_date

    # -------- Polymorphic contract --------
    @property
    @abstractmethod
    def asset_type(self) -> str:
        """
        Business discriminator, not a DB column.
        Must be implemented by subclasses.
        """
        raise NotImplementedError

    # -------- Invariants / hooks --------
    def is_active_on(self, on_date: date) -> bool:
        if self._start_date and on_date < self._start_date:
            return False
        if self._end_date and on_date > self._end_date:
            return False
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self._id}, type={self.asset_type})>"
