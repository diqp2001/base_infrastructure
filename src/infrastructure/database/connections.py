from .settings import get_database_url
from .base import create_engine_and_session
from sqlalchemy.orm import Session

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Get a session for the given database type
def get_database_session(db_type='sqlite') -> Session:
    """
    Returns a new session for the database type passed.
    """
    database_url = get_database_url(db_type)
    engine, SessionLocal = create_engine_and_session(database_url)
    return SessionLocal()