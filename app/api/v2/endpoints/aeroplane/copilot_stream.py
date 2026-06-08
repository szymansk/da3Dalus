"""SSE endpoint — POST /aeroplanes/{aeroplane_id}/copilot/stream (gh-918).

Flow
----
1. Persist the user message via copilot_history_service.append_message.
2. Load the full history.
3. Run copilot_service.run_turn as an async generator.
4. Format each yielded event via _sse_format and stream as text/event-stream.
5. On receiving the ``done`` event, persist the final assistant message
   (with accumulated tool_calls and tool_results).
6. Any exception → ``event: error {message}``; never leak the API key.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from fastapi.responses import StreamingResponse
from pydantic import UUID4, BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.copilot_history import CopilotMessageWrite
from app.services import copilot_history_service as hist_svc
from app.services import copilot_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request body
# ---------------------------------------------------------------------------


class CopilotStreamRequest(BaseModel):
    message: str = Field(..., description="User message to send to the copilot")
    context_hint: str = Field(
        default="",
        description="Short context string injected into the system prompt (e.g. active tab + aircraft name)",
    )


# ---------------------------------------------------------------------------
# SSE helper (mirrors openvsp_import._sse_format)
# ---------------------------------------------------------------------------


def _sse_format(event_type: str, data: dict) -> str:
    """Encode one SSE event as a UTF-8 string."""
    return f"event: {event_type}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/aeroplanes/{aeroplane_id}/copilot/stream",
    tags=["copilot"],
    operation_id="copilot_stream",
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": (
                "SSE stream. Events: "
                "``token`` {text} — assistant text delta; "
                "``tool_call`` {name, args} — tool invocation; "
                "``tool_result`` {name, summary} — tool result; "
                "``done`` — turn complete; "
                "``error`` {message} — error (key never leaked)."
            ),
        },
        404: {"description": "Aeroplane not found"},
        422: {"description": "Validation error"},
    },
)
async def copilot_stream(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    body: Annotated[CopilotStreamRequest, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    """Stream a copilot response as text/event-stream.

    Persists the user message first, runs the tool-calling loop against the
    LiteLLM hub (OpenAI SDK, hub mocked in CI), and persists the final
    assistant message on completion.
    """
    # Validate aeroplane exists and persist the user message
    try:
        hist_svc.append_message(
            db,
            aeroplane_id,
            CopilotMessageWrite(role="user", content=body.message),
        )
    except Exception as exc:
        # Convert service / not-found errors to HTTP before opening the stream
        from app.core.exceptions import NotFoundError, ServiceException

        if isinstance(exc, NotFoundError):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if isinstance(exc, ServiceException):
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc

    # Load history (includes the user message we just appended)
    history = hist_svc.get_history(db, aeroplane_id)

    # Look up the integer PK (tools need it)
    from app.models.aeroplanemodel import AeroplaneModel

    plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_id).first()
    if plane is None:
        raise HTTPException(status_code=404, detail="Aeroplane not found")

    async def _generate() -> AsyncGenerator[str, None]:
        accumulated_tool_calls = []
        accumulated_tool_results = []
        final_text = ""

        try:
            async for event in copilot_service.run_turn(
                db=db,
                aeroplane_id=plane.id,
                history=history,
                context_hint=body.context_hint,
            ):
                event_type = event.get("type", "unknown")

                if event_type == "done":
                    accumulated_tool_calls = event.get("tool_calls", [])
                    accumulated_tool_results = event.get("tool_results", [])
                    final_text = event.get("final_text", "")
                    # Persist the final assistant message
                    try:
                        hist_svc.append_message(
                            db,
                            aeroplane_id,
                            CopilotMessageWrite(
                                role="assistant",
                                content=final_text,
                                tool_calls=accumulated_tool_calls or None,
                                tool_results=accumulated_tool_results or None,
                            ),
                        )
                    except Exception as persist_exc:
                        logger.error("Failed to persist assistant message: %s", persist_exc)
                    done_data: dict = {"status": "ok"}
                    # Forward the max-iterations cut-off flag so the client can
                    # tell the user the turn was truncated (the service sets it
                    # only when the loop hit MAX_LOOP_ITERATIONS).
                    if event.get("truncated"):
                        done_data["truncated"] = True
                    yield _sse_format("done", done_data)

                elif event_type == "error":
                    yield _sse_format("error", {"message": event.get("message", "Unknown error")})

                elif event_type == "token":
                    yield _sse_format("token", {"text": event.get("text", "")})

                elif event_type == "tool_call":
                    yield _sse_format(
                        "tool_call",
                        {"name": event.get("name", ""), "args": event.get("args", {})},
                    )

                elif event_type == "tool_result":
                    yield _sse_format(
                        "tool_result",
                        {"name": event.get("name", ""), "summary": event.get("summary", {})},
                    )

        except Exception as exc:
            logger.exception("Unhandled error in copilot stream generator")
            yield _sse_format("error", {"message": "Internal server error"})

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
