

from sqlalchemy.orm import DeclarativeBase

class ModelBase(DeclarativeBase):
    pass


from src.infrastructure.models.finance.financial_assets.company_stock import CompanyStock
from src.infrastructure.models.finance.financial_assets.stock import Stock
from src.infrastructure.models.finance.exchange import Exchange
from src.infrastructure.models.finance.company import Company
from src.infrastructure.models.country import Country
from src.infrastructure.models.industry import Industry
from src.infrastructure.models.sector import Sector
from infrastructure.models.keys.finance.financial_assets.key_company_stock import KeyCompanyStock
from src.infrastructure.models.keys.key import Key
from src.infrastructure.models.repos.repo import Repo
