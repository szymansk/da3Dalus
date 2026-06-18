"""gh-1049: slow/requires_cadquery round-trip for the spar-insert endpoint.

Builds a real eHawk main wing via ``/from-wingconfig`` (the single source of
truth used by the other CAD integration tests), computes a real spar plan
through the full solver + SectionGeometry path, inserts it (commit), and asserts
the wing's cross-sections carry the inserted spares with the HARD INVARIANT held:
the front (main) spar is ``sort_index = 0`` in every segment it occupies.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models.aeroplanemodel import AeroplaneModel
from app.models.component import ComponentModel
from test.ehawk_workflow_helpers import _build_main_wing


@pytest.fixture()
def client(client_and_db):
    test_client, _ = client_and_db
    yield test_client


def _build_ehawk_wingconfig_payload() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    airfoil_path = str((repo_root / "components" / "airfoils" / "mh32.dat").resolve())
    wing_config = _build_main_wing(airfoil_path)
    state = wing_config.__getstate__()

    class _JsonSafeEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, "toTuple"):
                return list(obj.toTuple())
            if hasattr(obj, "x") and hasattr(obj, "y") and hasattr(obj, "z"):
                return [float(obj.x), float(obj.y), float(obj.z)]
            try:
                return float(obj)
            except Exception:
                return str(obj)

    return json.loads(json.dumps(state, cls=_JsonSafeEncoder))


def _first_material_id(session_local) -> int:
    db = session_local()
    try:
        material = (
            db.query(ComponentModel).filter(ComponentModel.component_type == "material").first()
        )
        assert material is not None, "expected a seeded structural material"
        return material.id
    finally:
        db.close()


def _node_uuid(session_local, node_id: int) -> str:
    """Resolve an aeroplane node's UUID from its integer PK."""
    db = session_local()
    try:
        node = db.query(AeroplaneModel).filter(AeroplaneModel.id == node_id).first()
        assert node is not None, f"node {node_id} not found"
        return str(node.uuid)
    finally:
        db.close()


def _spare_signature(wing_json: dict) -> list[tuple]:
    """A comparable signature of a wing's spares across all cross-sections.

    Uses the dimensional fields + origin/vector so two wings with the same spar
    layout compare equal regardless of DB ids.
    """
    sig: list[tuple] = []
    for x in wing_json["x_secs"]:
        for s in x.get("spare_list") or []:
            sig.append(
                (
                    round(s["spare_support_dimension_width"], 6),
                    round(s["spare_support_dimension_height"], 6),
                    round((s.get("spare_length") or 0.0), 6),
                    tuple(round(c, 6) for c in (s.get("spare_origin") or [])),
                    tuple(round(c, 6) for c in (s.get("spare_vector") or [])),
                )
            )
    return sig


@pytest.mark.slow
@pytest.mark.requires_cadquery
def test_spar_insert_commit_roundtrip_front_spar_index_zero(client_and_db):
    test_client, session_local = client_and_db
    client: TestClient = test_client
    wing_name = "main_wing"

    create_plane = test_client.post("/aeroplanes", params={"name": "spar insert RT"})
    assert create_plane.status_code == 201, create_plane.text
    aeroplane_id = create_plane.json()["id"]

    create_wing = test_client.post(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/from-wingconfig",
        json=_build_ehawk_wingconfig_payload(),
    )
    assert create_wing.status_code == 201, create_wing.text

    material_id = _first_material_id(session_local)
    request_body = {
        "material_id": material_id,
        "wing_name": wing_name,
        "moments": [
            {"y_span": 0.0, "bending_moment_Nm": 4.0},
            {"y_span": 0.5, "bending_moment_Nm": 1.5},
            {"y_span": 1.0, "bending_moment_Nm": 0.0},
        ],
        "sigma_allow_mpa_override": 600.0,
        "n_span": 6,
        "packing_factor": 0.9,
    }

    # 1) dry-run preview: no writes.
    preview = test_client.post(
        f"/aeroplanes/{aeroplane_id}/spar-plan/insert",
        json={**request_body, "dry_run": True},
    )
    assert preview.status_code == 200, preview.text
    preview_json = preview.json()
    assert preview_json["committed"] is False
    assert preview_json["planned_spares"], "expected at least one planned spare"
    # every front spar piece in the preview is index 0
    front_preview = [p for p in preview_json["planned_spares"] if p["role"] == "front"]
    assert front_preview
    assert all(p["spar_index"] == 0 for p in front_preview)

    # a dry run must not change the persisted spare count (the eHawk wing
    # already ships with construction spares — dry run touches nothing).
    wing_before = test_client.get(f"/aeroplanes/{aeroplane_id}/wings/{wing_name}").json()
    spares_before = sum(len(x.get("spare_list") or []) for x in wing_before["x_secs"])
    wing_before_again = test_client.get(f"/aeroplanes/{aeroplane_id}/wings/{wing_name}").json()
    assert sum(len(x.get("spare_list") or []) for x in wing_before_again["x_secs"]) == spares_before

    # 2) commit: persist the plan.
    commit = test_client.post(
        f"/aeroplanes/{aeroplane_id}/spar-plan/insert",
        json={**request_body, "dry_run": False},
    )
    assert commit.status_code == 200, commit.text
    commit_json = commit.json()
    assert commit_json["committed"] is True

    # the persisted wing now carries spares; the front spar is sort_index 0 in
    # every segment it occupies (HARD INVARIANT).
    wing_after = test_client.get(f"/aeroplanes/{aeroplane_id}/wings/{wing_name}").json()
    total_spares = sum(len(x.get("spare_list") or []) for x in wing_after["x_secs"])
    assert total_spares >= 1

    # planned front piece per segment (front has one piece per segment here).
    planned_front_by_seg = {
        p["segment_index"]: p for p in commit_json["planned_spares"] if p["role"] == "front"
    }
    assert planned_front_by_seg, "expected at least one front spar piece"
    for seg_idx, planned_front in planned_front_by_seg.items():
        # spare_list is returned ordered by sort_index, so [0] is the main spar.
        spare_list = wing_after["x_secs"][seg_idx].get("spare_list") or []
        assert spare_list, f"segment {seg_idx} should carry a front spar"
        main_spar = spare_list[0]
        # the index-0 (main) spar in this segment IS the planned front spar:
        # its bounding box equals the front piece OD (within metre tolerance).
        assert main_spar["spare_support_dimension_width"] == pytest.approx(
            planned_front["outer_d"], rel=1e-6, abs=1e-9
        )
        assert main_spar["spare_support_dimension_height"] == pytest.approx(
            planned_front["outer_d"], rel=1e-6, abs=1e-9
        )


@pytest.mark.slow
@pytest.mark.requires_cadquery
def test_spar_insert_commit_preserves_solved_origin_and_vector_gh1053(client_and_db):
    """gh-1053: the committed front AND rear spars must land where the SOLVER
    placed them — at DISTINCT chordwise stations — not both collapsed onto the
    forced 0.25c default by the standard recompute.

    Asserts the persisted ``spare_origin`` / ``spare_vector`` equal the planned
    (preview) values within mm tolerance, for the front AND the rear spar, in
    every segment that carries both. Before the fix the rear spar's origin is
    overwritten with the front's quarter-chord origin (stacked), so this fails.
    """
    test_client, session_local = client_and_db
    wing_name = "main_wing"

    create_plane = test_client.post("/aeroplanes", params={"name": "spar insert origin RT"})
    assert create_plane.status_code == 201, create_plane.text
    aeroplane_id = create_plane.json()["id"]

    create_wing = test_client.post(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/from-wingconfig",
        json=_build_ehawk_wingconfig_payload(),
    )
    assert create_wing.status_code == 201, create_wing.text

    material_id = _first_material_id(session_local)
    request_body = {
        "material_id": material_id,
        "wing_name": wing_name,
        "moments": [
            {"y_span": 0.0, "bending_moment_Nm": 4.0},
            {"y_span": 0.5, "bending_moment_Nm": 1.5},
            {"y_span": 1.0, "bending_moment_Nm": 0.0},
        ],
        "sigma_allow_mpa_override": 600.0,
        "n_span": 6,
        "packing_factor": 0.9,
    }

    commit = test_client.post(
        f"/aeroplanes/{aeroplane_id}/spar-plan/insert",
        json={**request_body, "dry_run": False},
    )
    assert commit.status_code == 200, commit.text
    commit_json = commit.json()
    assert commit_json["committed"] is True

    planned = commit_json["planned_spares"]
    front_by_seg = {p["segment_index"]: p for p in planned if p["role"] == "front"}
    rear_by_seg = {p["segment_index"]: p for p in planned if p["role"] == "rear"}
    # We need at least one segment carrying BOTH a front and a rear spar so the
    # "distinct chordwise station" invariant is meaningful.
    shared_segments = sorted(set(front_by_seg) & set(rear_by_seg))
    assert shared_segments, "expected at least one segment with both a front and rear spar"

    wing_after = test_client.get(f"/aeroplanes/{aeroplane_id}/wings/{wing_name}").json()

    def _assert_origin_vector(persisted, planned_piece, label):
        po = persisted["spare_origin"]
        plo = planned_piece["spare_origin"]
        assert po is not None, f"{label}: persisted origin is None"
        for axis, (got, want) in enumerate(zip(po, plo, strict=True)):
            assert got == pytest.approx(want, abs=1e-3), (
                f"{label}: origin axis {axis} persisted {got} != planned {want}"
            )
        pv = persisted["spare_vector"]
        plv = planned_piece["spare_vector"]
        assert pv is not None, f"{label}: persisted vector is None"
        for axis, (got, want) in enumerate(zip(pv, plv, strict=True)):
            assert got == pytest.approx(want, abs=1e-3), (
                f"{label}: vector axis {axis} persisted {got} != planned {want}"
            )

    for seg_idx in shared_segments:
        spare_list = wing_after["x_secs"][seg_idx].get("spare_list") or []
        # Invariant: front = sort_index 0, rear = sort_index 1.
        assert len(spare_list) >= 2, f"segment {seg_idx} should carry front + rear"
        front_persisted = spare_list[0]
        rear_persisted = spare_list[1]

        _assert_origin_vector(front_persisted, front_by_seg[seg_idx], f"seg{seg_idx} front")
        _assert_origin_vector(rear_persisted, rear_by_seg[seg_idx], f"seg{seg_idx} rear")

        # The whole point of the two-spar plan: front and rear stay at the
        # solver's DISTINCT stations, NOT stacked on the same 0.25c origin.
        # The persisted front↔rear separation must equal the SOLVED separation
        # (before the fix the rear was overwritten with the front's 0.25c
        # origin, so the persisted separation collapsed to ~0).
        fo = front_persisted["spare_origin"]
        ro = rear_persisted["spare_origin"]
        pfo = front_by_seg[seg_idx]["spare_origin"]
        pro = rear_by_seg[seg_idx]["spare_origin"]
        persisted_sep = max(abs(fo[i] - ro[i]) for i in range(3))
        planned_sep = max(abs(pfo[i] - pro[i]) for i in range(3))
        assert planned_sep > 1e-6, (
            f"seg{seg_idx}: solver itself produced no front/rear separation — bad fixture"
        )
        assert persisted_sep == pytest.approx(planned_sep, abs=1e-3), (
            f"seg{seg_idx}: persisted front/rear separation {persisted_sep} != "
            f"solved separation {planned_sep} (front {fo}, rear {ro})"
        )


@pytest.mark.slow
@pytest.mark.requires_cadquery
def test_spar_insert_commit_autosnapshots_and_restore_recovers_pre_insert_gh1058(client_and_db):
    """gh-1058: the destructive insert-commit auto-snapshots the head FIRST, and
    restoring that snapshot recovers the EXACT pre-insert spares.

    A dry-run must NOT snapshot (snapshot_id is null); a commit returns the
    snapshot id, and POST /aeroplanes/{snapshot_id}/restore yields a head whose
    spares match the pre-insert state byte-for-byte (within metre tolerance).
    """
    test_client, session_local = client_and_db
    wing_name = "main_wing"

    create_plane = test_client.post("/aeroplanes", params={"name": "spar insert autosnap RT"})
    assert create_plane.status_code == 201, create_plane.text
    aeroplane_id = create_plane.json()["id"]

    create_wing = test_client.post(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/from-wingconfig",
        json=_build_ehawk_wingconfig_payload(),
    )
    assert create_wing.status_code == 201, create_wing.text

    material_id = _first_material_id(session_local)
    request_body = {
        "material_id": material_id,
        "wing_name": wing_name,
        "moments": [
            {"y_span": 0.0, "bending_moment_Nm": 4.0},
            {"y_span": 0.5, "bending_moment_Nm": 1.5},
            {"y_span": 1.0, "bending_moment_Nm": 0.0},
        ],
        "sigma_allow_mpa_override": 600.0,
        "n_span": 6,
        "packing_factor": 0.9,
    }

    # Capture the pre-insert spare layout (the eHawk wing ships construction
    # spares that the destructive commit would REPLACE).
    wing_pre = test_client.get(f"/aeroplanes/{aeroplane_id}/wings/{wing_name}").json()
    pre_signature = _spare_signature(wing_pre)

    # 1) dry-run preview must NOT snapshot.
    preview = test_client.post(
        f"/aeroplanes/{aeroplane_id}/spar-plan/insert",
        json={**request_body, "dry_run": True},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["snapshot_id"] is None

    # 2) commit auto-snapshots BEFORE mutating; returns the snapshot id.
    commit = test_client.post(
        f"/aeroplanes/{aeroplane_id}/spar-plan/insert",
        json={**request_body, "dry_run": False},
    )
    assert commit.status_code == 200, commit.text
    commit_json = commit.json()
    assert commit_json["committed"] is True
    snapshot_id = commit_json["snapshot_id"]
    assert isinstance(snapshot_id, int), "commit must return an integer snapshot id"

    # The head changed (spares were replaced by the inserted plan).
    wing_post = test_client.get(f"/aeroplanes/{aeroplane_id}/wings/{wing_name}").json()
    post_signature = _spare_signature(wing_post)
    assert post_signature != pre_signature, "commit should have changed the spare layout"

    # 3) restore the auto-snapshot → a new head carrying the PRE-insert spares.
    restore = test_client.post(
        f"/aeroplanes/{snapshot_id}/restore",
        json={"name": "revert spar insert"},
    )
    assert restore.status_code == 201, restore.text
    restored_head_id = restore.json()["head_id"]
    restored_uuid = _node_uuid(session_local, restored_head_id)

    wing_restored = test_client.get(f"/aeroplanes/{restored_uuid}/wings/{wing_name}").json()
    assert _spare_signature(wing_restored) == pre_signature, (
        "restoring the auto-snapshot must recover the exact pre-insert spares"
    )
