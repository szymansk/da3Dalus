"""Clone service for the aircraft versioning system (gh-904).

``clone_aeroplane_subgraph`` deep-copies the full owned subgraph of an
AeroplaneModel — all design-bearing tables — into new rows with new PKs,
re-keying every internal FK so the clone is a fully independent copy.

Shared references (flight_profile, components library, TED servo's
component_id) are preserved as-is.  Transient/computed data (operating
points, flight envelope) and conversation history (copilot_messages)
are NOT cloned — the caller supplies version-metadata directly.

No db.commit() is called; get_db() owns the transaction.
"""

from __future__ import annotations

import copy
import logging
import uuid as _uuid_mod
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.models.aeroplanemodel import (
    AeroplaneModel,
    DesignAssumptionModel,
    FuselageModel,
    FuselageXSecSuperEllipseModel,
    LoadingScenarioModel,
    WeightItemModel,
    WingModel,
    WingXSecDetailModel,
    WingXSecModel,
    WingXSecSpareModel,
    WingXSecTedServoModel,
    WingXSecTrailingEdgeDeviceModel,
    WingXSecTurbulatorModel,
)
from app.models.component_tree import ComponentTreeNodeModel
from app.models.computation_config import AircraftComputationConfigModel
from app.models.mission_objective import MissionObjectiveModel
from app.models.stability_result import StabilityResultModel


# ---------------------------------------------------------------------------
# Coverage registry — every table with a (transitive) FK to ``aeroplanes``
# MUST appear in exactly one of these two sets.  The coverage test
# (test_aeroplane_clone_coverage.py) asserts that every discovered table is
# present in either set.
# ---------------------------------------------------------------------------

#: Tables that are deep-copied into the new aeroplane node.
#
# COVERAGE-TEST BLIND SPOT — STRING-FK TABLES
# The coverage test (test_aeroplane_clone_coverage.py) introspects SQLAlchemy
# ForeignKey objects to discover which tables are related to ``aeroplanes``.
# It therefore CANNOT find tables whose aeroplane reference is stored as a
# plain String column (no SQLAlchemy ForeignKey constraint), because those
# string FKs are invisible to the reflection-based BFS.
#
# Tables currently in this category (must be maintained manually):
#   • ``component_tree``  — aeroplane_id is VARCHAR(UUID); no int FK
#   • ``construction_plans`` — soft string FK; EXCLUDED intentionally
#   • ``construction_parts`` — string aeroplane_id; EXCLUDED intentionally
#
# If you add a new table with a string aeroplane reference, you MUST add it
# here (or to EXCLUDED_TABLES) by hand — the coverage test will not catch it.
CLONED_TABLES: frozenset[str] = frozenset(
    [
        "aeroplanes",  # the root — a new row is created
        "wings",  # owned by aeroplane_id FK
        "wing_xsecs",  # owned by wing_id FK
        "wing_xsec_details",  # owned by wing_xsec_id FK
        "wing_xsec_spares",  # owned by wing_xsec_detail_id FK
        "wing_xsec_trailing_edge_devices",  # owned by wing_xsec_detail_id FK
        "wing_xsec_turbulators",  # owned by wing_xsec_detail_id FK (gh-934)
        "wing_xsec_ted_servos",  # owned by ted_id FK; component_id is a shared ref
        "fuselages",  # owned by aeroplane_id FK; step_path/solid_step_path nulled
        "fuselage_xsecs",  # owned by fuselage_id FK
        "weight_items",  # owned by aeroplane_id FK
        "mission_objectives",  # owned by aeroplane_id FK (unique per aeroplane)
        "design_assumptions",  # owned by aeroplane_id FK
        "aircraft_computation_config",  # owned by aeroplane_id FK
        "stability_results",  # owned by aeroplane_id FK
        "loading_scenarios",  # owned; component_overrides JSON remapped
        # STRING-FK: aeroplane_id is VARCHAR(UUID), not an integer FK → invisible
        # to the BFS introspection; added manually (see blind-spot note above).
        "component_tree",  # owned; aeroplane_id = UUID str; parent_id remapped
    ]
)

#: Tables that are intentionally NOT cloned, with a brief reason.
EXCLUDED_TABLES: dict[str, str] = {
    # ── shared / library references ──────────────────────────────────────────
    "rc_flight_profiles": "shared flight-profile reference; FK kept as-is",
    "components": "global COTS component library; shared reference",
    "component_types": "component-type taxonomy; shared, no FK to aeroplanes",
    # ── transient / recomputed ────────────────────────────────────────────────
    "operating_points": "transient; recomputed on demand from geometry",
    "operating_pointsets": "transient; recomputed on demand from geometry",
    "flight_envelopes": "transient; recomputed on demand from assumptions",
    # ── conversation / provenance ─────────────────────────────────────────────
    "copilot_messages": "conversation excluded; provenance captured via note + cursor",
    # ── versioning meta (managed by caller, not cloned into child) ───────────
    "branches": "versioning meta; managed by the versioning service",
    # ── construction artefacts (string FK, not int-FK cascade) ───────────────
    "construction_plans": ("soft string FK to aeroplanes; template-style, not per-version-copy"),
    "construction_parts": (
        "string aeroplane_id (no int FK); per-aeroplane but file-backed — "
        "not cloned to avoid stale file references"
    ),
    # ── internal cross-references (no direct FK to aeroplanes) ───────────────
    "avl_geometry_events": "event-listener module; no own DB table",
    "stability_events": "internal event type; no own table",
    # ── misc library / lookup tables ─────────────────────────────────────────
    "airfoils": "airfoil geometry library; global shared data",
    "airfoil_low_re": "pre-computed polar cache; global shared data",
    "rc_flight_profile_entries": "child rows of rc_flight_profiles; shared",
    "tessellation_cache": (
        "geometry cache keyed by content hash; regenerated on demand — "
        "copying stale cache entries would waste space and may reference "
        "CAD artefacts that no longer exist"
    ),
    "avl_geometry_files": (
        "user-edited AVL geometry; per-aeroplane artefact but regenerated / "
        "re-edited on demand — copying would carry stale is_user_edited flags"
    ),
    "mission_presets": "global preset library; shared",
    "alembic_version": "migration tracking; not an app table",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def clone_aeroplane_subgraph(
    db: Session,
    source: AeroplaneModel,
    *,
    immutable: bool,
    branch_id: int | None,
    predecessor_id: int | None,
    root_id: int | None,
) -> AeroplaneModel:
    """Deep-copy the owned subgraph of *source* into a new AeroplaneModel.

    Creates new DB rows for every table listed in ``CLONED_TABLES``,
    re-keying all internal FKs to the new parent rows.  Shared references
    (flight_profile, component library entries) are preserved.

    No ``db.commit()`` is called — the caller's transaction (get_db)
    owns the commit boundary.  ``db.flush()`` is used after each group of
    inserts so that auto-generated PKs are available for FK re-keying.

    Parameters
    ----------
    db:
        Active SQLAlchemy Session (from get_db dependency).
    source:
        The aeroplane node to clone.  Must already be persisted (has ``.id``).
    immutable:
        Set ``is_immutable`` on the new node (True for snapshots, False for
        mutable branch heads).
    branch_id:
        FK to the ``branches`` row the clone belongs to (may be None when
        called from ``create_branch`` before the branch row exists — the
        caller must fill it in afterwards).
    predecessor_id:
        Self-referential FK: the node this was forked from.
    root_id:
        Lineage root node id.  Pass ``None`` and the caller must set it to
        the new node's own id (for the root itself).

    Returns
    -------
    AeroplaneModel
        The newly created (unflushed) aeroplane node with all children
        already added to the session.
    """
    # ── 1. Clone the root aeroplane row ──────────────────────────────────────
    clone = AeroplaneModel(
        uuid=_uuid_mod.uuid4(),
        name=source.name,
        total_mass_kg=source.total_mass_kg,
        flight_profile_id=source.flight_profile_id,  # shared ref — kept
        xyz_ref=copy.deepcopy(source.xyz_ref),
        assumption_computation_context=copy.deepcopy(source.assumption_computation_context),
        # Versioning metadata supplied by caller
        is_immutable=immutable,
        branch_id=branch_id,
        predecessor_id=predecessor_id,
        root_id=root_id,
        # Version label / note / provenance are caller's responsibility
        version_label=None,
        version_note=None,
        created_by=None,
        provenance_message_id=None,
        preview_png=None,
    )
    db.add(clone)
    db.flush()  # obtain clone.id

    # ── 2. Weight items ───────────────────────────────────────────────────────
    # We build an old-id → new-id map so loading_scenarios can remap
    # component_overrides (which store str(weight_item.id) as component_uuid).
    weight_id_map: dict[str, str] = {}  # str(old_id) → str(new_id)
    for wi in source.weight_items or []:
        new_wi = WeightItemModel(
            aeroplane_id=clone.id,
            name=wi.name,
            mass_kg=wi.mass_kg,
            x_m=wi.x_m,
            y_m=wi.y_m,
            z_m=wi.z_m,
            description=wi.description,
            category=wi.category,
        )
        db.add(new_wi)
        db.flush()
        weight_id_map[str(wi.id)] = str(new_wi.id)

    # ── 3. Wings → xsecs → details → spares + TEDs + servos ─────────────────
    for wing in source.wings or []:
        new_wing = WingModel(
            aeroplane_id=clone.id,
            name=wing.name,
            symmetric=wing.symmetric,
            design_model=wing.design_model,
        )
        db.add(new_wing)
        db.flush()

        for xsec in wing.x_secs or []:
            new_xsec = WingXSecModel(
                wing_id=new_wing.id,
                xyz_le=copy.deepcopy(xsec.xyz_le),
                chord=xsec.chord,
                twist=xsec.twist,
                airfoil=xsec.airfoil,
                sort_index=xsec.sort_index,
            )
            db.add(new_xsec)
            db.flush()

            if xsec.detail is not None:
                detail = xsec.detail
                new_detail = WingXSecDetailModel(
                    wing_xsec_id=new_xsec.id,
                    x_sec_type=detail.x_sec_type,
                    tip_type=detail.tip_type,
                    number_interpolation_points=detail.number_interpolation_points,
                )
                db.add(new_detail)
                db.flush()

                # Spares
                for spare in detail.spares or []:
                    new_spare = WingXSecSpareModel(
                        wing_xsec_detail_id=new_detail.id,
                        sort_index=spare.sort_index,
                        spare_support_dimension_width=spare.spare_support_dimension_width,
                        spare_support_dimension_height=spare.spare_support_dimension_height,
                        spare_position_factor=spare.spare_position_factor,
                        spare_length=spare.spare_length,
                        spare_start=spare.spare_start,
                        spare_mode=spare.spare_mode,
                        spare_vector=copy.deepcopy(spare.spare_vector),
                        spare_origin=copy.deepcopy(spare.spare_origin),
                    )
                    db.add(new_spare)

                # Turbulator (gh-934) — optional one-to-one per detail (gh-1069)
                turbulator = detail.turbulator
                if turbulator is not None:
                    new_turbulator = WingXSecTurbulatorModel(
                        wing_xsec_detail_id=new_detail.id,
                        form=turbulator.form,
                        height_mm=turbulator.height_mm,
                        position_root=turbulator.position_root,
                        position_tip=turbulator.position_tip,
                        enabled=turbulator.enabled,
                    )
                    db.add(new_turbulator)

                # TED + servo
                ted = detail.trailing_edge_device
                if ted is not None:
                    new_ted = WingXSecTrailingEdgeDeviceModel(
                        wing_xsec_detail_id=new_detail.id,
                        name=ted.name,
                        role=ted.role,
                        label=ted.label,
                        rel_chord_root=ted.rel_chord_root,
                        rel_chord_tip=ted.rel_chord_tip,
                        hinge_spacing=ted.hinge_spacing,
                        side_spacing_root=ted.side_spacing_root,
                        side_spacing_tip=ted.side_spacing_tip,
                        servo_placement=ted.servo_placement,
                        rel_chord_servo_position=ted.rel_chord_servo_position,
                        rel_length_servo_position=ted.rel_length_servo_position,
                        positive_deflection_deg=ted.positive_deflection_deg,
                        negative_deflection_deg=ted.negative_deflection_deg,
                        deflection_deg=ted.deflection_deg,
                        trailing_edge_offset_factor=ted.trailing_edge_offset_factor,
                        hinge_type=ted.hinge_type,
                        symmetric=ted.symmetric,
                        mix_gain_primary=ted.mix_gain_primary,
                        mix_gain_secondary=ted.mix_gain_secondary,
                        differential_ratio=ted.differential_ratio,
                        servo_index=ted.servo_index,
                    )
                    db.add(new_ted)
                    db.flush()

                    # Servo (keep component_id — shared library reference)
                    if ted.servo_data is not None:
                        sv = ted.servo_data
                        new_servo = WingXSecTedServoModel(
                            ted_id=new_ted.id,
                            component_id=sv.component_id,  # shared ref
                            length=sv.length,
                            width=sv.width,
                            height=sv.height,
                            leading_length=sv.leading_length,
                            latch_z=sv.latch_z,
                            latch_x=sv.latch_x,
                            latch_thickness=sv.latch_thickness,
                            latch_length=sv.latch_length,
                            cable_z=sv.cable_z,
                            screw_hole_lx=sv.screw_hole_lx,
                            screw_hole_d=sv.screw_hole_d,
                        )
                        db.add(new_servo)

    # ── 4. Fuselages → xsecs (null STEP paths) ───────────────────────────────
    for fus in source.fuselages or []:
        new_fus = FuselageModel(
            aeroplane_id=clone.id,
            name=fus.name,
            symmetric=fus.symmetric,
            step_path=None,  # regenerated on demand
            solid_step_path=None,  # regenerated on demand
        )
        db.add(new_fus)
        db.flush()

        for xsec in fus.x_secs or []:
            new_xsec = FuselageXSecSuperEllipseModel(
                fuselage_id=new_fus.id,
                xyz=copy.deepcopy(xsec.xyz),
                a=xsec.a,
                b=xsec.b,
                n=xsec.n,
                sort_index=xsec.sort_index,
            )
            db.add(new_xsec)

    # ── 5. Mission objective ──────────────────────────────────────────────────
    mo = source.mission_objective
    if mo is not None:
        new_mo = MissionObjectiveModel(
            aeroplane_id=clone.id,
            mission_type=mo.mission_type,
            target_cruise_mps=mo.target_cruise_mps,
            target_stall_safety=mo.target_stall_safety,
            target_maneuver_n=mo.target_maneuver_n,
            target_glide_ld=mo.target_glide_ld,
            target_climb_energy=mo.target_climb_energy,
            target_wing_loading_n_m2=mo.target_wing_loading_n_m2,
            target_field_length_m=mo.target_field_length_m,
            available_runway_m=mo.available_runway_m,
            runway_type=mo.runway_type,
            t_static_N=mo.t_static_N,
            takeoff_mode=mo.takeoff_mode,
            landing_surface=mo.landing_surface,
            landing_safety_factor=mo.landing_safety_factor,
            available_field_length_m=mo.available_field_length_m,
        )
        db.add(new_mo)

    # ── 6. Design assumptions ─────────────────────────────────────────────────
    for da in source.design_assumptions or []:
        new_da = DesignAssumptionModel(
            aeroplane_id=clone.id,
            parameter_name=da.parameter_name,
            estimate_value=da.estimate_value,
            calculated_value=da.calculated_value,
            calculated_source=da.calculated_source,
            active_source=da.active_source,
            divergence_pct=da.divergence_pct,
        )
        db.add(new_da)

    # ── 7. Aircraft computation config ────────────────────────────────────────
    cc = source.computation_config
    if cc is not None:
        new_cc = AircraftComputationConfigModel(
            aeroplane_id=clone.id,
            coarse_alpha_min_deg=cc.coarse_alpha_min_deg,
            coarse_alpha_max_deg=cc.coarse_alpha_max_deg,
            coarse_alpha_step_deg=cc.coarse_alpha_step_deg,
            fine_alpha_margin_deg=cc.fine_alpha_margin_deg,
            fine_alpha_step_deg=cc.fine_alpha_step_deg,
            fine_velocity_count=cc.fine_velocity_count,
            debounce_seconds=cc.debounce_seconds,
        )
        db.add(new_cc)

    # ── 8. Stability results ──────────────────────────────────────────────────
    for sr in source.stability_results or []:
        new_sr = StabilityResultModel(
            aeroplane_id=clone.id,
            solver=sr.solver,
            neutral_point_x=sr.neutral_point_x,
            mac=sr.mac,
            cg_x_used=sr.cg_x_used,
            static_margin_pct=sr.static_margin_pct,
            stability_class=sr.stability_class,
            cg_range_forward=sr.cg_range_forward,
            cg_range_aft=sr.cg_range_aft,
            Cma=sr.Cma,
            Cnb=sr.Cnb,
            Clb=sr.Clb,
            trim_alpha_deg=sr.trim_alpha_deg,
            trim_elevator_deg=sr.trim_elevator_deg,
            is_statically_stable=sr.is_statically_stable,
            is_directionally_stable=sr.is_directionally_stable,
            is_laterally_stable=sr.is_laterally_stable,
            computed_at=sr.computed_at,
            status=sr.status,
            geometry_hash=sr.geometry_hash,
        )
        db.add(new_sr)

    # ── 9. Loading scenarios (remap weight_item id refs in component_overrides)
    for ls in source.loading_scenarios or []:
        new_overrides = _remap_component_overrides(ls.component_overrides, weight_id_map)
        new_ls = LoadingScenarioModel(
            aeroplane_id=clone.id,
            name=ls.name,
            aircraft_class=ls.aircraft_class,
            component_overrides=new_overrides,
            is_default=ls.is_default,
        )
        db.add(new_ls)

    # ── 10. Component tree (re-key aeroplane_id + parent_id) ─────────────────
    _clone_component_tree(db, source, clone)

    db.flush()  # make all new ids visible before returning
    return clone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _remap_component_overrides(
    overrides: Any,
    weight_id_map: dict[str, str],
) -> Any:
    """Remap ``component_uuid`` values in *overrides* using *weight_id_map*.

    ``component_overrides`` is a JSON dict whose ``toggles``,
    ``mass_overrides``, and ``position_overrides`` lists each contain dicts
    with a ``component_uuid`` key that holds ``str(weight_item.id)``.  We
    replace each old id with the corresponding new id from *weight_id_map*.

    Values not in the map are passed through unchanged (they may refer to
    COTS component UUIDs which are shared refs).
    """
    if not overrides or not weight_id_map:
        return copy.deepcopy(overrides) if overrides else overrides

    result = copy.deepcopy(overrides)

    for list_key in ("toggles", "mass_overrides", "position_overrides"):
        items = result.get(list_key) if isinstance(result, dict) else None
        if not items:
            continue
        for item in items:
            if isinstance(item, dict) and "component_uuid" in item:
                old_uuid = item["component_uuid"]
                item["component_uuid"] = weight_id_map.get(old_uuid, old_uuid)

    return result


def _clone_component_tree(
    db: Session,
    source: AeroplaneModel,
    clone: AeroplaneModel,
) -> None:
    """Clone all component_tree nodes for *source* into *clone*.

    - ``aeroplane_id`` (STRING) is updated to ``str(clone.uuid)`` because
      the component-tree service uses the UUID string as the aeroplane
      identifier (the URL path parameter is the UUID).
    - ``parent_id`` is remapped from old node ids to new node ids using a
      pass-1 / pass-2 approach: create all nodes in topological order
      (roots first, then children), collecting old_id → new_id as we go,
      then update parent_id references.
    """
    # Fetch all nodes for this aeroplane.  The aeroplane_id is stored as a
    # string; in practice the frontend passes the UUID string.
    old_uuid_str = str(source.uuid)
    nodes = (
        db.query(ComponentTreeNodeModel)
        .filter(ComponentTreeNodeModel.aeroplane_id == old_uuid_str)
        .order_by(ComponentTreeNodeModel.id)
        .all()
    )

    if not nodes:
        return

    new_uuid_str = str(clone.uuid)
    id_map: dict[int, int] = {}  # old node id → new node id

    # Pass 1: insert all nodes with parent_id=None (we fix it in pass 2).
    for node in nodes:
        new_node = ComponentTreeNodeModel(
            aeroplane_id=new_uuid_str,
            parent_id=None,  # fixed in pass 2
            sort_index=node.sort_index,
            node_type=node.node_type,
            name=node.name,
            shape_key=node.shape_key,
            shape_hash=node.shape_hash,
            volume_mm3=node.volume_mm3,
            area_mm2=node.area_mm2,
            component_id=node.component_id,  # shared COTS ref
            quantity=node.quantity,
            construction_part_id=node.construction_part_id,  # shared ref
            pos_x=node.pos_x,
            pos_y=node.pos_y,
            pos_z=node.pos_z,
            rot_x=node.rot_x,
            rot_y=node.rot_y,
            rot_z=node.rot_z,
            material_id=node.material_id,  # shared ref
            weight_override_g=node.weight_override_g,
            print_type=node.print_type,
            scale_factor=node.scale_factor,
            synced_from=node.synced_from,
        )
        db.add(new_node)
        db.flush()
        id_map[node.id] = new_node.id

    # Pass 2: fix parent_id references using the id map.
    for node in nodes:
        if node.parent_id is not None:
            new_parent_id = id_map.get(node.parent_id)
            if new_parent_id is not None:
                new_node_id = id_map[node.id]
                db.query(ComponentTreeNodeModel).filter(
                    ComponentTreeNodeModel.id == new_node_id
                ).update({"parent_id": new_parent_id})
            else:
                # The source node's parent_id is not in the id_map — this means
                # the parent node belongs to a different aeroplane (cross-aeroplane
                # reference) or the data is corrupt.  We drop the parent link
                # (parent_id stays None from pass-1) and log a warning so the
                # operator can investigate without a silent data loss.
                logger.warning(
                    "_clone_component_tree: node %s (source id=%s) has parent_id=%s "
                    "that is not in the cloned node set for aeroplane %s → %s. "
                    "parent_id left as None on the cloned node.",
                    id_map[node.id],
                    node.id,
                    node.parent_id,
                    source.id,
                    clone.id,
                )
