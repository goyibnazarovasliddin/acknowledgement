from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401 — ensures models are registered
    Base.metadata.create_all(bind=engine)
    _migrate_columns()


def _migrate_columns():
    """Add new columns to existing tables (SQLite create_all won't ALTER)."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "documents" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("documents")}
    stmts = []
    if "archived" not in cols:
        stmts.append("ALTER TABLE documents ADD COLUMN archived BOOLEAN NOT NULL DEFAULT 0")
    if "archived_at" not in cols:
        stmts.append("ALTER TABLE documents ADD COLUMN archived_at DATETIME")
    if stmts:
        with engine.begin() as conn:
            for s in stmts:
                conn.execute(text(s))
