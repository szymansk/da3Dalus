"""OpenVSP BLANK + Vehicle CG handler (gh-645).

BLANK geoms in OpenVSP are pure transforms with optional Mass and
Inertia. We import them as :class:`WeightItemWrite` records collected
in :attr:`ImportResult.weight_items`. The vehicle-wide centre-of-
gravity (and total mass when declared) lives on the vehicle
container's ``Mass_Props`` group; we resolve it in a post-pass and
write it onto :attr:`AeroplaneSchema.xyz_ref`.

Scope (per ``feedback_openvsp_import_rc_scope``):

* In scope: explicit BLANK Mass + XForm position, vehicle CG/TotalMass.
* Out of scope: inertia tensor (closed #657), Density/MassShell volumetric
  masses on BLANK geoms (Phase 2).
"""

from __future__ import annotations

from types import ModuleType

from app.converters import openvsp_importer
from app.converters.openvsp_importer import AeroplaneSchema, ImportContext
from app.schemas.weight_item import WeightItemWrite


# ---------------------------------------------------------------------------
# BLANK handler
# ---------------------------------------------------------------------------


def _find_parm(vsp: ModuleType, container: str, parm: str, group: str) -> str:
    return vsp.FindParm(container, parm, group)


def _get_val(vsp: ModuleType, pid: str) -> float:
    if not pid:
        return 0.0
    return float(vsp.GetParmVal(pid))


def _handle_blank(
    gid: str,
    name: str,
    aeroplane: AeroplaneSchema,
    ctx: ImportContext,
    vsp: ModuleType,
) -> None:
    """Convert a BLANK geom into a WeightItemWrite.

    Pure-transform BLANKs (no mass parm or Mass==0) are skipped
    silently. Negative masses emit a warning and are skipped.
    """
    mass_pid = _find_parm(vsp, gid, "Mass", "Mass_Props")
    if not mass_pid:
        return  # pure-transform BLANK; not an error
    mass = _get_val(vsp, mass_pid)
    if mass == 0:
        return
    if mass < 0:
        ctx.add_warning(
            component_type="BLANK",
            component_name=name,
            reason=f"BLANK {name!r} has negative mass ({mass}); skipped.",
            severity="warning",
        )
        return

    x = _get_val(vsp, _find_parm(vsp, gid, "X_Location", "XForm"))
    y = _get_val(vsp, _find_parm(vsp, gid, "Y_Location", "XForm"))
    z = _get_val(vsp, _find_parm(vsp, gid, "Z_Location", "XForm"))

    ctx.add_weight_item(
        WeightItemWrite(
            name=name,
            mass_kg=mass,
            x_m=x,
            y_m=y,
            z_m=z,
            description=f"Imported from OpenVSP BLANK geom {gid}",
            category="other",
        )
    )


# ---------------------------------------------------------------------------
# Vehicle-CG post-pass
# ---------------------------------------------------------------------------


def _resolve_vehicle_cg(aeroplane: AeroplaneSchema, ctx: ImportContext, vsp: ModuleType) -> None:
    """Read Mass_Props on the vehicle container; fall back to computed CG.

    1. If the vehicle declares X_CG/Y_CG/Z_CG, use those.
    2. Else compute mass-weighted average from collected weight items.
    3. Else leave the default ``[0, 0, 0]``.
    4. Warn if declared TotalMass mismatches the sum of imported items
       by more than 1%.
    """
    try:
        vehicle_id = vsp.GetVehicleID()
    except Exception:
        return  # No vehicle — nothing to do.

    total_mass_pid = _find_parm(vsp, vehicle_id, "TotalMass", "Mass_Props")
    declared_total = _get_val(vsp, total_mass_pid) if total_mass_pid else 0.0

    xcg_pid = _find_parm(vsp, vehicle_id, "X_CG", "Mass_Props")
    ycg_pid = _find_parm(vsp, vehicle_id, "Y_CG", "Mass_Props")
    zcg_pid = _find_parm(vsp, vehicle_id, "Z_CG", "Mass_Props")
    declared_cg = (
        (
            _get_val(vsp, xcg_pid),
            _get_val(vsp, ycg_pid),
            _get_val(vsp, zcg_pid),
        )
        if (xcg_pid or ycg_pid or zcg_pid)
        else None
    )

    if declared_total > 0:
        aeroplane.total_mass_kg = declared_total

    if declared_cg is not None and any(v != 0 for v in declared_cg):
        aeroplane.xyz_ref = list(declared_cg)
    elif ctx.weight_items:
        total = sum(w.mass_kg for w in ctx.weight_items)
        if total > 0:
            aeroplane.xyz_ref = [
                sum(w.mass_kg * getattr(w, axis) for w in ctx.weight_items) / total
                for axis in ("x_m", "y_m", "z_m")
            ]

    # Consistency check: if declared TotalMass exists, compare to sum.
    if declared_total > 0 and ctx.weight_items:
        items_total = sum(w.mass_kg for w in ctx.weight_items)
        if items_total > 0:
            rel = abs(items_total - declared_total) / declared_total
            if rel > 0.01:
                ctx.add_warning(
                    component_type="VEHICLE",
                    component_name="vehicle",
                    reason=(
                        f"Total mass mismatch: BLANK sum = {items_total:.3f} kg "
                        f"vs declared TotalMass = {declared_total:.3f} kg "
                        f"({rel * 100:.1f}% relative)."
                    ),
                    severity="warning",
                )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register() -> None:
    """Register the BLANK handler and the vehicle-CG post-pass."""
    openvsp_importer.register_handler("BLANK", _handle_blank)
    openvsp_importer.register_post_pass(_resolve_vehicle_cg)
