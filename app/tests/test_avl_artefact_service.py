"""Tests for AVL reproducibility artefacts (gh-529 / epic gh-525 C4)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.schemas.avl_artefact import AvlArtefact, AvlIndexSnapshot, AvlRunState
from app.services.avl_artefact_service import (
    build_avl_artefact,
    compute_geometry_hash,
    verify_avl_replay,
)
from app.services.avl_strip_forces import (
    build_yduplicate_sign_map,
    get_control_surface_index_map,
)


def _cs(name: str, *, symmetric: bool = True, hinge_point: float = 0.75) -> SimpleNamespace:
    """Build a minimal stub matching the asb.ControlSurface attributes
    we read (name, symmetric, hinge_point, deflection)."""
    return SimpleNamespace(
        name=name,
        symmetric=symmetric,
        hinge_point=hinge_point,
        deflection=0.0,
    )


def _wing(*xsec_control_groups: tuple[SimpleNamespace, ...]) -> SimpleNamespace:
    """Build a stub wing with one xsec per group of control surfaces."""
    xsecs = [SimpleNamespace(control_surfaces=list(group)) for group in xsec_control_groups]
    return SimpleNamespace(xsecs=xsecs)


def _airplane(*wings: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(wings=list(wings))


def _canonical_4surface_airplane() -> SimpleNamespace:
    """Canonical fixture: aileron pair (symmetric=False), elevator,
    rudder, flap. Replicates a typical RC trainer surface set."""
    aileron = _cs("[aileron]Aileron", symmetric=False, hinge_point=0.75)
    flap = _cs("[flap]Flap", symmetric=True, hinge_point=0.70)
    elevator = _cs("[elevator]Elevator", symmetric=True, hinge_point=0.80)
    rudder = _cs("[rudder]Rudder", symmetric=True, hinge_point=0.78)

    main_wing = _wing((aileron,), (flap,))  # two xsecs on main wing
    h_tail = _wing((elevator,))
    v_tail = _wing((rudder,))
    return _airplane(main_wing, h_tail, v_tail)


# ============================================================================
# YDUPLICATE-dedup
# ============================================================================


def test_index_map_dedupes_symmetric_pair_to_one_index():
    """Canonical 4-surface fixture: aileron + elevator + rudder + flap →
    4 indices, NOT 8 (ASB uses one control_surface per logical pair)."""
    airplane = _canonical_4surface_airplane()
    cs_map = get_control_surface_index_map(airplane)
    assert len(cs_map) == 4, f"Expected 4 AVL d-indices, got {len(cs_map)}: {cs_map}"
    # Order should match input traversal: aileron first (main wing first xsec)
    assert cs_map["[aileron]Aileron"] == 1
    assert cs_map["[flap]Flap"] == 2
    assert cs_map["[elevator]Elevator"] == 3
    assert cs_map["[rudder]Rudder"] == 4


def test_yduplicate_sign_map_uses_symmetric_flag():
    """gh-529: SgnDup factor is +1 for symmetric surfaces, -1 for
    antisymmetric (aileron pair)."""
    airplane = _canonical_4surface_airplane()
    signs = build_yduplicate_sign_map(airplane)
    assert signs["[aileron]Aileron"] == -1.0  # antisymmetric
    assert signs["[flap]Flap"] == 1.0
    assert signs["[elevator]Elevator"] == 1.0
    assert signs["[rudder]Rudder"] == 1.0


# ============================================================================
# geometry_hash
# ============================================================================


def test_geometry_hash_is_deterministic():
    """Same airplane built twice → identical hash."""
    h1 = compute_geometry_hash(_canonical_4surface_airplane())
    h2 = compute_geometry_hash(_canonical_4surface_airplane())
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


def test_geometry_hash_changes_when_xsecs_are_reordered():
    """gh-529: reordering xsec control surfaces produces a different hash
    so replay can reject the drift."""
    a = _canonical_4surface_airplane()
    b = _canonical_4surface_airplane()
    # Swap xsec order on the main wing.
    b.wings[0].xsecs = list(reversed(b.wings[0].xsecs))
    assert compute_geometry_hash(a) != compute_geometry_hash(b), (
        "Hash must distinguish reordered xsec lists"
    )


def test_geometry_hash_changes_when_a_surface_is_removed():
    a = _canonical_4surface_airplane()
    b = _canonical_4surface_airplane()
    # Drop the flap.
    b.wings[0].xsecs[1].control_surfaces = []
    assert compute_geometry_hash(a) != compute_geometry_hash(b)


def test_geometry_hash_changes_when_symmetric_flag_flips():
    """A flap toggled to antisymmetric is a different AVL geometry (the
    SgnDup factor flips), so the hash must change."""
    a = _canonical_4surface_airplane()
    b = _canonical_4surface_airplane()
    b.wings[0].xsecs[1].control_surfaces[0].symmetric = False
    assert compute_geometry_hash(a) != compute_geometry_hash(b)


# ============================================================================
# build_avl_artefact
# ============================================================================


def test_build_avl_artefact_populates_all_required_fields():
    airplane = _canonical_4surface_airplane()
    artefact = build_avl_artefact(
        airplane,
        alpha_deg=3.5,
        beta_deg=0.0,
        velocity_mps=22.0,
        x_cg_m=0.092,
        control_deflections_deg={"[elevator]Elevator": -2.0, "[flap]Flap": 0.0},
        mach=0.07,
        run_case_constraints={"C1": "bank=0", "C2": "velocity=22.0"},
        avl_version="3.40",
    )

    assert isinstance(artefact, AvlArtefact)
    # Snapshot
    assert artefact.index_snapshot.name_to_index["[aileron]Aileron"] == 1
    assert artefact.index_snapshot.yduplicate_sign["[aileron]Aileron"] == -1.0
    assert len(artefact.index_snapshot.geometry_hash) == 64
    # Run state
    assert artefact.run_state.alpha_deg == 3.5
    assert artefact.run_state.velocity_mps == 22.0
    assert artefact.run_state.x_cg_m == 0.092
    assert artefact.run_state.control_deflections_deg["[elevator]Elevator"] == -2.0
    assert artefact.run_state.run_case_constraints["C1"] == "bank=0"
    assert artefact.avl_version == "3.40"


def test_artefact_reverse_lookup_finds_control_name_for_index():
    airplane = _canonical_4surface_airplane()
    artefact = build_avl_artefact(
        airplane,
        alpha_deg=0.0,
        beta_deg=0.0,
        velocity_mps=20.0,
        x_cg_m=0.1,
    )
    assert artefact.control_name_for_index(1) == "[aileron]Aileron"
    assert artefact.control_name_for_index(99) is None


# ============================================================================
# verify_avl_replay
# ============================================================================


def test_verify_avl_replay_returns_none_when_geometry_unchanged():
    airplane = _canonical_4surface_airplane()
    artefact = build_avl_artefact(
        airplane,
        alpha_deg=1.0,
        beta_deg=0.0,
        velocity_mps=18.0,
        x_cg_m=0.1,
    )
    assert verify_avl_replay(airplane, artefact) is None


def test_verify_avl_replay_rejects_reordered_xsecs():
    """gh-529 critical: a reordered geometry must fail replay validation
    BEFORE AVL is invoked, so silent index mis-binding cannot happen."""
    airplane_at_capture = _canonical_4surface_airplane()
    artefact = build_avl_artefact(
        airplane_at_capture,
        alpha_deg=2.0,
        beta_deg=0.0,
        velocity_mps=20.0,
        x_cg_m=0.1,
    )

    airplane_now = _canonical_4surface_airplane()
    airplane_now.wings[0].xsecs = list(reversed(airplane_now.wings[0].xsecs))

    mismatch = verify_avl_replay(airplane_now, artefact)
    assert mismatch is not None
    assert mismatch.reason == "geometry_hash_mismatch"
    assert mismatch.expected == artefact.index_snapshot.geometry_hash
    assert mismatch.actual != artefact.index_snapshot.geometry_hash


def test_verify_avl_replay_rejects_added_surface():
    airplane_at_capture = _canonical_4surface_airplane()
    artefact = build_avl_artefact(
        airplane_at_capture,
        alpha_deg=0.0,
        beta_deg=0.0,
        velocity_mps=20.0,
        x_cg_m=0.1,
    )

    airplane_now = _canonical_4surface_airplane()
    # Add a new spoiler surface to a wing.
    airplane_now.wings[0].xsecs[0].control_surfaces.append(
        _cs("[spoiler]Spoiler", symmetric=True, hinge_point=0.5)
    )
    mismatch = verify_avl_replay(airplane_now, artefact)
    assert mismatch is not None
    assert mismatch.reason == "geometry_hash_mismatch"


# ============================================================================
# Schema sanity
# ============================================================================


def test_geometry_hash_field_enforces_sha256_length():
    """Pydantic schema rejects a too-short hash."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AvlIndexSnapshot(
            name_to_index={},
            yduplicate_sign={},
            captured_at="2026-05-15T00:00:00+00:00",
            geometry_hash="too-short",
        )


def test_run_state_round_trips_through_model_dump():
    state = AvlRunState(
        alpha_deg=2.5,
        beta_deg=-1.0,
        velocity_mps=21.0,
        mach=0.06,
        x_cg_m=0.085,
        control_deflections_deg={"[elevator]Elevator": -1.5},
        run_case_constraints={"C1": "bank=0"},
    )
    dumped = state.model_dump()
    assert dumped["alpha_deg"] == 2.5
    assert dumped["control_deflections_deg"]["[elevator]Elevator"] == -1.5
    # Re-parse must succeed
    re_parsed = AvlRunState.model_validate(dumped)
    assert re_parsed == state
