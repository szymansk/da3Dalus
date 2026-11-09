"""Role and attachment of a fuselage body (gh-1355, slice 1).

Every body carries a ``role`` (default ``fuselage``) and optionally ``attached_to``, the name of
the body it sits on. A canopy needs a parent and lies within its parent's x range. These tests
use an in-memory SQLite database, never the real one.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app import schemas
from app.converters.model_schema_converters import (
    _fuselage_schemas_with_mirrors,
    _mirror_fuselage_schema_y,
    aeroplane_model_to_aeroplane_schema_async,
)
from app.models.aeroplanemodel import AeroplaneModel, FuselageModel
from app.services.aeroplane_clone_service import clone_aeroplane_subgraph


def section(x: float, z: float = 0.0, n_lower: float | None = None) -> dict:
    return {"xyz": [x, 0.0, z], "a": 0.03, "b": 0.05, "n": 2.0, "n_lower": n_lower}


def body(name: str, x0: float = 0.0, x1: float = 1.0, **fields) -> dict:
    return {"name": name, "x_secs": [section(x0), section(x1)], **fields}


def canopy(x0: float = 0.2, x1: float = 0.5, attached_to: str | None = "Rumpf") -> dict:
    """A canopy as the plan importer writes it: n_lower 1, centre at the joint height."""
    return {
        "name": "Haube",
        "role": "canopy",
        "attached_to": attached_to,
        "x_secs": [section(x0, 0.05, n_lower=1.0), section(x1, 0.05, n_lower=1.0)],
    }


def spinner(x0: float = -0.1, x1: float = 0.0, attached_to: str | None = "Rumpf") -> dict:
    """A tractor spinner (gh-1375): its back plate at the parent's first station."""
    return {
        "name": "Spinner",
        "role": "spinner",
        "attached_to": attached_to,
        "x_secs": [section(x0), section(x1)],
    }


# --------------------------------------------------------------------------- schema


class TestSchema:
    def test_role_defaults_to_fuselage_and_attached_to_to_none(self):
        fuselage = schemas.FuselageSchema(**body("Rumpf"))
        assert fuselage.role == schemas.BodyRole.FUSELAGE
        assert fuselage.attached_to is None

    def test_every_role_of_the_format_is_accepted(self):
        roles = {r.value for r in schemas.BodyRole}
        assert roles == {"fuselage", "canopy", "nacelle", "fairing", "pod", "spinner", "other"}

    def test_an_unknown_role_is_refused(self):
        payload = body("Rumpf", role="cockpit")
        with pytest.raises(ValidationError, match="role"):
            schemas.FuselageSchema(**payload)

    def test_the_model_round_trip_keeps_role_and_attached_to(self):
        fuselage = schemas.FuselageSchema(**canopy())
        model = FuselageModel.from_dict(name="Haube", data=fuselage.model_dump())
        back = schemas.FuselageSchema.model_validate(model, from_attributes=True)
        assert (back.role, back.attached_to) == (schemas.BodyRole.CANOPY, "Rumpf")


# --------------------------------------------------------------------------- mirrored copy


class TestMirroredCopy:
    def test_the_mirror_keeps_role_and_points_at_the_mirrored_parent(self):
        nacelle = schemas.FuselageSchema(**body("Gondel", role="nacelle", symmetric=True))
        fairing = schemas.FuselageSchema(
            **body("Verkleidung", role="fairing", attached_to="Gondel", symmetric=True)
        )
        mirrored = _mirror_fuselage_schema_y(fairing, mirrored_parents={"Gondel"})
        assert mirrored.name == "Verkleidung (mirror)"
        assert mirrored.role == schemas.BodyRole.FAIRING
        assert mirrored.attached_to == "Gondel (mirror)"
        assert _mirror_fuselage_schema_y(nacelle, mirrored_parents=set()).role == (
            schemas.BodyRole.NACELLE
        )

    def test_the_mirror_of_a_body_on_an_unmirrored_parent_keeps_the_parent(self):
        fairing = schemas.FuselageSchema(
            **body("Radverkleidung", role="fairing", attached_to="Rumpf", symmetric=True)
        )
        mirrored = _mirror_fuselage_schema_y(fairing, mirrored_parents=set())
        assert mirrored.attached_to == "Rumpf"

    def test_the_expansion_names_the_mirrored_parents(self):
        fuselages = {
            "Gondel": schemas.FuselageSchema(**body("Gondel", role="nacelle", symmetric=True)),
            "Verkleidung": schemas.FuselageSchema(
                **body("Verkleidung", role="fairing", attached_to="Gondel", symmetric=True)
            ),
        }
        expanded = _fuselage_schemas_with_mirrors(fuselages)
        assert [(f.name, f.attached_to) for f in expanded] == [
            ("Gondel", None),
            ("Gondel (mirror)", None),
            ("Verkleidung", "Gondel"),
            ("Verkleidung (mirror)", "Gondel (mirror)"),
        ]


# --------------------------------------------------------------------------- REST


def _plane(client) -> str:
    return client.post("/aeroplanes", params={"name": "Haube"}).json()["id"]


def _put(client, plane_id: str, payload: dict):
    return client.put(f"/aeroplanes/{plane_id}/fuselages/{payload['name']}", json=payload)


def _with_fuselage(client) -> str:
    plane_id = _plane(client)
    assert _put(client, plane_id, body("Rumpf")).status_code == 201
    return plane_id


def test_create_and_read_carry_role_and_attached_to(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    assert _put(client, plane_id, canopy()).status_code == 201

    got = client.get(f"/aeroplanes/{plane_id}/fuselages/Haube").json()
    assert (got["role"], got["attached_to"]) == ("canopy", "Rumpf")
    parent = client.get(f"/aeroplanes/{plane_id}/fuselages/Rumpf").json()
    assert (parent["role"], parent["attached_to"]) == ("fuselage", None)


def test_update_changes_role_and_attached_to(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    _put(client, plane_id, body("Gondel"))
    url = f"/aeroplanes/{plane_id}/fuselages/Gondel"
    sent = body("Gondel", role="nacelle", attached_to="Rumpf")
    assert client.post(url, json=sent).status_code == 200
    got = client.get(url).json()
    assert (got["role"], got["attached_to"]) == ("nacelle", "Rumpf")


def test_a_canopy_without_parent_is_a_422(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    response = _put(client, plane_id, canopy(attached_to=None))
    assert response.status_code == 422
    assert 'fuselages["Haube"].attached_to' in response.json()["detail"]
    assert "needs attached_to" in response.json()["detail"]


def test_a_canopy_on_a_canopy_is_a_422(client_and_db):
    """gh-1355 slice 2: the solvers fold every canopy into one parent that is no canopy."""
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    assert _put(client, plane_id, canopy()).status_code == 201
    hood = {**canopy(attached_to="Haube"), "name": "Haube2"}
    response = _put(client, plane_id, hood)
    assert response.status_code == 422
    assert 'fuselages["Haube2"].attached_to' in response.json()["detail"]
    assert "itself a canopy" in response.json()["detail"]


def test_an_unknown_parent_is_a_422(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    response = _put(client, plane_id, canopy(attached_to="Fuselage"))
    assert response.status_code == 422
    assert "'Fuselage', which is not a body of this aircraft" in response.json()["detail"]
    assert client.get(f"/aeroplanes/{plane_id}/fuselages").json() == ["Rumpf"]


def test_a_body_attached_to_itself_is_a_422(client_and_db):
    """The body takes the name of the path, so attached_to is compared with that name."""
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    payload = body("Other", attached_to="Pod")
    response = client.put(f"/aeroplanes/{plane_id}/fuselages/Pod", json=payload)
    assert response.status_code == 422
    assert "attached to itself" in response.json()["detail"]


def test_a_cycle_is_a_422(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    _put(client, plane_id, body("Gondel", attached_to="Rumpf"))
    url = f"/aeroplanes/{plane_id}/fuselages/Rumpf"
    response = client.post(url, json=body("Rumpf", attached_to="Gondel"))
    assert response.status_code == 422
    assert "cycle" in response.json()["detail"]
    assert client.get(url).json()["attached_to"] is None


def test_a_canopy_outside_its_parent_is_a_422_at_the_section(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    response = _put(client, plane_id, canopy(0.2, 1.3))
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert 'fuselages["Haube"].x_secs[1].xyz[0]' in detail
    assert "behind its parent 'Rumpf'" in detail


def test_shortening_the_parent_under_its_canopy_is_a_422(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    _put(client, plane_id, canopy())
    url = f"/aeroplanes/{plane_id}/fuselages/Rumpf"
    response = client.post(url, json=body("Rumpf", 0.3, 1.0))
    assert response.status_code == 422
    assert "ahead of its parent 'Rumpf'" in response.json()["detail"]


def test_a_section_edit_moving_the_canopy_out_is_a_422(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    _put(client, plane_id, canopy())
    url = f"/aeroplanes/{plane_id}/fuselages/Haube/cross_sections"
    moved = client.put(f"{url}/1", json=section(1.2, 0.05, n_lower=1.0))
    assert moved.status_code == 422
    added = client.post(f"{url}/-1", json=section(-0.1, 0.05, n_lower=1.0))
    assert added.status_code == 422
    inside = client.put(f"{url}/1", json=section(0.6, 0.05, n_lower=1.0))
    assert inside.status_code == 200


def test_a_parent_section_edit_or_delete_keeps_the_canopy_inside(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    _put(client, plane_id, canopy())
    url = f"/aeroplanes/{plane_id}/fuselages/Rumpf/cross_sections"
    assert client.put(f"{url}/1", json=section(0.4)).status_code == 422
    client.post(f"{url}/1", json=section(0.6))
    assert client.delete(f"{url}/0").status_code == 422
    assert client.delete(f"{url}/2").status_code == 200


def test_deleting_a_body_others_are_attached_to_is_a_409(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    _put(client, plane_id, canopy())
    response = client.delete(f"/aeroplanes/{plane_id}/fuselages/Rumpf")
    assert response.status_code == 409
    assert "'Haube'" in response.json()["detail"]
    assert client.delete(f"/aeroplanes/{plane_id}/fuselages/Haube").status_code == 200
    assert client.delete(f"/aeroplanes/{plane_id}/fuselages/Rumpf").status_code == 200


def test_bodies_without_role_behave_as_before(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    assert _put(client, plane_id, body("Strebe", 1.5, 2.5)).status_code == 201
    assert client.delete(f"/aeroplanes/{plane_id}/fuselages/Rumpf").status_code == 200


# --------------------------------------------------------------------------- clone


def test_cloning_an_aeroplane_copies_role_and_attached_to(client_and_db):
    client, session_factory = client_and_db
    plane_id = _with_fuselage(client)
    _put(client, plane_id, canopy())

    with session_factory() as db:
        source = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == plane_id).one()
        clone = clone_aeroplane_subgraph(
            db, source, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db.flush()
        cloned = db.query(FuselageModel).filter(FuselageModel.aeroplane_id == clone.id).all()
        fields = {f.name: (f.role, f.attached_to) for f in cloned}
    assert fields == {"Rumpf": ("fuselage", None), "Haube": ("canopy", "Rumpf")}


def test_the_aeroplane_schema_carries_both_fields(client_and_db):
    client, session_factory = client_and_db
    plane_id = _with_fuselage(client)
    _put(client, plane_id, canopy())
    with session_factory() as db:
        plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == plane_id).one()
        schema = aeroplane_model_to_aeroplane_schema_async(plane)
    assert schema.fuselages["Haube"].role == schemas.BodyRole.CANOPY
    assert schema.fuselages["Haube"].attached_to == "Rumpf"
    assert schema.fuselages["Rumpf"].role == schemas.BodyRole.FUSELAGE


# --------------------------------------------------------------------------- spinner (gh-1375)


def test_a_spinner_round_trip_keeps_role_and_attached_to(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    assert _put(client, plane_id, spinner()).status_code == 201
    got = client.get(f"/aeroplanes/{plane_id}/fuselages/Spinner").json()
    assert (got["role"], got["attached_to"]) == ("spinner", "Rumpf")
    assert [xs["xyz"][0] for xs in got["x_secs"]] == [-0.1, 0.0]


def test_a_pusher_spinner_is_accepted(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    assert _put(client, plane_id, spinner(1.0, 1.1)).status_code == 201


def test_a_spinner_without_parent_is_a_422(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    response = _put(client, plane_id, spinner(attached_to=None))
    assert response.status_code == 422
    assert 'fuselages["Spinner"].attached_to' in response.json()["detail"]
    assert "is a spinner and needs attached_to" in response.json()["detail"]
    assert client.get(f"/aeroplanes/{plane_id}/fuselages").json() == ["Rumpf"]


def test_a_spinner_on_a_canopy_is_a_422(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    assert _put(client, plane_id, canopy()).status_code == 201
    response = _put(client, plane_id, spinner(0.1, 0.2, attached_to="Haube"))
    assert response.status_code == 422
    assert 'fuselages["Spinner"].attached_to' in response.json()["detail"]
    assert "'Haube', a canopy" in response.json()["detail"]


def test_a_spinner_on_a_spinner_is_a_422(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    assert _put(client, plane_id, spinner()).status_code == 201
    cap = {**spinner(-0.2, -0.1, attached_to="Spinner"), "name": "Cap"}
    response = _put(client, plane_id, cap)
    assert response.status_code == 422
    assert 'fuselages["Cap"].attached_to' in response.json()["detail"]
    assert "'Spinner', a spinner" in response.json()["detail"]


def test_a_spinner_not_adjoining_its_parent_is_a_422_at_the_section(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    response = _put(client, plane_id, spinner(-0.1, -0.02))
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert 'fuselages["Spinner"].x_secs[1].xyz[0]' in detail
    assert "adjoins one end of its parent 'Rumpf'" in detail


def test_moving_the_parent_nose_away_from_its_spinner_is_a_422(client_and_db):
    client, _ = client_and_db
    plane_id = _with_fuselage(client)
    assert _put(client, plane_id, spinner()).status_code == 201
    url = f"/aeroplanes/{plane_id}/fuselages/Rumpf"
    response = client.post(url, json=body("Rumpf", 0.05, 1.0))
    assert response.status_code == 422
    assert "spinner 'Spinner'" in response.json()["detail"]
