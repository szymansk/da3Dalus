"""Background auto-retrim — query dirty OPs, trim each, recompute stability."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.db.session import SessionLocal
from app.models.aeroplanemodel import (
    AeroplaneModel,
    WingModel,
    WingXSecDetailModel,
    WingXSecModel,
    WingXSecTrailingEdgeDeviceModel,
)
from app.models.analysismodels import OperatingPointModel
from app.schemas.aeroanalysisschema import (
    AeroBuildupTrimRequest,
    OperatingPointSchema,
)
from app.services.aerobuildup_trim_service import trim_with_aerobuildup
from app.services.stability_service import get_stability_summary

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_PITCH_TOKENS = {"elevator", "stabilator", "elevon"}


def _find_pitch_control_name(db: Session, aeroplane_id: int) -> str | None:
    """Find the name of the first pitch control surface on the aeroplane."""
    rows = (
        db.query(WingXSecTrailingEdgeDeviceModel.name)
        .join(
            WingXSecDetailModel,
            WingXSecTrailingEdgeDeviceModel.wing_xsec_detail_id == WingXSecDetailModel.id,
        )
        .join(WingXSecModel, WingXSecDetailModel.wing_xsec_id == WingXSecModel.id)
        .join(WingModel, WingXSecModel.wing_id == WingModel.id)
        .filter(WingModel.aeroplane_id == aeroplane_id)
        .all()
    )
    for (name,) in rows:
        if name and any(token in name.lower() for token in _PITCH_TOKENS):
            return name
    return None


def _op_model_to_schema(op: OperatingPointModel) -> OperatingPointSchema:
    """Convert an OperatingPointModel row to an OperatingPointSchema."""
    return OperatingPointSchema(
        name=op.name,
        description=op.description or "",
        velocity=op.velocity,
        alpha=op.alpha,
        beta=op.beta,
        p=op.p or 0.0,
        q=op.q or 0.0,
        r=op.r or 0.0,
        xyz_ref=op.xyz_ref or [0.0, 0.0, 0.0],
        altitude=op.altitude or 0.0,
        control_deflections=op.control_deflections,
    )


async def retrim_dirty_ops(aeroplane_id: int) -> None:
    """Re-trim all DIRTY operating points for an aeroplane.

    Called by the background job tracker after debounce. Uses AeroBuildup
    solver. After all OPs are processed, recomputes stability.
    """
    db = SessionLocal()
    try:
        aeroplane = db.query(AeroplaneModel).filter_by(id=aeroplane_id).first()
        if aeroplane is None:
            logger.error("Retrim: aeroplane %d not found", aeroplane_id)
            return

        pitch_control = _find_pitch_control_name(db, aeroplane_id)
        if pitch_control is None:
            logger.warning(
                "Retrim: no pitch control surface on aeroplane %d — skipping",
                aeroplane_id,
            )
            return

        dirty_ops = (
            db.query(OperatingPointModel)
            .filter_by(aircraft_id=aeroplane_id, status="DIRTY")
            .all()
        )
        if not dirty_ops:
            logger.debug("Retrim: no dirty OPs for aeroplane %d", aeroplane_id)
            return

        aeroplane_uuid = aeroplane.uuid
        any_trimmed = False

        for op in dirty_ops:
            op.status = "COMPUTING"
            db.flush()

            try:
                op_schema = _op_model_to_schema(op)
                request = AeroBuildupTrimRequest(
                    operating_point=op_schema,
                    trim_variable=pitch_control,
                    target_coefficient="Cm",
                    target_value=0.0,
                )
                result = await trim_with_aerobuildup(db, aeroplane_uuid, request)

                if result.converged:
                    op.status = "TRIMMED"
                    any_trimmed = True
                    op.control_deflections = {
                        **(op.control_deflections or {}),
                        pitch_control: result.trimmed_deflection,
                    }
                else:
                    op.status = "LIMIT_REACHED"
            except Exception:
                logger.exception(
                    "Retrim failed for OP %d (%s) on aeroplane %d",
                    op.id,
                    op.name,
                    aeroplane_id,
                )
                op.status = "NOT_TRIMMED"

            db.flush()

        if any_trimmed:
            first_trimmed = (
                db.query(OperatingPointModel)
                .filter_by(aircraft_id=aeroplane_id, status="TRIMMED")
                .first()
            )
            if first_trimmed:
                try:
                    from app.schemas.AeroplaneRequest import AnalysisToolUrlType

                    op_schema = _op_model_to_schema(first_trimmed)
                    await get_stability_summary(
                        db, aeroplane_uuid, op_schema, AnalysisToolUrlType.AEROBUILDUP
                    )
                except Exception:
                    logger.exception(
                        "Stability recomputation failed for aeroplane %d",
                        aeroplane_id,
                    )

        db.commit()
    except Exception:
        logger.exception("Retrim transaction failed for aeroplane %d", aeroplane_id)
        db.rollback()
    finally:
        db.close()
