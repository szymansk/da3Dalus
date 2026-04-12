"""Copilot History Service — per-aeroplane chat thread persistence."""

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError
from app.models.aeroplanemodel import AeroplaneModel, CopilotMessageModel
from app.schemas.copilot_history import CopilotHistory, CopilotMessageRead, CopilotMessageWrite

logger = logging.getLogger(__name__)


def _get_aeroplane(db: Session, aeroplane_uuid) -> AeroplaneModel:
    aeroplane = db.query(AeroplaneModel).filter(
        AeroplaneModel.uuid == aeroplane_uuid
    ).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def _msg_to_schema(msg: CopilotMessageModel) -> CopilotMessageRead:
    return CopilotMessageRead(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        tool_calls=msg.tool_calls,
        tool_results=msg.tool_results,
        parent_id=msg.parent_id,
        created_at=msg.created_at,
    )


def get_history(db: Session, aeroplane_uuid) -> CopilotHistory:
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    messages = [_msg_to_schema(m) for m in aeroplane.copilot_messages]
    return CopilotHistory(messages=messages)


def append_message(
    db: Session, aeroplane_uuid, data: CopilotMessageWrite
) -> CopilotMessageRead:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        next_index = len(aeroplane.copilot_messages)
        msg = CopilotMessageModel(
            aeroplane_id=aeroplane.id,
            sort_index=next_index,
            role=data.role,
            content=data.content,
            tool_calls=data.tool_calls,
            tool_results=data.tool_results,
            parent_id=data.parent_id,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return _msg_to_schema(msg)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in append_message: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def clear_history(db: Session, aeroplane_uuid) -> None:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        for msg in list(aeroplane.copilot_messages):
            db.delete(msg)
        db.commit()
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in clear_history: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def delete_message(db: Session, aeroplane_uuid, message_id: int) -> None:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        msg = next((m for m in aeroplane.copilot_messages if m.id == message_id), None)
        if msg is None:
            raise NotFoundError(entity="CopilotMessage", resource_id=message_id)
        db.delete(msg)
        db.commit()
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in delete_message: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc
