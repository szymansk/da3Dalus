"""Removal of rows that belong to one aeroplane node but have no ORM cascade.

Used by every path that deletes aeroplane nodes (``delete_aeroplane``,
``discard_branch``, lineage delete), so there is exactly one implementation
of "what a node owns" (ADR 0022).

Rows bound by a nullable integer FK (analysis) or a plain string uuid
(component tree, construction parts) would otherwise survive and be
inherited by the next aeroplane that reuses the integer id.
"""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel, OperatingPointSetModel
from app.models.component_tree import ComponentTreeNodeModel
from app.models.construction_part import ConstructionPartModel
from app.models.tessellation_cache import TessellationCacheModel


def purge_node_dependents(db: Session, node: AeroplaneModel) -> None:
    """Delete analysis, tree, part and cache rows keyed to *node*.

    Flight envelopes, wings, fuselages etc. are removed by the ORM cascade
    when the node itself is deleted.
    """
    for model in (OperatingPointModel, OperatingPointSetModel):
        db.execute(delete(model).where(model.aircraft_id == node.id))
    db.execute(delete(TessellationCacheModel).where(TessellationCacheModel.aeroplane_id == node.id))
    uuid_key = str(node.uuid)
    # Tree nodes first: they reference construction parts.
    for model in (ComponentTreeNodeModel, ConstructionPartModel):
        db.execute(delete(model).where(model.aeroplane_id == uuid_key))
