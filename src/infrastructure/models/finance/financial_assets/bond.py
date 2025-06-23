from sqlalchemy import Column, Integer, String, Float, Date
from src.infrastructure.models import ModelBase as Base # Base class for SQLAlchemy models

class Bond(Base):
    __tablename__ = 'bonds'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)  # Name of the bond (e.g., 'US Government Bond')
    bond_type = Column(String, nullable=False)  # Type of bond (e.g., 'Government', 'Corporate')
    coupon_rate = Column(Float, nullable=False)  # Coupon rate as a percentage
    maturity_date = Column(Date, nullable=False)  # Maturity date of the bond
    face_value = Column(Float, nullable=False)  # Face value (par value) of the bond
    issue_date = Column(Date, nullable=True)  # Issue date of the bond
    currency = Column(String, nullable=False)  # Currency (e.g., 'USD', 'EUR')

    def __repr__(self):
        return f"<Bond(id={self.id}, name={self.name}, bond_type={self.bond_type}, coupon_rate={self.coupon_rate}, maturity_date={self.maturity_date}, face_value={self.face_value}, issue_date={self.issue_date}, currency={self.currency})>"

    def __init__(self, name: str, bond_type: str, coupon_rate: float, maturity_date: str, face_value: float, issue_date: str, currency: str):
        self.name = name
        self.bond_type = bond_type
        self.coupon_rate = coupon_rate
        self.maturity_date = maturity_date
        self.face_value = face_value
        self.issue_date = issue_date
        self.currency = currency
