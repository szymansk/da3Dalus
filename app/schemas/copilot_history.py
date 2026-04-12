from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class CopilotMessageWrite(BaseModel):
    role: Literal["user", "assistant", "tool"] = Field(..., description="Message role")
    content: str = Field("", description="Message text content")
    tool_calls: Optional[list[dict[str, Any]]] = Field(None, description="Tool call payloads")
    tool_results: Optional[list[dict[str, Any]]] = Field(None, description="Tool result payloads")
    parent_id: Optional[int] = Field(None, description="Parent message ID for branching")


class CopilotMessageRead(CopilotMessageWrite):
    id: int = Field(..., description="Message ID")
    created_at: datetime = Field(..., description="Creation timestamp")


class CopilotHistory(BaseModel):
    messages: list[CopilotMessageRead] = Field(default_factory=list)
