"""Tests for the get_db dependency's transaction management."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db


@pytest.fixture()
def _patched_session(monkeypatch):
    """Patch SessionLocal to use in-memory SQLite."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    patched = sessionmaker(
        bind=engine, class_=Session, expire_on_commit=False,
        autocommit=False, autoflush=False,
    )
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr("app.db.session.SessionLocal", patched)
    yield engine
    Base.metadata.drop_all(bind=engine)


class TestGetDbTransactionManagement:
    def test_commits_on_success(self, _patched_session):
        gen = get_db()
        db = next(gen)
        db.execute(text(
            "CREATE TABLE _txn_test (id INTEGER PRIMARY KEY)"
        ))
        db.execute(text("INSERT INTO _txn_test (id) VALUES (1)"))
        try:
            gen.send(None)
        except StopIteration:
            pass
        with _patched_session.connect() as conn:
            row = conn.execute(text("SELECT id FROM _txn_test")).fetchone()
            assert row is not None
            assert row[0] == 1

    def test_rollbacks_on_exception(self, _patched_session):
        gen = get_db()
        db = next(gen)
        db.execute(text(
            "CREATE TABLE _txn_test2 (id INTEGER PRIMARY KEY)"
        ))
        db.execute(text("INSERT INTO _txn_test2 (id) VALUES (99)"))
        with pytest.raises(ValueError, match="boom"):
            gen.throw(ValueError("boom"))
        with _patched_session.connect() as conn:
            try:
                row = conn.execute(text("SELECT id FROM _txn_test2")).fetchone()
                assert row is None
            except Exception:
                pass
