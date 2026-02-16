from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def flush_db():
    """Delete all data from database tables. Use for starting fresh with tests."""
    from app.models import Analysis, PortfolioEntry, Listing, WatchlistItem, SearchURL

    init_db()  # Ensure tables exist (creates them if database is new)
    db = SessionLocal()
    try:
        db.query(Analysis).delete()
        db.query(PortfolioEntry).delete()
        db.query(Listing).delete()
        db.query(WatchlistItem).delete()
        db.query(SearchURL).delete()
        db.commit()
    finally:
        db.close()
