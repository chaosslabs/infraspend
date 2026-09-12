from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import logging
from app.helpers.sandbox import sandbox_enabled

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@postgres:5432/dbname"
)


if sandbox_enabled():
    DATABASE_URL = "sqlite:///" + os.getenv(
        "PREVIEW_DB_PATH", "/tmp/infraspend-preview.db"
    )

logger.info("Initializing database connection")

engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {}
    ),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
