from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings


def get_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or settings.database_url)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
