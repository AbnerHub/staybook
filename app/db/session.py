from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session]:
    """FastAPI dependency that yields a database session and handles cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
