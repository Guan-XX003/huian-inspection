from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
_db_initialized = False


def get_db() -> Generator[Session, None, None]:
    ensure_db_initialized()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    global _db_initialized
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()
    _db_initialized = True


def ensure_db_initialized() -> None:
    if not _db_initialized:
        init_db()


def _apply_lightweight_migrations() -> None:
    from .models import StandardClause

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "standard_clauses" not in table_names:
        StandardClause.__table__.create(bind=engine, checkfirst=True)
    if "model_providers" not in table_names:
        return
    with engine.begin() as connection:
        existing_columns = {column["name"] for column in inspector.get_columns("model_providers")}
        if "api_key_secret" not in existing_columns:
            connection.execute(text("ALTER TABLE model_providers ADD COLUMN api_key_secret TEXT DEFAULT ''"))
        if "audit_tasks" in table_names:
            audit_columns = {column["name"] for column in inspector.get_columns("audit_tasks")}
            if "session_title" not in audit_columns:
                connection.execute(text("ALTER TABLE audit_tasks ADD COLUMN session_title VARCHAR(160) DEFAULT ''"))
            if "session_group" not in audit_columns:
                connection.execute(text("ALTER TABLE audit_tasks ADD COLUMN session_group VARCHAR(80) DEFAULT '默认分组'"))
            if "session_archived" not in audit_columns:
                connection.execute(text("ALTER TABLE audit_tasks ADD COLUMN session_archived BOOLEAN DEFAULT 0"))
