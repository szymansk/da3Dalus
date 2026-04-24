"""Tests for app.services.copilot_history_service — per-aeroplane chat persistence."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import patch, MagicMock

from app.core.exceptions import InternalError, NotFoundError
from app.models.aeroplanemodel import CopilotMessageModel
from app.schemas.copilot_history import CopilotMessageWrite
from app.services import copilot_history_service as svc
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_msg_write(
    role: str = "user",
    content: str = "hello",
    tool_calls=None,
    tool_results=None,
    parent_id=None,
) -> CopilotMessageWrite:
    return CopilotMessageWrite(
        role=role,
        content=content,
        tool_calls=tool_calls,
        tool_results=tool_results,
        parent_id=parent_id,
    )


# ---------------------------------------------------------------------------
# _get_aeroplane
# ---------------------------------------------------------------------------

class TestGetAeroplane:
    """Tests for the shared _get_aeroplane helper."""

    def test_raises_not_found_for_unknown_uuid(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc._get_aeroplane(db, uuid.uuid4())

    def test_returns_aeroplane_for_valid_uuid(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            result = svc._get_aeroplane(db, aeroplane.uuid)
            assert result.id == aeroplane.id


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------

class TestGetHistory:
    """Tests for get_history."""

    def test_empty_history_for_new_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = svc.get_history(db, aeroplane.uuid)
            assert history.messages == []

    def test_returns_messages_in_order(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.append_message(db, aeroplane.uuid, _make_msg_write(content="first"))
            svc.append_message(db, aeroplane.uuid, _make_msg_write(content="second"))

            history = svc.get_history(db, aeroplane.uuid)
            assert len(history.messages) == 2
            assert history.messages[0].content == "first"
            assert history.messages[1].content == "second"

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.get_history(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# append_message
# ---------------------------------------------------------------------------

class TestAppendMessage:
    """Tests for append_message."""

    def test_append_user_message(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            msg = svc.append_message(db, aeroplane.uuid, _make_msg_write(content="hi"))

            assert msg.id is not None
            assert msg.role == "user"
            assert msg.content == "hi"
            assert msg.created_at is not None

    def test_append_assistant_message_with_tool_calls(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            tool_calls = [{"name": "get_wing", "args": {}}]
            msg = svc.append_message(
                db, aeroplane.uuid,
                _make_msg_write(role="assistant", content="", tool_calls=tool_calls),
            )
            assert msg.role == "assistant"
            assert msg.tool_calls == tool_calls

    def test_append_tool_message_with_results(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            tool_results = [{"output": "ok"}]
            msg = svc.append_message(
                db, aeroplane.uuid,
                _make_msg_write(role="tool", content="", tool_results=tool_results),
            )
            assert msg.role == "tool"
            assert msg.tool_results == tool_results

    def test_append_with_parent_id(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            first = svc.append_message(db, aeroplane.uuid, _make_msg_write(content="root"))
            child = svc.append_message(
                db, aeroplane.uuid,
                _make_msg_write(content="reply", parent_id=first.id),
            )
            assert child.parent_id == first.id

    def test_sort_index_increments(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.append_message(db, aeroplane.uuid, _make_msg_write(content="a"))
            svc.append_message(db, aeroplane.uuid, _make_msg_write(content="b"))

            msgs = db.query(CopilotMessageModel).filter(
                CopilotMessageModel.aeroplane_id == aeroplane.id
            ).order_by(CopilotMessageModel.sort_index).all()
            assert msgs[0].sort_index == 0
            assert msgs[1].sort_index == 1

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.append_message(db, uuid.uuid4(), _make_msg_write())

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            with patch.object(db, "commit", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.append_message(db, aeroplane.uuid, _make_msg_write())


# ---------------------------------------------------------------------------
# clear_history
# ---------------------------------------------------------------------------

class TestClearHistory:
    """Tests for clear_history."""

    def test_clear_removes_all_messages(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.append_message(db, aeroplane.uuid, _make_msg_write(content="a"))
            svc.append_message(db, aeroplane.uuid, _make_msg_write(content="b"))

            svc.clear_history(db, aeroplane.uuid)
            history = svc.get_history(db, aeroplane.uuid)
            assert history.messages == []

    def test_clear_on_empty_history_is_noop(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.clear_history(db, aeroplane.uuid)  # should not raise
            history = svc.get_history(db, aeroplane.uuid)
            assert history.messages == []

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.clear_history(db, uuid.uuid4())

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            svc.append_message(db, aeroplane.uuid, _make_msg_write(content="x"))
            with patch.object(db, "commit", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.clear_history(db, aeroplane.uuid)


# ---------------------------------------------------------------------------
# delete_message
# ---------------------------------------------------------------------------

class TestDeleteMessage:
    """Tests for delete_message."""

    def test_delete_specific_message(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            m1 = svc.append_message(db, aeroplane.uuid, _make_msg_write(content="keep"))
            m2 = svc.append_message(db, aeroplane.uuid, _make_msg_write(content="delete me"))

            svc.delete_message(db, aeroplane.uuid, m2.id)
            history = svc.get_history(db, aeroplane.uuid)
            assert len(history.messages) == 1
            assert history.messages[0].id == m1.id

    def test_raises_not_found_for_missing_message(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            with pytest.raises(NotFoundError):
                svc.delete_message(db, aeroplane.uuid, 99999)

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.delete_message(db, uuid.uuid4(), 1)

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            msg = svc.append_message(db, aeroplane.uuid, _make_msg_write(content="x"))
            with patch.object(db, "commit", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.delete_message(db, aeroplane.uuid, msg.id)


# ---------------------------------------------------------------------------
# _msg_to_schema
# ---------------------------------------------------------------------------

class TestMsgToSchema:
    """Tests for _msg_to_schema conversion."""

    def test_converts_all_fields(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            tool_calls = [{"name": "f", "args": {}}]
            tool_results = [{"output": "ok"}]
            msg = svc.append_message(
                db, aeroplane.uuid,
                _make_msg_write(
                    role="assistant",
                    content="text",
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                    parent_id=None,
                ),
            )
            assert msg.role == "assistant"
            assert msg.content == "text"
            assert msg.tool_calls == tool_calls
            assert msg.tool_results == tool_results
            assert msg.parent_id is None
