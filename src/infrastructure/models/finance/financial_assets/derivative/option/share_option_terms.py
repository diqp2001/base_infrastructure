"""
Columns of a listed option on a share (ShareOption in the domain), shared by the company share and ETF share option
tables: each keeps its own table, the contract terms are declared once.
"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import declared_attr


class ShareOptionTermsMixin:

    @declared_attr
    def exchange_id(cls):
        return Column(Integer, ForeignKey('exchanges.id'), nullable=False)

    strike_price = Column(Numeric(precision=15, scale=6), nullable=True)
    multiplier = Column(Numeric(precision=10, scale=2), nullable=True, default=1.0)
    expiry = Column(String(20), nullable=True)
