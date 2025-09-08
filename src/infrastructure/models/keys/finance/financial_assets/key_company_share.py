from sqlalchemy import Column, ForeignKey, Integer, String, Date
from sqlalchemy.orm import relationship
from src.infrastructure.models import ModelBase as Base

class KeyCompanyShare(Base):
    __tablename__ = 'key_company_shares'
    __table_args__ = {'extend_existing': True}


    id = Column(Integer, primary_key=True, nullable=False)
    company_share_id = Column(Integer, ForeignKey('company_shares.id'), nullable=False)
    repo_id = Column(Integer,  ForeignKey('repo.id'),nullable=False)
    key_id = Column(Integer, ForeignKey('key.id'), nullable=False)
    key_value = Column(Integer, nullable=False)  # e.g., '989898'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    extend_existing = True

    # Relationship with CompanyShare
    company_share = relationship("CompanyShare", back_populates="key_company_shares")
    key = relationship("Key", back_populates="key_company_shares")
    repo = relationship("Repo", back_populates="key_company_shares")
    
    def __repr__(self):
        return f"<KeyCompanyShare(key_id={self.key_id}, key_value={self.key_value})>"