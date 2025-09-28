from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def init_engine(settings: Settings) -> Engine:
    global _engine, _session_factory
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            future=True,
        )
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session, future=True)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Engine not initialized. Call init_engine(settings) first.")
    return _engine


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    if _session_factory is None:
        raise RuntimeError("Session factory not initialized. Call init_engine(settings) first.")
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def healthcheck(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
