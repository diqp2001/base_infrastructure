"""
Share backtest class extending SecurityBackTest with share-specific functionality.
Provides shareholder rights, voting features, and ownership tracking.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from src.domain.entities.finance.back_testing.enums import SecurityType
from src.domain.entities.finance.back_testing.financial_assets.security_backtest import MarketData, SecurityBackTest
from src.domain.entities.finance.back_testing.financial_assets.symbol import Symbol


@dataclass
class ShareholderRight:
    """Value object for shareholder rights."""
    right_type: str  # e.g., "voting", "dividend", "liquidation"
    description: str
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    
    def is_active(self, current_date: datetime) -> bool:
        """Check if right is currently active."""
        if current_date < self.effective_date:
            return False
        if self.expiry_date and current_date > self.expiry_date:
            return False
        return True


@dataclass
class VotingEvent:
    """Value object for voting events."""
    proposal_id: str
    proposal_description: str
    voting_date: datetime
    votes_per_share: Decimal
    vote_cast: Optional[str] = None  # "for", "against", "abstain"
    
    def __post_init__(self):
        if self.votes_per_share < 0:
            raise ValueError("Votes per share cannot be negative")


class ShareBackTest(SecurityBackTest):
    """
    Share class extending SecurityBackTest with share-specific functionality.
    Provides shareholder rights, voting features, and ownership tracking.
    """
    
    def __init__(self, id: int, share_class: str, issuer_id: int, start_date: datetime, end_date: Optional[datetime] = None):
        # Create symbol for base Security class
        symbol = Symbol(
            value=f"SHARE_{issuer_id}_{share_class}",
            security_type=SecurityType.EQUITY  # Shares are equity securities
        )
        
        super().__init__(symbol)
        
        # Share-specific attributes
        self.id = id
        self.share_class = share_class
        self.issuer_id = issuer_id
        self.start_date = start_date
        self.end_date = end_date
        
        # Share-specific features
        self._shareholder_rights: List[ShareholderRight] = []
        self._voting_events: List[VotingEvent] = []
        self._par_value: Optional[Decimal] = None
        self._voting_power: Decimal = Decimal('1')  # Default 1 vote per share
        self._ownership_percentage: Optional[Decimal] = None
        self._transfer_restrictions: List[str] = []
        
    @property
    def issuer_identifier(self) -> int:
        """Get issuer ID."""
        return self.issuer_id
        
    @property
    def share_class_name(self) -> str:
        """Get share class."""
        return self.share_class
    
    @property
    def par_value(self) -> Optional[Decimal]:
        """Get par value per share."""
        return self._par_value
    
    @property
    def voting_power(self) -> Decimal:
        """Get voting power per share."""
        return self._voting_power
    
    @property
    def ownership_percentage(self) -> Optional[Decimal]:
        """Get ownership percentage if known."""
        return self._ownership_percentage
    
    @property
    def shareholder_rights(self) -> List[ShareholderRight]:
        """Get list of shareholder rights."""
        return self._shareholder_rights.copy()
    
    def _post_process_data(self, data: MarketData) -> None:
        """Share-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Update ownership percentage if total shares known
        self._update_ownership_calculation()
        
        # Check for upcoming voting events
        self._check_voting_events(data.timestamp)
    
    def _update_ownership_calculation(self) -> None:
        """Update ownership percentage calculation."""
        # This would require total shares outstanding information
        # In a real system, this would be calculated from company data
        pass
    
    def _check_voting_events(self, current_date: datetime) -> None:
        """Check for upcoming or active voting events."""
        for event in self._voting_events:
            if (event.voting_date - current_date).days <= 30:  # 30 days before voting
                # Notify about upcoming voting opportunity
                pass
    
    def set_par_value(self, par_value: Decimal) -> None:
        """Set par value for the shares."""
        if par_value < 0:
            raise ValueError("Par value cannot be negative")
        self._par_value = par_value
    
    def set_voting_power(self, votes_per_share: Decimal) -> None:
        """Set voting power per share."""
        if votes_per_share < 0:
            raise ValueError("Voting power cannot be negative")
        self._voting_power = votes_per_share
    
    def add_shareholder_right(self, right: ShareholderRight) -> None:
        """Add a shareholder right."""
        self._shareholder_rights.append(right)
        self._shareholder_rights.sort(key=lambda r: r.effective_date)
    
    def add_voting_event(self, event: VotingEvent) -> None:
        """Add a voting event."""
        self._voting_events.append(event)
        self._voting_events.sort(key=lambda e: e.voting_date, reverse=True)
    
    def get_active_rights(self, current_date: datetime) -> List[ShareholderRight]:
        """Get currently active shareholder rights."""
        return [right for right in self._shareholder_rights 
                if right.is_active(current_date)]
    
    def calculate_voting_power_total(self, shares_held: Optional[Decimal] = None) -> Decimal:
        """Calculate total voting power for held shares."""
        if shares_held is None:
            shares_held = self.holdings.quantity
        return shares_held * self._voting_power
    
    def cast_vote(self, proposal_id: str, vote: str) -> bool:
        """Cast vote for a specific proposal."""
        if vote not in ["for", "against", "abstain"]:
            raise ValueError("Vote must be 'for', 'against', or 'abstain'")
            
        for event in self._voting_events:
            if event.proposal_id == proposal_id:
                event.vote_cast = vote
                return True
        return False
    
    def add_transfer_restriction(self, restriction: str) -> None:
        """Add transfer restriction."""
        if restriction not in self._transfer_restrictions:
            self._transfer_restrictions.append(restriction)
    
    def remove_transfer_restriction(self, restriction: str) -> None:
        """Remove transfer restriction."""
        if restriction in self._transfer_restrictions:
            self._transfer_restrictions.remove(restriction)
    
    def can_transfer(self) -> bool:
        """Check if shares can be transferred."""
        return len(self._transfer_restrictions) == 0
    
    def calculate_book_value(self, total_book_value: Decimal, total_shares: Decimal) -> Decimal:
        """Calculate book value per share."""
        if total_shares <= 0:
            raise ValueError("Total shares must be positive")
        return total_book_value / total_shares
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for share position.
        May vary based on share class and restrictions.
        """
        position_value = abs(quantity * self.price)
        
        # Higher margin for restricted shares
        if self._transfer_restrictions:
            margin_rate = Decimal('0.50')  # 50% for restricted shares
        else:
            margin_rate = Decimal('0.30')  # 30% for regular shares
        
        if quantity >= 0:  # Long position
            return position_value * margin_rate
        else:  # Short position
            return position_value * (margin_rate + Decimal('0.20'))
    
    def get_contract_multiplier(self) -> Decimal:
        """Shares have a contract multiplier of 1."""
        return Decimal('1')
    
    @property
    def asset_type(self) -> str:
        """Override for backwards compatibility."""
        return "Share"
    
    def __str__(self) -> str:
        return f"Share({self.share_class}, Issuer:{self.issuer_id}, ${self.price})"
    
    def __repr__(self) -> str:
        return (f"Share(id={self.id}, class={self.share_class}, "
                f"issuer={self.issuer_id}, price={self.price}, "
                f"voting_power={self.voting_power})")