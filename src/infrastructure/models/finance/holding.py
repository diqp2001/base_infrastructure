"""
Infrastructure models for holdings - SQLAlchemy models matching domain entities
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.infrastructure.models import ModelBase as Base


class HoldingModel(Base):
    """
    Base SQLAlchemy model for holdings.
    Maps to domain.entities.finance.holding.holding.Holding
    """
    __tablename__ = 'holdings'

    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey('financial_assets.id'), nullable=False)
    container_id = Column(Integer, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)

    # Relationships
    asset = relationship("FinancialAssetModel", back_populates="holdings")


class PortfolioHoldingModel(HoldingModel):
    """
    SQLAlchemy model for portfolio holdings.
    Maps to domain.entities.finance.holding.portfolio_holding.PortfolioHolding
    """
    __tablename__ = 'portfolio_holdings'
    
    id = Column(Integer, ForeignKey('holdings.id'), primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)

    # Relationships
    portfolio = relationship("PortfolioModel", back_populates="holdings")


class PortfolioCompanyShareHoldingModel(PortfolioHoldingModel):
    """
    SQLAlchemy model for company share holdings within a portfolio.
    Maps to domain.entities.finance.holding.portfolio_company_share_holding.PortfolioCompanyShareHolding
    """
    __tablename__ = 'portfolio_company_share_holdings'
    
    id = Column(Integer, ForeignKey('portfolio_holdings.id'), primary_key=True)
    company_share_id = Column(Integer, ForeignKey('company_shares.id'), nullable=False)
    portfolio_company_share_id = Column(Integer, ForeignKey('portfolio_company_shares.id'), nullable=False)

    # Relationships
    company_share = relationship("CompanyShareModel")
    portfolio_company_share = relationship("PortfolioCompanyShareModel")