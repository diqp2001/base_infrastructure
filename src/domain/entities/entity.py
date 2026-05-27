from typing import Optional


class Entity:
    """
    Pure domain base class for all non-factor domain entities.
    No ORM, no persistence concerns, no discriminator column.
    Provides a common identity contract (id) across all domain objects.
    """

    def __init__(self, id: Optional[int] = None):
        self.id = id

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"
