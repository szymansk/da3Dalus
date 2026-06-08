"""Copilot service — tool-calling loop that drives the AI agent (gh-918).

The public surface is a single async generator ``run_turn`` that:

1. Builds the messages list (system prompt + history).
2. Calls the OpenAI-compatible LiteLLM hub using the ``openai`` SDK with
   streaming enabled.
3. Yields ``dict`` events that the SSE endpoint formats and sends to the
   browser:

   * ``{"type": "token", "text": "…"}``      — assistant text delta
   * ``{"type": "tool_call", "name": "…", "args": {…}}``  — model wants to call a tool
   * ``{"type": "tool_result", "name": "…", "summary": {…}}``  — server-side result

4. Executes tool calls server-side via ``copilot_tools.execute``, appends
   the results to the conversation, and continues the loop.
5. Stops after at most ``MAX_LOOP_ITERATIONS`` exchanges (guard against
   runaway tool loops).

Hub client injection
--------------------
The OpenAI client is built by the module-level factory ``_make_openai_client``.
Tests monkeypatch ``app.services.copilot_service._make_openai_client`` to
inject a fake client — **no real API call is ever made in CI**.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SSE error sanitization
# ---------------------------------------------------------------------------


def _sanitize_error(exc: BaseException) -> str:
    """Return a safe error message that never exposes the configured API key.

    Any occurrence of the raw COPILOT_API_KEY value in ``str(exc)`` is
    replaced with the placeholder ``"[REDACTED]"``.  Additionally the raw
    exception text is replaced with a category message so that transient
    auth / network details are not forwarded to the browser.
    """
    try:
        from app.core.config import settings

        secret = settings.COPILOT_API_KEY
        key_value = secret.get_secret_value() if secret else None
    except Exception:  # noqa: BLE001
        key_value = None

    # Build a human-friendly category string from the exception type.
    exc_type = type(exc).__name__
    raw = str(exc)

    # Redact the key before doing anything else.
    if key_value and key_value in raw:
        raw = raw.replace(key_value, "[REDACTED]")

    # For authentication/connection errors substitute a generic message so
    # internal details (URLs, tokens) are not forwarded to the browser.
    lower = raw.lower()
    if any(kw in lower for kw in ("auth", "key", "token", "api_key", "secret", "credential")):
        return f"{exc_type}: authentication or configuration error"
    if any(kw in lower for kw in ("connect", "timeout", "network", "refused", "unreachable")):
        return f"{exc_type}: hub connection error"

    # Generic fallback — include redacted message.
    return f"{exc_type}: {raw}"

# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

MAX_LOOP_ITERATIONS: int = 6

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are da3Dalus, an AI aircraft-design copilot integrated into the
da3Dalus workbench. You serve both hobbyists (RC / model aircraft, FPV)
and professional engineers (UAV, light aircraft).

## Role
Advisory-only (Slice 1). You help users understand and improve their design
by answering questions, running analyses, and interpreting results. You do
NOT change the design directly; if asked, say "Design changes are coming
in a future update — for now I can show you the numbers and explain what
to adjust."

## Anti-hallucination rules (HARD)
1. NEVER invent numbers. Always retrieve real values via the tools.
2. Before quoting any figure (mass, span, CL, static margin, …) call
   get_design_snapshot or run_analysis. If a tool returns an error or
   timeout, say so explicitly.
3. When you cite a number, state which tool produced it.
4. If you are unsure, say so; do not guess.

## Provisional knowledge (until RAG is available)
Use the following as approximate guidance only — the user's actual design
numbers from the tools take precedence.

### Static margin targets (% MAC)
- RC trainer / beginner: 15–25 %
- RC sport / intermediate: 8–15 %
- RC aerobatic / advanced: 0–8 % (neutrally stable)
- UAV / autonomous: 5–15 % (depends on autopilot authority)
- Light GA (Scholz/Sadraey): 5–15 %

### Horizontal tail volume coefficient V_H
- Light GA / trainer: 0.30–0.50
- RC trainer: 0.35–0.55
- RC sport: 0.25–0.40
- Flying wing: not applicable (elevon authority)

### Lift-to-drag benchmarks
- RC trainer: L/D 8–12
- RC glider / thermal soarer: L/D 20–35
- RC sport: L/D 10–15
- Small UAV (fixed-wing): L/D 12–20

### Sizing methodology (Scholz / Sadraey)
For preliminary sizing use: T/W vs W/S matching chart, Breguet endurance
equation, and constraint analysis. These are analytical starting points;
refine with the polar tool.

### First-flight CG (RC models only)
Set CG to the aft edge of the safe forward CG range (typically 25–30 % MAC
for trainers). Verify with a slow glide test at safe altitude.

## Language
Reply in the same language the user writes in (German if they write in
German, English otherwise). UI chrome and code comments are always English.

## Context hint (injected per turn)
{context_hint}
"""


# ---------------------------------------------------------------------------
# OpenAI client factory — monkeypatched in tests
# ---------------------------------------------------------------------------


def _make_openai_client():  # pragma: no cover — tested via monkeypatch
    """Build an OpenAI-compatible client from config.

    Returns an ``openai.AsyncOpenAI`` (or compatible) instance configured
    to talk to the LiteLLM hub.  Tests replace this function to inject a
    fake client.
    """
    from openai import AsyncOpenAI

    from app.core.config import settings

    kwargs: dict[str, Any] = {}
    if settings.COPILOT_BASE_URL:
        kwargs["base_url"] = settings.COPILOT_BASE_URL
    if settings.COPILOT_API_KEY:
        kwargs["api_key"] = settings.COPILOT_API_KEY.get_secret_value()
    else:
        # AsyncOpenAI requires an api_key; use a placeholder so the import
        # succeeds even without a real key.  Actual calls will fail gracefully
        # and the error is surfaced as an SSE error event.
        kwargs["api_key"] = "no-key"

    return AsyncOpenAI(**kwargs)


# ---------------------------------------------------------------------------
# Helper — convert CopilotMessageRead → OpenAI message dict
# ---------------------------------------------------------------------------


def _history_to_openai(messages) -> list[dict[str, Any]]:
    """Convert a list of CopilotMessageRead to OpenAI chat message dicts."""
    result: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "user":
            result.append({"role": "user", "content": m.content or ""})
        elif m.role == "assistant":
            msg: dict[str, Any] = {"role": "assistant", "content": m.content or ""}
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            result.append(msg)
            # Anthropic's strict tool protocol (and OpenAI's) requires every
            # assistant ``tool_use``/``tool_call`` to be immediately followed by
            # a matching ``tool`` result message. We persist the turn as a single
            # assistant row carrying both tool_calls and tool_results (no separate
            # ``tool`` rows), so reconstruct the result messages here — otherwise
            # the replayed history has an orphaned tool_use and the hub 400s on
            # every turn after the first tool use (gh-922).
            if m.tool_calls:
                results_by_id = {
                    tr.get("tool_call_id", ""): tr for tr in (m.tool_results or [])
                }
                for tc in m.tool_calls:
                    tc_id = tc.get("id", "")
                    tr = results_by_id.get(tc_id)
                    content = (
                        json.dumps(tr.get("result", tr))
                        if tr is not None
                        else json.dumps({"error": "tool result unavailable"})
                    )
                    result.append(
                        {"role": "tool", "tool_call_id": tc_id, "content": content}
                    )
        elif m.role == "tool":
            # Tool result messages: one message per tool result
            if m.tool_results:
                for tr in m.tool_results:
                    result.append(
                        {
                            "role": "tool",
                            "tool_call_id": tr.get("tool_call_id", ""),
                            "content": json.dumps(tr.get("result", tr)),
                        }
                    )
            else:
                result.append({"role": "tool", "content": m.content or "", "tool_call_id": ""})
    return result


# ---------------------------------------------------------------------------
# run_turn — async generator
# ---------------------------------------------------------------------------


async def run_turn(
    *,
    db: Session,
    aeroplane_id: int,
    history,
    context_hint: str = "",
) -> AsyncGenerator[dict[str, Any], None]:
    """Run one copilot turn as an async generator of SSE-ready events.

    Parameters
    ----------
    db:
        SQLAlchemy session (caller-owned, no commit inside this function).
    aeroplane_id:
        Integer PK of the aeroplane (used for tool execution).
    history:
        CopilotHistory from ``copilot_history_service.get_history``.
        The latest message is the user turn just appended.
    context_hint:
        Short string injected into the system prompt (e.g. "Active tab:
        Wing Editor · Aircraft: MyGlider").

    Yields
    ------
    dict
        SSE-ready event dicts:
        ``{"type": "token", "text": "…"}``
        ``{"type": "tool_call", "name": "…", "args": {…}}``
        ``{"type": "tool_result", "name": "…", "summary": {…}}``
        ``{"type": "done"}``
        ``{"type": "error", "message": "…"}``
    """
    from app.services import copilot_tools

    from app.core.config import settings

    system_content = SYSTEM_PROMPT.format(context_hint=context_hint or "(no context)")

    # Build initial messages list
    openai_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_content},
        *_history_to_openai(history.messages),
    ]

    tool_schemas = copilot_tools.list_schemas()

    # Accumulate tool calls and results for final persistence
    accumulated_tool_calls: list[dict[str, Any]] = []
    accumulated_tool_results: list[dict[str, Any]] = []

    # The final text the assistant produced (used for persistence)
    final_text = ""

    # Set to True when the loop exits via a clean finish_reason="stop"; stays
    # False if we ran out of MAX_LOOP_ITERATIONS while the model was still
    # requesting tool calls (truncated turn).
    turn_complete = False

    client = _make_openai_client()

    for iteration in range(MAX_LOOP_ITERATIONS):
        # ---- stream one completion ----------------------------------------
        try:
            stream = await client.chat.completions.create(
                model=settings.COPILOT_MODEL,
                messages=openai_messages,
                tools=tool_schemas,
                tool_choice="auto",
                stream=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Hub call failed on iteration %d", iteration)
            yield {"type": "error", "message": f"Hub error: {_sanitize_error(exc)}"}
            return

        # Collect the streamed response
        text_delta = ""
        tool_call_chunks: dict[int, dict[str, Any]] = {}  # index → accumulated chunk
        finish_reason: str | None = None

        try:
            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if choice is None:
                    continue

                finish_reason = choice.finish_reason or finish_reason
                delta = choice.delta

                # Text token
                if delta.content:
                    text_delta += delta.content
                    yield {"type": "token", "text": delta.content}

                # Tool call chunk accumulation
                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        idx = tc_chunk.index
                        if idx not in tool_call_chunks:
                            tool_call_chunks[idx] = {
                                "id": tc_chunk.id or "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc_chunk.id:
                            tool_call_chunks[idx]["id"] = tc_chunk.id
                        if tc_chunk.function:
                            if tc_chunk.function.name:
                                tool_call_chunks[idx]["function"]["name"] += (
                                    tc_chunk.function.name
                                )
                            if tc_chunk.function.arguments:
                                tool_call_chunks[idx]["function"]["arguments"] += (
                                    tc_chunk.function.arguments
                                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Stream read failed on iteration %d", iteration)
            yield {"type": "error", "message": f"Stream error: {_sanitize_error(exc)}"}
            return

        if text_delta:
            final_text += text_delta

        # ---- handle finish_reason ----------------------------------------

        if finish_reason == "stop" or (not tool_call_chunks and finish_reason != "tool_calls"):
            # Normal text completion — we're done
            turn_complete = True
            break

        if not tool_call_chunks:
            # Unexpected finish without tool_calls and not stop
            turn_complete = True
            break

        # ---- execute tool calls ------------------------------------------
        # Build the assistant message with tool_calls
        tool_calls_list = [tool_call_chunks[i] for i in sorted(tool_call_chunks)]

        # Append assistant tool-call message to the conversation
        openai_messages.append(
            {
                "role": "assistant",
                "content": text_delta or None,
                "tool_calls": tool_calls_list,
            }
        )

        accumulated_tool_calls.extend(tool_calls_list)

        tool_result_messages: list[dict[str, Any]] = []

        for tc in tool_calls_list:
            tool_name = tc["function"]["name"]
            args_str = tc["function"]["arguments"]
            tool_call_id = tc["id"]

            # Parse args
            try:
                args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args = {}

            yield {"type": "tool_call", "name": tool_name, "args": args}

            # Execute server-side in a worker thread so the event loop stays
            # free (tool execution is CPU-bound / blocking I/O).  Inside the
            # worker thread there is no running event loop, so _run_analysis
            # can safely call asyncio.run().
            try:
                result = await asyncio.to_thread(
                    copilot_tools.execute, tool_name, db, aeroplane_id, **args
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Tool %s execution failed", tool_name)
                result = {"error": str(exc)}

            yield {"type": "tool_result", "name": tool_name, "summary": result}

            tool_result_entry = {
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "result": result,
            }
            accumulated_tool_results.append(tool_result_entry)

            tool_result_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(result),
                }
            )

        # Append all tool results to the message thread
        openai_messages.extend(tool_result_messages)

    # If we exhausted MAX_LOOP_ITERATIONS without a clean stop the client
    # should know the turn was cut off so it can tell the user.
    done_event: dict[str, Any] = {
        "type": "done",
        "tool_calls": accumulated_tool_calls,
        "tool_results": accumulated_tool_results,
        "final_text": final_text,
    }
    if not turn_complete:
        done_event["truncated"] = True

    yield done_event
