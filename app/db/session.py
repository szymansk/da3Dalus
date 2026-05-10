
import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

SQLALCHEMY_DATABASE_URL = os.getenv(
    "SQLALCHEMY_DATABASE_URL",
    "sqlite:///./db/test.db",  # Fallback für lokal
)

_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

# SQLite: long-running async writers (assumption recompute) hold a
# transaction for several seconds while AeroBuildup runs. Without WAL +
# a generous busy_timeout, parallel writes (e.g. user clicking "Use
# calc" while a recompute is in flight) fail with "database is locked".
_engine_kwargs: dict = {}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {
        "check_same_thread": False,  # asyncio.to_thread workers cross threads
        "timeout": 30,                # block up to 30s on a locked DB instead of failing
    }

engine = create_engine(SQLALCHEMY_DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


if _is_sqlite:
    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        """Enable WAL + sane defaults on every new SQLite connection.

        WAL allows concurrent readers and a single writer to make
        progress without locking each other out — necessary because
        the assumption recompute keeps a write transaction open for
        several seconds.
        """
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
        finally:
            cursor.close()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()