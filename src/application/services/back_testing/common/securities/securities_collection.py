"""
Securities collection class for managing multiple securities.
"""

from typing import Dict, List, Optional, Iterator
from ..symbol import Symbol
from .security import Security


class Securities:
    """
    Dictionary-like collection for managing securities.
    Provides easy access to securities by symbol.
    """
    
    def __init__(self):
        self._securities: Dict[Symbol, Security] = {}
    
    def add(self, symbol: Symbol, security: Security) -> None:
        """Add a security to the collection."""
        self._securities[symbol] = security
    
    def remove(self, symbol: Symbol) -> bool:
        """Remove a security from the collection."""
        if symbol in self._securities:
            del self._securities[symbol]
            return True
        return False
    
    def get(self, symbol: Symbol) -> Optional[Security]:
        """Get a security by symbol."""
        return self._securities.get(symbol)
    
    def contains(self, symbol: Symbol) -> bool:
        """Check if a security exists in the collection."""
        return symbol in self._securities
    
    def keys(self) -> Iterator[Symbol]:
        """Get all symbols in the collection."""
        return iter(self._securities.keys())
    
    def values(self) -> Iterator[Security]:
        """Get all securities in the collection."""
        return iter(self._securities.values())
    
    def items(self) -> Iterator[tuple[Symbol, Security]]:
        """Get all symbol-security pairs."""
        return iter(self._securities.items())
    
    def clear(self) -> None:
        """Clear all securities from the collection."""
        self._securities.clear()
    
    def __len__(self) -> int:
        """Get the number of securities in the collection."""
        return len(self._securities)
    
    def __getitem__(self, symbol: Symbol) -> Security:
        """Get a security by symbol using bracket notation."""
        return self._securities[symbol]
    
    def __setitem__(self, symbol: Symbol, security: Security) -> None:
        """Set a security by symbol using bracket notation."""
        self._securities[symbol] = security
    
    def __delitem__(self, symbol: Symbol) -> None:
        """Delete a security by symbol using bracket notation."""
        del self._securities[symbol]
    
    def __contains__(self, symbol: Symbol) -> bool:
        """Check if a symbol exists using 'in' operator."""
        return symbol in self._securities
    
    def __iter__(self) -> Iterator[Symbol]:
        """Iterate over symbols."""
        return iter(self._securities.keys())
    
    def __repr__(self) -> str:
        """String representation of the collection."""
        return f"Securities({len(self._securities)} securities)"