"""Tests for app.services.copilot_service — tool-calling loop (gh-918).

The LiteLLM hub is NEVER called in these tests.  ``_make_openai_client``
is monkeypatched to return a scripted fake client whose
``chat.completions.create`` returns pre-built async streams.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.copilot_service as svc_module
import app.services.copilot_tools as tools_module
from app.schemas.copilot_history import CopilotHistory, CopilotMessageRead
from app.services.copilot_service import MAX_LOOP_ITERATIONS, _sanitize_error, run_turn
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# Fake stream helpers
# ---------------------------------------------------------------------------


def _make_chunk(content: str | None = None, tool_calls=None, finish_reason: str | None = None):
    """Build a minimal streaming chunk object."""
    delta = MagicMock()
    delta.content = content
    delta.tool_calls = tool_calls or []

    choice = MagicMock()
    choice.delta = delta
    choice.finish_reason = finish_reason

    chunk = MagicMock()
    chunk.choices = [choice]
    return chunk


def _make_tool_call_chunk(index: int, call_id: str, name: str, args: str):
    """Build a tool-call delta chunk."""
    func = MagicMock()
    func.name = name
    func.arguments = args

    tc = MagicMock()
    tc.index = index
    tc.id = call_id
    tc.function = func

    return _make_chunk(tool_calls=[tc], finish_reason="tool_calls")


async def _async_iter(items):
    """Yield items from a list as an async iterator."""
    for item in items:
        yield item


class FakeStream:
    """An async context manager that yields chunks."""

    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        return _async_iter(self._chunks).__aiter__()


def _fake_client_for_text(text: str):
    """A fake client whose single stream yields a text response then stops."""
    chunks = [
        _make_chunk(content=text[:5]),
        _make_chunk(content=text[5:]),
        _make_chunk(finish_reason="stop"),
    ]

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=FakeStream(chunks))
    return client


def _fake_client_with_one_tool_call(
    tool_name: str,
    tool_args: dict,
    call_id: str,
    final_text: str,
):
    """A fake client that: first yields a tool_call, then yields text + stop."""
    args_str = json.dumps(tool_args)

    # First stream: one tool-call chunk + finish_reason=tool_calls
    tc_chunk = _make_tool_call_chunk(0, call_id, tool_name, args_str)
    first_stream = FakeStream([tc_chunk])

    # Second stream: text reply + stop
    second_chunks = [
        _make_chunk(content=final_text),
        _make_chunk(finish_reason="stop"),
    ]
    second_stream = FakeStream(second_chunks)

    call_count = [0]

    async def _create(**_kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return first_stream
        return second_stream

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = _create
    return client


def _build_history(messages=None) -> CopilotHistory:
    """Build a minimal CopilotHistory for testing."""
    from datetime import datetime, timezone

    msgs = []
    for i, (role, content) in enumerate(messages or [("user", "hello")]):
        msgs.append(
            CopilotMessageRead(
                id=i + 1,
                role=role,
                content=content,
                tool_calls=None,
                tool_results=None,
                parent_id=None,
                created_at=datetime.now(timezone.utc),
            )
        )
    return CopilotHistory(messages=msgs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _collect_events(gen: AsyncGenerator) -> list[dict]:
    events = []
    async for ev in gen:
        events.append(ev)
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunTurnTextOnly:
    """A plain text response with no tool calls."""

    def test_yields_tokens_and_done(self, client_and_db):
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history([("user", "What is the static margin?")])

            fake_client = _fake_client_for_text("Hello world")

            with patch.object(svc_module, "_make_openai_client", return_value=fake_client):
                import asyncio

                events = asyncio.run(
                    _collect_events(
                        run_turn(
                            db=db,
                            aeroplane_id=aeroplane.id,
                            history=history,
                            context_hint="Wing Editor",
                        )
                    )
                )

            types = [e["type"] for e in events]
            assert "token" in types
            assert types[-1] == "done"

            # Verify text is assembled correctly
            token_text = "".join(e["text"] for e in events if e["type"] == "token")
            assert "Hello world" == token_text

    def test_done_event_has_final_text(self, client_and_db):
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history()

            fake_client = _fake_client_for_text("test response")

            with patch.object(svc_module, "_make_openai_client", return_value=fake_client):
                import asyncio

                events = asyncio.run(
                    _collect_events(
                        run_turn(
                            db=db,
                            aeroplane_id=aeroplane.id,
                            history=history,
                        )
                    )
                )

            done_event = next(e for e in events if e["type"] == "done")
            assert done_event["final_text"] == "test response"


class TestRunTurnWithToolCall:
    """One tool call followed by a text response."""

    def test_yields_tool_call_tool_result_token_done(self, client_and_db):
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history([("user", "What is my design like?")])

            fake_client = _fake_client_with_one_tool_call(
                tool_name="get_design_snapshot",
                tool_args={},
                call_id="call_abc123",
                final_text="Here is your design summary.",
            )

            # Stub out the actual tool execution (no real DB queries needed)
            stub_result = {"span_m": 1.5, "mass_kg": 1.2}
            with patch.object(svc_module, "_make_openai_client", return_value=fake_client):
                with patch(
                    "app.services.copilot_tools.execute", return_value=stub_result
                ) as mock_execute:
                    import asyncio

                    events = asyncio.run(
                        _collect_events(
                            run_turn(
                                db=db,
                                aeroplane_id=aeroplane.id,
                                history=history,
                            )
                        )
                    )

            types = [e["type"] for e in events]
            assert "tool_call" in types
            assert "tool_result" in types
            assert "token" in types
            assert types[-1] == "done"

            # Verify tool was called with correct name and args
            mock_execute.assert_called_once_with(
                "get_design_snapshot", db, aeroplane.id
            )

    def test_tool_call_event_has_name_and_args(self, client_and_db):
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history()

            fake_client = _fake_client_with_one_tool_call(
                tool_name="run_analysis",
                tool_args={"kind": "polar"},
                call_id="call_xyz",
                final_text="Analysis complete.",
            )

            with patch.object(svc_module, "_make_openai_client", return_value=fake_client):
                with patch("app.services.copilot_tools.execute", return_value={"status": "ok"}):
                    import asyncio

                    events = asyncio.run(
                        _collect_events(
                            run_turn(db=db, aeroplane_id=aeroplane.id, history=history)
                        )
                    )

            tc_event = next(e for e in events if e["type"] == "tool_call")
            assert tc_event["name"] == "run_analysis"
            assert tc_event["args"] == {"kind": "polar"}

    def test_tool_result_event_has_summary(self, client_and_db):
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history()

            fake_client = _fake_client_with_one_tool_call(
                tool_name="get_design_snapshot",
                tool_args={},
                call_id="call_r1",
                final_text="Done.",
            )
            stub_result = {"mass_kg": 1.5}

            with patch.object(svc_module, "_make_openai_client", return_value=fake_client):
                with patch("app.services.copilot_tools.execute", return_value=stub_result):
                    import asyncio

                    events = asyncio.run(
                        _collect_events(
                            run_turn(db=db, aeroplane_id=aeroplane.id, history=history)
                        )
                    )

            tr_event = next(e for e in events if e["type"] == "tool_result")
            assert tr_event["name"] == "get_design_snapshot"
            assert tr_event["summary"] == stub_result

    def test_done_accumulates_tool_calls_and_results(self, client_and_db):
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history()

            fake_client = _fake_client_with_one_tool_call(
                tool_name="get_version_tree",
                tool_args={},
                call_id="call_v1",
                final_text="Version info provided.",
            )

            with patch.object(svc_module, "_make_openai_client", return_value=fake_client):
                with patch(
                    "app.services.copilot_tools.execute", return_value={"nodes": []}
                ):
                    import asyncio

                    events = asyncio.run(
                        _collect_events(
                            run_turn(db=db, aeroplane_id=aeroplane.id, history=history)
                        )
                    )

            done_event = next(e for e in events if e["type"] == "done")
            assert len(done_event["tool_calls"]) == 1
            assert len(done_event["tool_results"]) == 1
            assert done_event["tool_calls"][0]["function"]["name"] == "get_version_tree"


class TestMaxIterationsGuard:
    """The loop must stop after MAX_LOOP_ITERATIONS even if the model keeps requesting tools."""

    def test_guard_prevents_infinite_loop(self, client_and_db):
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history()

            # Every call returns another tool_call (never stops)
            call_count = [0]

            async def _always_tool_call(**_kwargs):
                call_count[0] += 1
                tc_chunk = _make_tool_call_chunk(
                    0, f"call_{call_count[0]}", "get_design_snapshot", "{}"
                )
                return FakeStream([tc_chunk])

            client = MagicMock()
            client.chat = MagicMock()
            client.chat.completions = MagicMock()
            client.chat.completions.create = _always_tool_call

            with patch.object(svc_module, "_make_openai_client", return_value=client):
                with patch(
                    "app.services.copilot_tools.execute", return_value={"data": "ok"}
                ):
                    import asyncio

                    events = asyncio.run(
                        _collect_events(
                            run_turn(db=db, aeroplane_id=aeroplane.id, history=history)
                        )
                    )

            # Should have stopped after MAX_LOOP_ITERATIONS completions
            assert call_count[0] <= MAX_LOOP_ITERATIONS
            # Last event should be done (not an error)
            assert events[-1]["type"] == "done"


class TestHubError:
    """If the hub raises, an error event is emitted."""

    def test_hub_error_yields_error_event(self, client_and_db):
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history()

            client = MagicMock()
            client.chat = MagicMock()
            client.chat.completions = MagicMock()
            client.chat.completions.create = AsyncMock(
                side_effect=RuntimeError("connection refused")
            )

            with patch.object(svc_module, "_make_openai_client", return_value=client):
                import asyncio

                events = asyncio.run(
                    _collect_events(
                        run_turn(db=db, aeroplane_id=aeroplane.id, history=history)
                    )
                )

            assert events[0]["type"] == "error"
            # The sanitizer replaces raw connection details with a category message.
            assert "error" in events[0]["message"].lower()

    def test_hub_error_does_not_leak_api_key(self, client_and_db):
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history()

            client = MagicMock()
            client.chat = MagicMock()
            client.chat.completions = MagicMock()
            client.chat.completions.create = AsyncMock(
                side_effect=RuntimeError("auth failed: key=sk-secret-key-value")
            )

            # The error message is emitted as-is from the exception, but
            # the endpoint layer never leaks it as an HTTP body.
            # The sanitizer must redact the key — this test now asserts absence.
            with patch.object(svc_module, "_make_openai_client", return_value=client):
                import app.core.config as cfg_mod
                from pydantic import SecretStr

                original_key = cfg_mod.settings.COPILOT_API_KEY
                cfg_mod.settings.COPILOT_API_KEY = SecretStr("sk-secret-key-value")
                try:
                    events = asyncio.run(
                        _collect_events(
                            run_turn(db=db, aeroplane_id=aeroplane.id, history=history)
                        )
                    )
                finally:
                    cfg_mod.settings.COPILOT_API_KEY = original_key

            assert events[0]["type"] == "error"
            # The raw key must NOT appear in any event
            all_event_text = json.dumps(events)
            assert "sk-secret-key-value" not in all_event_text, (
                f"API key leaked in events: {all_event_text}"
            )


# ---------------------------------------------------------------------------
# Blocker 1 — event-loop safety: run_analysis via asyncio.to_thread
# ---------------------------------------------------------------------------


class TestRunAnalysisViaToThread:
    """The critical regression guard for gh-902 Blocker 1.

    ``run_turn`` is an async generator that runs on the uvicorn event loop.
    It must dispatch ``copilot_tools.execute`` (and therefore ``_run_analysis``)
    to a worker thread via ``asyncio.to_thread`` so that the worker can call
    ``asyncio.run()`` without raising
    "RuntimeError: This event loop is already running".

    This test exercises the REAL ``copilot_tools.execute`` → ``_run_analysis``
    code path (NOT mocked) on a live event loop.  Only ``_run_polar_async`` is
    stubbed to avoid real aero computation in CI.
    """

    def test_run_analysis_does_not_raise_on_live_event_loop(self, client_and_db):
        """Drives run_turn end-to-end on a live loop with a real execute call."""
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history([("user", "What is the polar?")])

            # Hub client: first call returns run_analysis tool call, second
            # returns a text stop — the hub never makes a real network call.
            fake_client = _fake_client_with_one_tool_call(
                tool_name="run_analysis",
                tool_args={"kind": "polar"},
                call_id="call_event_loop_test",
                final_text="Polar analysed.",
            )

            # Stub the expensive async polar computation to return immediately.
            # We do NOT stub copilot_tools.execute — the real dispatch path must run.
            async def _instant_polar(db, aeroplane_uuid):
                return {
                    "status": "ok",
                    "kind": "polar",
                    "cl_max": 1.2,
                    "cd_min": 0.03,
                    "cl_cd_max": 15.0,
                }

            with patch.object(svc_module, "_make_openai_client", return_value=fake_client):
                with patch.object(tools_module, "_run_polar_async", _instant_polar):
                    # Run on a live event loop — this is what raises if the
                    # asyncio.new_event_loop().run_until_complete() bug exists.
                    events = asyncio.run(
                        _collect_events(
                            run_turn(
                                db=db,
                                aeroplane_id=aeroplane.id,
                                history=history,
                            )
                        )
                    )

            # Must NOT have raised RuntimeError — if it did, the run_until_complete
            # above would have propagated it.
            types = [e["type"] for e in events]
            # The tool call was dispatched and a result was produced.
            assert "tool_call" in types, "Expected tool_call event"
            assert "tool_result" in types, "Expected tool_result event — real execute() must run"
            assert types[-1] == "done"

            # The tool result must contain real polar data (not a stub from
            # patch("copilot_tools.execute")), proving the real path ran.
            tr = next(e for e in events if e["type"] == "tool_result")
            assert tr["name"] == "run_analysis"
            assert tr["summary"].get("status") == "ok", (
                f"Expected ok polar result, got: {tr['summary']}"
            )

    def test_run_analysis_tool_execute_does_not_raise_when_called_from_running_loop(
        self, client_and_db
    ):
        """Direct sanity check: execute() in a worker thread from a running loop.

        Previously _run_analysis called asyncio.new_event_loop().run_until_complete()
        which raises RuntimeError if a loop is already running.  The fix runs
        execute() in a worker thread (no running loop there) and _run_analysis
        calls asyncio.run() which is always safe in that context.

        This test simulates the same isolation by calling execute() via
        asyncio.to_thread from within a coroutine running on a live loop.
        """
        _, SessionLocal = client_and_db

        async def _run():
            with SessionLocal() as db:
                plane = make_aeroplane(db)

                async def _instant_polar(db, aeroplane_uuid):
                    return {"status": "ok", "kind": "polar", "cl_max": 1.1}

                with patch.object(tools_module, "_run_polar_async", _instant_polar):
                    # This is the exact pattern run_turn now uses.
                    result = await asyncio.to_thread(
                        tools_module.execute, "run_analysis", db, plane.id, kind="polar"
                    )
            return result

        result = asyncio.run(_run())
        # Must not raise; must return the mocked polar result
        assert result.get("status") == "ok"
        assert result.get("kind") == "polar"


# ---------------------------------------------------------------------------
# API key must never appear in SSE events
# ---------------------------------------------------------------------------


class TestApiKeyNotLeakedInSseEvents:
    """The configured COPILOT_API_KEY must never appear in any SSE event."""

    def test_hub_error_with_key_in_exc_does_not_leak_key(self, client_and_db):
        """An auth exception whose text contains the API key must be redacted."""
        _, SessionLocal = client_and_db

        fake_key = "sk-super-secret-test-key-12345"

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history()

            client = MagicMock()
            client.chat = MagicMock()
            client.chat.completions = MagicMock()
            # Exception message literally embeds the key — simulates what OpenAI
            # SDK does when reporting auth failures.
            client.chat.completions.create = AsyncMock(
                side_effect=RuntimeError(
                    f"Authentication failed: api_key={fake_key} is invalid"
                )
            )

            import app.core.config as cfg_mod
            from pydantic import SecretStr

            original_key = cfg_mod.settings.COPILOT_API_KEY
            cfg_mod.settings.COPILOT_API_KEY = SecretStr(fake_key)
            try:
                with patch.object(svc_module, "_make_openai_client", return_value=client):
                    events = asyncio.run(
                        _collect_events(
                            run_turn(db=db, aeroplane_id=aeroplane.id, history=history)
                        )
                    )
            finally:
                cfg_mod.settings.COPILOT_API_KEY = original_key

        # The raw key must NOT appear anywhere in any event.
        all_event_text = json.dumps(events)
        assert fake_key not in all_event_text, (
            f"API key leaked in SSE events: {all_event_text}"
        )
        assert events[0]["type"] == "error"

    def test_stream_error_with_key_in_exc_does_not_leak_key(self, client_and_db):
        """A streaming exception whose text contains the API key must be redacted."""
        _, SessionLocal = client_and_db

        fake_key = "sk-another-secret-key-99999"

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history()

            async def _bad_stream():
                raise RuntimeError(f"Stream broken: bearer={fake_key}")
                yield  # makes this an async generator (unreachable but required)

            class _ErrStream:
                def __aiter__(self):
                    return _bad_stream().__aiter__()

            client = MagicMock()
            client.chat = MagicMock()
            client.chat.completions = MagicMock()
            client.chat.completions.create = AsyncMock(return_value=_ErrStream())

            import app.core.config as cfg_mod
            from pydantic import SecretStr

            original_key = cfg_mod.settings.COPILOT_API_KEY
            cfg_mod.settings.COPILOT_API_KEY = SecretStr(fake_key)
            try:
                with patch.object(svc_module, "_make_openai_client", return_value=client):
                    events = asyncio.run(
                        _collect_events(
                            run_turn(db=db, aeroplane_id=aeroplane.id, history=history)
                        )
                    )
            finally:
                cfg_mod.settings.COPILOT_API_KEY = original_key

        all_event_text = json.dumps(events)
        assert fake_key not in all_event_text, (
            f"API key leaked in SSE stream-error events: {all_event_text}"
        )
        assert events[0]["type"] == "error"


# ---------------------------------------------------------------------------
# Truncated flag on MAX_LOOP_ITERATIONS
# ---------------------------------------------------------------------------


class TestTruncatedFlag:
    """done event must carry truncated=True when the loop hit MAX_LOOP_ITERATIONS."""

    def test_done_has_truncated_true_on_loop_exhaustion(self, client_and_db):
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history()

            # Every hub response is another tool_call — never stops naturally.
            call_count = [0]

            async def _always_tool_call(**_kwargs):
                call_count[0] += 1
                tc_chunk = _make_tool_call_chunk(
                    0, f"call_{call_count[0]}", "get_design_snapshot", "{}"
                )
                return FakeStream([tc_chunk])

            client = MagicMock()
            client.chat = MagicMock()
            client.chat.completions = MagicMock()
            client.chat.completions.create = _always_tool_call

            with patch.object(svc_module, "_make_openai_client", return_value=client):
                with patch(
                    "app.services.copilot_tools.execute", return_value={"data": "ok"}
                ):
                    events = asyncio.run(
                        _collect_events(
                            run_turn(db=db, aeroplane_id=aeroplane.id, history=history)
                        )
                    )

        done_event = next(e for e in events if e["type"] == "done")
        assert done_event.get("truncated") is True, (
            f"Expected truncated=True in done event, got: {done_event}"
        )

    def test_done_has_no_truncated_key_on_clean_stop(self, client_and_db):
        """When the model stops naturally, truncated must NOT be in the done event."""
        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            history = _build_history()

            fake_client = _fake_client_for_text("All done cleanly.")

            with patch.object(svc_module, "_make_openai_client", return_value=fake_client):
                events = asyncio.run(
                    _collect_events(
                        run_turn(db=db, aeroplane_id=aeroplane.id, history=history)
                    )
                )

        done_event = next(e for e in events if e["type"] == "done")
        assert "truncated" not in done_event, (
            f"truncated key should not be present on clean stop, got: {done_event}"
        )


# ---------------------------------------------------------------------------
# _sanitize_error unit tests
# ---------------------------------------------------------------------------


class TestSanitizeError:
    """Unit tests for the _sanitize_error helper."""

    def test_redacts_key_in_raw_message(self):
        import app.core.config as cfg_mod
        from pydantic import SecretStr

        fake_key = "sk-unit-test-key-xyz"
        original = cfg_mod.settings.COPILOT_API_KEY
        cfg_mod.settings.COPILOT_API_KEY = SecretStr(fake_key)
        try:
            exc = RuntimeError(f"request failed api_key={fake_key}")
            result = _sanitize_error(exc)
        finally:
            cfg_mod.settings.COPILOT_API_KEY = original

        assert fake_key not in result

    def test_connection_errors_become_generic(self):
        exc = RuntimeError("Connection refused to 10.0.0.1:8080")
        result = _sanitize_error(exc)
        assert "10.0.0.1" not in result
        assert "connection" in result.lower() or "error" in result.lower()

    def test_auth_errors_become_generic(self):
        exc = ValueError("Invalid api_key provided: sk-abc123")
        result = _sanitize_error(exc)
        assert "sk-abc123" not in result

    def test_benign_error_preserved(self):
        exc = RuntimeError("division by zero")
        result = _sanitize_error(exc)
        # Not a key/connection error — message should pass through (redacted form)
        assert "division by zero" in result
