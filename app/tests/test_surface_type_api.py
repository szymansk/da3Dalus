"""gh-1187: the explicit wing role ``surface_type`` through REST, the service and the converters."""

from __future__ import annotations

import pytest
from app.core.exceptions import ValidationDomainError
from app.models.aeroplanemodel import WingModel
from app.schemas.aeroplaneschema import SurfaceType
from app.services import surface_type_service as sts
from app.tests.conftest import make_aeroplane

SURFACE_TYPES = [
    "main_wing",
    "horizontal_tail",
    "vertical_tail",
    "v_tail",
    "canard",
    "tandem_wing",
    "winglet",
]


def _geometry(surface_type: str | None, chord: float = 0.2, span: float = 0.5) -> dict:
    body = {
        "name": "ignored",
        "symmetric": True,
        "x_secs": [
            {"xyz_le": [0.0, 0.0, 0.0], "chord": chord, "twist": 0.0, "airfoil": "naca0012"},
            {"xyz_le": [0.0, span, 0.0], "chord": chord / 2, "twist": 0.0, "airfoil": "naca0012"},
        ],
    }
    if surface_type is not None:
        body["surface_type"] = surface_type
    return body


@pytest.fixture
def plane(client_and_db):
    client, session_factory = client_and_db
    with session_factory() as db:
        aeroplane = make_aeroplane(db)
        yield client, session_factory, str(aeroplane.uuid), aeroplane.id


def _put(client, plane_id: str, name: str, surface_type: str | None, **kw):
    return client.put(f"/aeroplanes/{plane_id}/wings/{name}", json=_geometry(surface_type, **kw))


# ── create / read ─────────────────────────────────────────────────────────────


def test_create_requires_surface_type(plane) -> None:
    client, _, plane_id, _ = plane
    response = _put(client, plane_id, "w", None)
    assert response.status_code == 422


def test_create_rejects_an_unknown_surface_type(plane) -> None:
    client, _, plane_id, _ = plane
    response = _put(client, plane_id, "w", "biplane_upper")
    assert response.status_code == 422


@pytest.mark.parametrize("surface_type", [t for t in SURFACE_TYPES if t != "main_wing"])
def test_every_non_main_role_round_trips(plane, surface_type: str) -> None:
    client, _, plane_id, _ = plane
    assert _put(client, plane_id, "w", surface_type).status_code == 201
    body = client.get(f"/aeroplanes/{plane_id}/wings/w").json()
    assert body["surface_type"] == surface_type
    assert body["surface_type_inferred"] is False


def test_aeroplane_read_carries_surface_type_per_wing(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    _put(client, plane_id, "Tail", "horizontal_tail")
    wings = client.get(f"/aeroplanes/{plane_id}").json()["wings"]
    assert {name: w["surface_type"] for name, w in wings.items()} == {
        "Main": "main_wing",
        "Tail": "horizontal_tail",
    }


# ── exactly one main wing ─────────────────────────────────────────────────────


def test_a_second_main_wing_is_rejected_with_422(plane) -> None:
    client, _, plane_id, _ = plane
    assert _put(client, plane_id, "A", "main_wing").status_code == 201
    response = _put(client, plane_id, "B", "main_wing")
    assert response.status_code == 422
    assert "main wing" in response.json()["detail"]


def test_deleting_the_only_main_wing_is_rejected_while_other_wings_remain(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    _put(client, plane_id, "Tail", "horizontal_tail")
    response = client.delete(f"/aeroplanes/{plane_id}/wings/Main")
    assert response.status_code == 422
    assert client.get(f"/aeroplanes/{plane_id}/wings/Main").status_code == 200


def test_deleting_the_last_wing_is_allowed(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    assert client.delete(f"/aeroplanes/{plane_id}/wings/Main").status_code == 200


def test_deleting_a_tail_is_allowed(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    _put(client, plane_id, "Tail", "horizontal_tail")
    assert client.delete(f"/aeroplanes/{plane_id}/wings/Tail").status_code == 200


def test_update_cannot_retype_the_only_main_wing(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    response = client.post(f"/aeroplanes/{plane_id}/wings/Main", json=_geometry("horizontal_tail"))
    assert response.status_code == 422


def test_update_keeps_the_role_when_geometry_changes(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    response = client.post(
        f"/aeroplanes/{plane_id}/wings/Main", json=_geometry("main_wing", chord=0.3)
    )
    assert response.status_code == 200
    assert client.get(f"/aeroplanes/{plane_id}/wings/Main").json()["surface_type"] == "main_wing"


# ── PATCH surface-type ────────────────────────────────────────────────────────


def _patch(client, plane_id: str, name: str, **body):
    return client.patch(f"/aeroplanes/{plane_id}/wings/{name}/surface-type", json=body)


def test_patch_retypes_a_tail(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    _put(client, plane_id, "Tail", "horizontal_tail")
    assert _patch(client, plane_id, "Tail", surface_type="canard").status_code == 200
    assert client.get(f"/aeroplanes/{plane_id}/wings/Tail").json()["surface_type"] == "canard"


def test_patch_to_second_main_wing_without_swap_is_422(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    _put(client, plane_id, "Tail", "horizontal_tail")
    response = _patch(client, plane_id, "Tail", surface_type="main_wing")
    assert response.status_code == 422


def test_patch_swaps_main_wing_atomically(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    _put(client, plane_id, "Tail", "horizontal_tail")
    response = _patch(
        client, plane_id, "Tail", surface_type="main_wing", former_main_becomes="tandem_wing"
    )
    assert response.status_code == 200
    roles = {
        name: client.get(f"/aeroplanes/{plane_id}/wings/{name}").json()["surface_type"]
        for name in ("Main", "Tail")
    }
    assert roles == {"Main": "tandem_wing", "Tail": "main_wing"}


def test_patch_swap_target_may_not_be_main_wing_again(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    _put(client, plane_id, "Tail", "horizontal_tail")
    response = _patch(
        client, plane_id, "Tail", surface_type="main_wing", former_main_becomes="main_wing"
    )
    assert response.status_code == 422


def test_patch_cannot_retype_the_only_main_wing(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    response = _patch(client, plane_id, "Main", surface_type="horizontal_tail")
    assert response.status_code == 422


def test_patch_unknown_wing_is_404(plane) -> None:
    client, _, plane_id, _ = plane
    assert _patch(client, plane_id, "Nope", surface_type="canard").status_code == 404


def test_patch_rejects_unknown_fields(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    assert _patch(client, plane_id, "Main", surface_type="main_wing", extra=1).status_code == 422


# ── inferred values: declared until confirmed ─────────────────────────────────


def _inferred_plane(client_and_db):
    """A plane whose two wings carry roles that are only migration proposals."""
    client, session_factory = client_and_db
    with session_factory() as db:
        aeroplane = make_aeroplane(db)
        plane_id = str(aeroplane.uuid)
    assert _put(client, plane_id, "Main", "main_wing").status_code == 201
    assert _put(client, plane_id, "Tail", "horizontal_tail").status_code == 201
    with session_factory() as db:
        for wing in db.query(WingModel).all():
            wing.surface_type_inferred = True
        db.commit()
    return client, plane_id


def test_inferred_roles_are_flagged_on_the_wing_and_declared_as_design_warnings(
    client_and_db,
) -> None:
    client, plane_id = _inferred_plane(client_and_db)
    assert client.get(f"/aeroplanes/{plane_id}/wings/Main").json()["surface_type_inferred"] is True
    summary = client.get(f"/aeroplanes/{plane_id}/assumptions").json()
    warnings = summary["design_warnings"]
    assert sorted(w["context"]["wing"] for w in warnings) == ["Main", "Tail"]
    assert {w["code"] for w in warnings} == {"SURFACE_TYPE_INFERRED"}
    assert {w["severity"] for w in warnings} == {"warning"}


def test_patch_with_the_current_value_confirms_and_clears_the_warning(client_and_db) -> None:
    client, plane_id = _inferred_plane(client_and_db)
    assert _patch(client, plane_id, "Tail", surface_type="horizontal_tail").status_code == 200
    assert client.get(f"/aeroplanes/{plane_id}/wings/Tail").json()["surface_type_inferred"] is False
    warnings = client.get(f"/aeroplanes/{plane_id}/assumptions").json()["design_warnings"]
    assert [w["context"]["wing"] for w in warnings] == ["Main"]


def test_saving_geometry_with_the_proposed_role_does_not_confirm_it(client_and_db) -> None:
    client, plane_id = _inferred_plane(client_and_db)
    response = client.post(f"/aeroplanes/{plane_id}/wings/Tail", json=_geometry("horizontal_tail"))
    assert response.status_code == 200
    assert client.get(f"/aeroplanes/{plane_id}/wings/Tail").json()["surface_type_inferred"] is True


def test_saving_geometry_with_a_different_role_is_the_users_decision(client_and_db) -> None:
    client, plane_id = _inferred_plane(client_and_db)
    response = client.post(f"/aeroplanes/{plane_id}/wings/Tail", json=_geometry("canard"))
    assert response.status_code == 200
    body = client.get(f"/aeroplanes/{plane_id}/wings/Tail").json()
    assert (body["surface_type"], body["surface_type_inferred"]) == ("canard", False)


# ── WingConfig paths ──────────────────────────────────────────────────────────


def _wingconfig(surface_type: str | None = None) -> dict:
    airfoil = "../components/airfoils/mh32.dat"
    body = {
        "segments": [
            {
                "root_airfoil": {"airfoil": airfoil, "chord": 150.0, "incidence": 0},
                "tip_airfoil": {"airfoil": airfoil, "chord": 120.0, "incidence": 0},
                "length": 500.0,
                "sweep": 10.0,
                "number_interpolation_points": 101,
            }
        ],
        "nose_pnt": [0, 0, 0],
        "symmetric": True,
    }
    if surface_type is not None:
        body["surface_type"] = surface_type
    return body


def test_from_wingconfig_requires_surface_type(plane) -> None:
    client, _, plane_id, _ = plane
    response = client.post(f"/aeroplanes/{plane_id}/wings/W/from-wingconfig", json=_wingconfig())
    assert response.status_code == 422


def test_from_wingconfig_stores_the_role(plane) -> None:
    client, _, plane_id, _ = plane
    response = client.post(
        f"/aeroplanes/{plane_id}/wings/W/from-wingconfig", json=_wingconfig("main_wing")
    )
    assert response.status_code == 201
    assert client.get(f"/aeroplanes/{plane_id}/wings/W").json()["surface_type"] == "main_wing"


def test_put_wingconfig_without_role_keeps_the_existing_role_and_flag(client_and_db) -> None:
    client, session_factory = client_and_db
    with session_factory() as db:
        plane_id = str(make_aeroplane(db).uuid)
    created = client.post(
        f"/aeroplanes/{plane_id}/wings/Tail/from-wingconfig", json=_wingconfig("horizontal_tail")
    )
    assert created.status_code == 201
    with session_factory() as db:
        db.query(WingModel).one().surface_type_inferred = True
        db.commit()
    response = client.put(f"/aeroplanes/{plane_id}/wings/Tail/wingconfig", json=_wingconfig())
    assert response.status_code == 200
    body = client.get(f"/aeroplanes/{plane_id}/wings/Tail").json()
    assert (body["surface_type"], body["surface_type_inferred"]) == ("horizontal_tail", True)


def test_put_wingconfig_creating_a_wing_requires_the_role(plane) -> None:
    client, _, plane_id, _ = plane
    response = client.put(f"/aeroplanes/{plane_id}/wings/New/wingconfig", json=_wingconfig())
    assert response.status_code == 422


def test_put_wingconfig_with_a_second_main_wing_is_rejected(plane) -> None:
    client, _, plane_id, _ = plane
    _put(client, plane_id, "Main", "main_wing")
    response = client.put(
        f"/aeroplanes/{plane_id}/wings/Other/wingconfig", json=_wingconfig("main_wing")
    )
    assert response.status_code == 422


# ── service-level helpers ─────────────────────────────────────────────────────


class _Wing:
    def __init__(self, name: str, surface_type, inferred: bool = False) -> None:
        self.name = name
        self.surface_type = surface_type
        self.surface_type_inferred = inferred


def test_assert_one_main_wing_accepts_no_wings_and_exactly_one() -> None:
    sts.assert_one_main_wing([])
    sts.assert_one_main_wing([SurfaceType.MAIN_WING, SurfaceType.HORIZONTAL_TAIL])
    sts.assert_one_main_wing(["main_wing"])


def test_assert_one_main_wing_rejects_none_when_wings_exist() -> None:
    with pytest.raises(ValidationDomainError):
        sts.assert_one_main_wing([SurfaceType.HORIZONTAL_TAIL])


def test_assert_one_main_wing_rejects_two() -> None:
    with pytest.raises(ValidationDomainError):
        sts.assert_one_main_wing(["main_wing", "main_wing"])


def test_wing_surface_type_handles_missing_and_enum_values() -> None:
    assert sts.wing_surface_type(_Wing("a", None)) is None
    assert sts.wing_surface_type(_Wing("a", SurfaceType.CANARD)) == SurfaceType.CANARD
    assert sts.wing_surface_type(_Wing("a", "v_tail")) == SurfaceType.V_TAIL


def test_wings_of_type_and_find_main_wing() -> None:
    wings = [_Wing("t", "horizontal_tail"), _Wing("m", "main_wing"), _Wing("v", "v_tail")]
    assert [w.name for w in sts.wings_of_type(wings, SurfaceType.V_TAIL)] == ["v"]
    assert sts.find_main_wing(wings).name == "m"
    assert sts.find_main_wing([_Wing("t", "horizontal_tail")]) is None
    assert sts.find_main_wing([]) is None


def test_surface_type_warnings_only_for_inferred_wings() -> None:
    warnings = sts.surface_type_warnings(
        [_Wing("a", "main_wing", True), _Wing("b", "canard", False), _Wing("c", None, True)]
    )
    assert [(w.context["wing"], w.context["surface_type"]) for w in warnings] == [
        ("a", "main_wing"),
        ("c", None),
    ]
    assert all(
        w.severity == "warning" and w.code == sts.SURFACE_TYPE_INFERRED_CODE for w in warnings
    )
