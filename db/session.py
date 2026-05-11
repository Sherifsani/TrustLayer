import os
import uuid as _uuid
from typing import Generator, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

from api.models.db_models import Base, User

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/trustlayer")
# Railway injects postgres:// but SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user(db: Session, user_id: str) -> Optional[User]:
    """Look up a User by UUID string or user_handle (e.g. 'usr_adaeze001')."""
    try:
        uid = _uuid.UUID(user_id)
        return db.query(User).filter(User.id == uid).first()
    except ValueError:
        return db.query(User).filter(User.user_handle == user_id).first()


def create_tables():
    Base.metadata.create_all(bind=engine)
