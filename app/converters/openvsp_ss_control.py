"""OpenVSP SS_CONTROL → TrailingEdgeDevice handler (gh-644).

Per the scope-clarification comment on #644 (RC-scaling focus): this
handler does the **minimal** mapping from a VSP ``SS_CONTROL`` sub-
surface to our :class:`TrailingEdgeDeviceDetailSchema`. The user
edits role/mixing/etc. in the frontend.

Explicitly **out of scope**:

* CSGroup gain matrix
* antisymmetric flag (each TED inherits `symmetric` from its wing)
* Leading-edge devices (warn + skip)
* Role inference (set to ``OTHER``; user can change in UI)

Runs as a post-pass over the populated AeroplaneSchema so it doesn't
need to know wing-handler internals. It re-queries the vsp module
for each WING geom id recorded in :attr:`ImportContext.wing_geom_ids`.
"""

from __future__ import annotations

from types import ModuleType

from app.converters import openvsp_importer
from app.converters.openvsp_importer import AeroplaneSchema, ImportContext
from app.schemas.aeroplaneschema import (
    ControlSurfaceRole,
    TrailingEdgeDeviceDetailSchema,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _u_to_segment_index(*, u: float, n_sec: int) -> int:
    """Map a parametric u ∈ [0, 1] to a segment index 1..n_sec.

    OpenVSP's wing u parameter spans the whole loft; we approximate it
    as a linear distribution across the n_sec segments so the
    inboard-half lands on segment 1, outboard-half on segment n.
    """
    if n_sec < 1:
        return 1
    if u <= 0.0:
        return 1
    if u >= 1.0:
        return n_sec
    return max(1, min(n_sec, int(u * n_sec) + 1))


def _read_parm(vsp: ModuleType, container: str, parm: str, group: str) -> float:
    pid = vsp.FindParm(container, parm, group)
    if not pid:
        return 0.0
    return float(vsp.GetParmVal(pid))


def _handle_wing_sub_surfaces(
    wing_gid: str,
    wing_name: str,
    aeroplane: AeroplaneSchema,
    ctx: ImportContext,
    vsp: ModuleType,
) -> None:
    """Walk SS_CONTROL sub-surfaces on a wing and attach TEDs.

    Skipped (with warning) when:
    * The wing isn't in aeroplane.wings (probably failed earlier).
    * LE_Flag is set (LE devices are out of scope per #644 clarification).
    """
    if not aeroplane.wings or wing_name not in aeroplane.wings:
        return
    wing = aeroplane.wings[wing_name]

    try:
        ss_ids = list(vsp.GetSubSurfIDVec(wing_gid))
    except AttributeError:
        return  # vsp version without sub-surface API; nothing to do.

    ss_control = getattr(vsp, "SS_CONTROL", 3)
    n_sec = max(1, len(wing.x_secs) - 1)

    for sid in ss_ids:
        if vsp.GetSubSurfType(sid) != ss_control:
            continue
        sub_index = vsp.GetSubSurfIndex(sid)
        grp = f"SS_Control_{sub_index + 1}"

        le_flag = _read_parm(vsp, wing_gid, "LE_Flag", grp) >= 0.5
        if le_flag:
            ctx.add_warning(
                component_type="WING_SS_CONTROL",
                component_name=f"{wing_name}::{vsp.GetSubSurfName(sid)}",
                reason=(
                    "Leading-edge sub-surface detected; LE devices are out of "
                    "scope for the Phase 1 RC-scaling importer. Sub-surface skipped."
                ),
                severity="info",
            )
            continue

        eta_flag = _read_parm(vsp, wing_gid, "EtaFlag", grp) >= 0.5
        if eta_flag:
            u_start = _read_parm(vsp, wing_gid, "EtaStart", grp)
            u_end = _read_parm(vsp, wing_gid, "EtaEnd", grp)
        else:
            u_start = _read_parm(vsp, wing_gid, "UStart", grp)
            u_end = _read_parm(vsp, wing_gid, "UEnd", grp)

        # OpenVSP's Length_C_* is the chord fraction measured from
        # the trailing edge towards the hinge; our rel_chord_* is
        # measured from the leading edge.
        c_root_le = 1.0 - _read_parm(vsp, wing_gid, "Length_C_Start", grp)
        c_tip_le = 1.0 - _read_parm(vsp, wing_gid, "Length_C_End", grp)
        deflection = _read_parm(vsp, wing_gid, "Deflection", grp)

        ted = TrailingEdgeDeviceDetailSchema(
            name=vsp.GetSubSurfName(sid),
            role=ControlSurfaceRole.OTHER,
            rel_chord_root=c_root_le,
            rel_chord_tip=c_tip_le,
            deflection_deg=deflection,
            symmetric=wing.symmetric,
        )

        # Attach to the inboard xsec of the segment whose midpoint
        # contains the SS_CONTROL midpoint. The Pydantic model stores
        # TEDs on the xsec whose outgoing segment carries them.
        u_mid = (u_start + u_end) / 2.0
        seg_idx = _u_to_segment_index(u=u_mid, n_sec=n_sec)
        # seg_idx is 1-based; corresponding inboard xsec index is seg_idx - 1
        xsec_idx = seg_idx - 1
        target = wing.x_secs[xsec_idx]
        if target.trailing_edge_device is not None:
            # Already has a TED — keep the existing one and warn.
            ctx.add_warning(
                component_type="WING_SS_CONTROL",
                component_name=f"{wing_name}::{vsp.GetSubSurfName(sid)}",
                reason=(
                    f"Multiple SS_CONTROL sub-surfaces map to wing segment "
                    f"{seg_idx}; only the first is imported as TED."
                ),
                severity="warning",
            )
            continue
        target.trailing_edge_device = ted


def _post_pass(aeroplane: AeroplaneSchema, ctx: ImportContext, vsp: ModuleType) -> None:
    """Run SS_CONTROL → TED for every registered WING geom id."""
    for gid, name in list(ctx.wing_geom_ids.items()):
        try:
            _handle_wing_sub_surfaces(gid, name, aeroplane, ctx, vsp)
        except Exception as exc:  # pragma: no cover - defensive
            ctx.add_warning(
                component_type="WING_SS_CONTROL",
                component_name=name,
                reason=f"SS_CONTROL pass failed on wing {name}: {exc}",
                severity="warning",
            )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register() -> None:
    """Register the SS_CONTROL post-pass."""
    openvsp_importer.register_post_pass(_post_pass)
