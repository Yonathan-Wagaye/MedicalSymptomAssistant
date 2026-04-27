from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.core.config import config

# manages conenction pool
engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)

# session factory 
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# a base class for orm models
Base = declarative_base()

# dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
