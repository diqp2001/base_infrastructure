from .base import Base
from .connections import get_database_session
#from .models import Stock, Bond  # Import your SQLAlchemy models here

def initialize_database(db_type='sqlite'):
    session = get_database_session(db_type)
    Base.metadata.create_all(bind=session.bind)
