"""
SecurityChanges class for tracking security additions and removals.
"""

from typing import List, Iterator
from dataclasses import dataclass, field

from .security import Security


@dataclass
class SecurityChanges:
    """
    Represents changes to the securities collection.
    Tracks which securities were added and removed.
    """
    added_securities: List[Security] = field(default_factory=list)
    removed_securities: List[Security] = field(default_factory=list)
    
    @property
    def count(self) -> int:
        """Total number of security changes."""
        return len(self.added_securities) + len(self.removed_securities)
    
    @property
    def added_count(self) -> int:
        """Number of securities added."""
        return len(self.added_securities)
    
    @property
    def removed_count(self) -> int:
        """Number of securities removed."""
        return len(self.removed_securities)
    
    def add_security(self, security: Security) -> None:
        """Add a security to the added collection."""
        self.added_securities.append(security)
    
    def remove_security(self, security: Security) -> None:
        """Add a security to the removed collection."""
        self.removed_securities.append(security)
    
    def __iter__(self) -> Iterator[Security]:
        """Iterate over all securities (added and removed)."""
        for security in self.added_securities:
            yield security
        for security in self.removed_securities:
            yield security
    
    def __len__(self) -> int:
        """Return the total number of changes."""
        return self.count
    
    def __str__(self) -> str:
        """String representation of the changes."""
        return f"SecurityChanges(Added: {self.added_count}, Removed: {self.removed_count})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"SecurityChanges(added_securities={len(self.added_securities)}, "
                f"removed_securities={len(self.removed_securities)})")