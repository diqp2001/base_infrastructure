"""
ORM model for Bond - separate from src.domain entity to avoid metaclass conflicts.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from src.infrastructure.models.finance.financial_assets.financial_asset import FinancialAssetModel


class BondModel(FinancialAssetModel):
    """
    SQLAlchemy ORM model for Bond.
    Completely separate from src.domain entity to avoid metaclass conflicts.
    """
    __tablename__ = 'bonds'
    
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    isin = Column(String(12), nullable=False, index=True, unique=True)  # International Securities Identification Number
    cusip = Column(String(9), nullable=True, index=True)  # Committee on Uniform Securities Identification Procedures
    name = Column(String(255), nullable=False)  # Name of the bond
    issuer = Column(String(255), nullable=False)
    bond_type = Column(String(50), nullable=False)  # Government, Corporate, Municipal, etc.
    currency = Column(String(3), nullable=False, default='USD')  # Currency code
    
    # Bond terms
    face_value = Column(Numeric(15, 2), nullable=False, default=1000)
    coupon_rate = Column(Numeric(8, 4), nullable=False)  # Annual coupon rate
    issue_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    payment_frequency = Column(Integer, nullable=False, default=2)  # Payments per year
    
    # Credit information
    credit_rating = Column(String(10), nullable=True)  # AAA, AA+, etc.
    rating_agency = Column(String(50), nullable=True)  # Moody's, S&P, Fitch
    
    # Market data fields
    current_price = Column(Numeric(10, 4), nullable=True)  # % of face value
    yield_to_maturity = Column(Numeric(8, 4), nullable=True)
    duration = Column(Numeric(8, 4), nullable=True)  # Modified duration
    convexity = Column(Numeric(10, 4), nullable=True)
    accrued_interest = Column(Numeric(10, 4), nullable=True)
    last_update = Column(DateTime, nullable=True)
    
    # Status fields
    is_tradeable = Column(Boolean, default=True)
    is_callable = Column(Boolean, default=False)
    call_date = Column(Date, nullable=True)
    call_price = Column(Numeric(10, 4), nullable=True)
    
    # Market information
    outstanding_amount = Column(Numeric(20, 2), nullable=True)
    minimum_denomination = Column(Numeric(15, 2), default=1000)

    __mapper_args__ = {
        "polymorphic_identity": "bond",
    }

    def __repr__(self):
        return f"<Bond(id={self.id}, isin={self.isin}, issuer={self.issuer})>"
