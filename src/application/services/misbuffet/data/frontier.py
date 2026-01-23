from datetime import datetime, timedelta

class Frontier:
    """
    Maintains a time frontier to prevent look-ahead bias.
    The frontier can only advance forward in time, never backwards.
    """

    def __init__(self, frontier: datetime):
        self.frontier = frontier

    def advance(self, new_time: datetime):
        """
        Advance the frontier to a new time.
        
        Args:
            new_time: New frontier time
            
        Raises:
            ValueError: If new_time is before current frontier
        """
        if new_time < self.frontier:
            raise ValueError(f"Cannot go backwards: {new_time} < {self.frontier}")
        self.frontier = new_time

    def can_access(self, time: datetime) -> bool:
        """
        Check if data at given time can be accessed.
        
        Args:
            time: Time to check
            
        Returns:
            True if time is at or before the frontier
        """
        return time <= self.frontier

    def __str__(self) -> str:
        return f"Frontier({self.frontier})"

    def __repr__(self) -> str:
        return self.__str__()