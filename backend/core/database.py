"""Motor SQLite en modo WAL con transacciones atómicas."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from backend.core.config import get_settings

_engine: Engine | None = None


def _enable_wal(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def get_engine(url: str | None = None) -> Engine:
    global _engine
    if _engine is None or url is not None:
        engine = create_engine(url or get_settings().database_url,
                               connect_args={"check_same_thread": False})
        event.listen(engine, "connect", _enable_wal)
        import backend.models.ledger  # noqa: F401  registra las tablas
        SQLModel.metadata.create_all(engine)
        if url is not None:
            return engine
        _engine = engine
    return _engine


def set_engine(engine: Engine) -> None:
    """Permite inyectar un engine (tests en memoria)."""
    global _engine
    _engine = engine


@contextmanager
def atomic() -> Iterator[Session]:
    """Sesión transaccional: commit si todo va bien, rollback ante cualquier error."""
    with Session(get_engine(), expire_on_commit=False) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
