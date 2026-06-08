"""Tests for POST /aeroplanes/{id}/copilot/stream SSE endpoint (gh-918).

The LiteLLM hub is NEVER called.  ``copilot_service.run_turn`` is replaced
with a scripted async generator that emits a predefined event sequence.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator
from unittest.mock import patch, AsyncMock

import pytest

from app.services import copilot_history_service as hist_svc
from app.schemas.copilot_history import CopilotMessageWrite
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# SSE parsing helper
# ---------------------------------------------------------------------------


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    """Parse a raw SSE response body into a list of (event_type, data) tuples."""
    result = []
    current_event = None
    current_data = None

    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            raw_data = line[len("data:"):].strip()
            try:
                current_data = json.loads(raw_data)
            except json.JSONDecodeError:
                current_data = {"raw": raw_data}
        elif line == "" and current_event is not None:
            result.append((current_event, current_data or {}))
            current_event = None
            current_data = None

    return result


# ---------------------------------------------------------------------------
# Fake run_turn generators
# ---------------------------------------------------------------------------


async def _gen_token_tool_done(*_, **__) -> AsyncGenerator[dict, None]:
    """Scripted sequence: one token → one tool_call → one tool_result → done."""
    yield {"type": "token", "text": "Here is your design."}
    yield {"type": "tool_call", "name": "get_design_snapshot", "args": {}}
    yield {"type": "tool_result", "name": "get_design_snapshot", "summary": {"span": 1.5}}
    yield {
        "type": "done",
        "final_text": "Here is your design.",
        "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "get_design_snapshot", "arguments": "{}"}}],
        "tool_results": [{"tool_call_id": "c1", "name": "get_design_snapshot", "result": {"span": 1.5}}],
    }


async def _gen_error(*_, **__) -> AsyncGenerator[dict, None]:
    """Scripted sequence: error event."""
    yield {"type": "error", "message": "Hub unreachable"}


async def _gen_text_only(*_, **__) -> AsyncGenerator[dict, None]:
    """Simple text-only response."""
    yield {"type": "token", "text": "Hello!"}
    yield {"type": "done", "final_text": "Hello!", "tool_calls": [], "tool_results": []}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCopilotStreamEndpoint:
    """Integration tests for POST /aeroplanes/{id}/copilot/stream."""

    def test_returns_200_with_event_stream_content_type(self, client_and_db):
        client, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        with patch("app.services.copilot_service.run_turn", new=_gen_text_only):
            resp = client.post(
                f"/aeroplanes/{aeroplane.uuid}/copilot/stream",
                json={"message": "What is my CL max?"},
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_sse_events_include_token_and_done(self, client_and_db):
        client, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        with patch("app.services.copilot_service.run_turn", new=_gen_text_only):
            resp = client.post(
                f"/aeroplanes/{aeroplane.uuid}/copilot/stream",
                json={"message": "hello"},
            )

        events = _parse_sse(resp.text)
        event_types = [e[0] for e in events]

        assert "token" in event_types
        assert "done" in event_types

    def test_sse_events_include_tool_call_and_tool_result(self, client_and_db):
        client, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        with patch("app.services.copilot_service.run_turn", new=_gen_token_tool_done):
            resp = client.post(
                f"/aeroplanes/{aeroplane.uuid}/copilot/stream",
                json={"message": "Analyse my design"},
            )

        events = _parse_sse(resp.text)
        event_types = [e[0] for e in events]

        assert "tool_call" in event_types
        assert "tool_result" in event_types
        assert "done" in event_types

    def test_history_has_user_and_assistant_messages_after_stream(self, client_and_db):
        client, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            aeroplane_uuid = aeroplane.uuid

        with patch("app.services.copilot_service.run_turn", new=_gen_text_only):
            client.post(
                f"/aeroplanes/{aeroplane_uuid}/copilot/stream",
                json={"message": "What is my wing area?"},
            )

        # Verify history was persisted
        with SessionLocal() as db:
            history = hist_svc.get_history(db, aeroplane_uuid)

        assert len(history.messages) == 2
        assert history.messages[0].role == "user"
        assert history.messages[0].content == "What is my wing area?"
        assert history.messages[1].role == "assistant"
        assert history.messages[1].content == "Hello!"

    def test_assistant_message_persists_tool_calls_and_results(self, client_and_db):
        client, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            aeroplane_uuid = aeroplane.uuid

        with patch("app.services.copilot_service.run_turn", new=_gen_token_tool_done):
            client.post(
                f"/aeroplanes/{aeroplane_uuid}/copilot/stream",
                json={"message": "Show me the snapshot"},
            )

        with SessionLocal() as db:
            history = hist_svc.get_history(db, aeroplane_uuid)

        assistant_msg = next(m for m in history.messages if m.role == "assistant")
        assert assistant_msg.tool_calls is not None
        assert len(assistant_msg.tool_calls) == 1
        assert assistant_msg.tool_results is not None
        assert len(assistant_msg.tool_results) == 1

    def test_error_event_in_sse_stream(self, client_and_db):
        client, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        with patch("app.services.copilot_service.run_turn", new=_gen_error):
            resp = client.post(
                f"/aeroplanes/{aeroplane.uuid}/copilot/stream",
                json={"message": "test"},
            )

        events = _parse_sse(resp.text)
        event_types = [e[0] for e in events]
        assert "error" in event_types

        error_data = next(d for t, d in events if t == "error")
        assert "message" in error_data

    def test_returns_404_for_unknown_aeroplane(self, client_and_db):
        client, _ = client_and_db

        import uuid

        with patch("app.services.copilot_service.run_turn", new=_gen_text_only):
            resp = client.post(
                f"/aeroplanes/{uuid.uuid4()}/copilot/stream",
                json={"message": "test"},
            )

        assert resp.status_code == 404

    def test_returns_422_for_missing_message_body(self, client_and_db):
        client, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        resp = client.post(
            f"/aeroplanes/{aeroplane.uuid}/copilot/stream",
            json={},  # missing required "message"
        )

        assert resp.status_code == 422

    def test_token_text_matches_generated_content(self, client_and_db):
        client, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        with patch("app.services.copilot_service.run_turn", new=_gen_text_only):
            resp = client.post(
                f"/aeroplanes/{aeroplane.uuid}/copilot/stream",
                json={"message": "hello"},
            )

        events = _parse_sse(resp.text)
        token_events = [(t, d) for t, d in events if t == "token"]
        assert len(token_events) == 1
        assert token_events[0][1]["text"] == "Hello!"

    def test_context_hint_accepted(self, client_and_db):
        """context_hint field is accepted without error."""
        client, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        with patch("app.services.copilot_service.run_turn", new=_gen_text_only):
            resp = client.post(
                f"/aeroplanes/{aeroplane.uuid}/copilot/stream",
                json={"message": "hello", "context_hint": "Wing Editor · MyGlider"},
            )

        assert resp.status_code == 200
