from enum import Enum


class OptionType(Enum):
    """Standard option types."""
    CALL = "call"
    PUT = "put"

    @property
    def is_call(self) -> bool:
        return self == OptionType.CALL

    @property
    def is_put(self) -> bool:
        return self == OptionType.PUT

    def __str__(self):
        return self.value