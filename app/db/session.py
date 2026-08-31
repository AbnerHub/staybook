from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session]:
    """FastAPI dependency that yields a database session and owns the transaction.

    Commits on success so writes performed by the services (which only flush)
    are persisted, and rolls back if the request raises, so no partial state is
    committed. Services that commit explicitly (e.g. StayService) remain
    correct: the trailing commit here is a no-op once the transaction is clean.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
