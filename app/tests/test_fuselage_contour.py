"""The optional point contour of a fuselage section (gh-1349, slice 1: format, backend, display).

A contour is the measured right half outline, ``[y, z]`` in metres relative to the section's
``xyz``, from the bottom centre to the top centre. It is display and CAD geometry; the solvers keep
the super-ellipse fit ``a``/``b``/``n``/``n_lower``. These tests use an in-memory SQLite database,
never the real one.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from app import schemas
from app.converters.model_schema_converters import _mirror_fuselage_schema_y
from app.models.aeroplanemodel import AeroplaneModel, FuselageModel
from app.services.aeroplane_clone_service import clone_aeroplane_subgraph


def half_ellipse(a: float, b: float, count: int = 13) -> list[list[float]]:
    """Right half of the ellipse (a, b), bottom centre to top centre; odd count hits y = a."""
    points = []
    for index in range(count):
        angle = -math.pi / 2 + math.pi * index / (count - 1)
        points.append([a * math.cos(angle), b * math.sin(angle)])
    points[0] = [0.0, -b]
    points[-1] = [0.0, b]
    return points


def section(x: float, a: float = 0.03, b: float = 0.05, contour=True, count: int = 13) -> dict:
    payload = {"xyz": [x, 0.0, 0.0], "a": a, "b": b, "n": 2.0}
    if contour:
        payload["contour"] = half_ellipse(a, b, count)
    return payload


def body(*sections: dict) -> dict:
    return {"name": "Rumpf", "x_secs": list(sections)}


# --------------------------------------------------------------------------- schema


class TestSectionSchema:
    def test_a_section_without_contour_is_unchanged(self):
        xsec = schemas.FuselageXSecSuperEllipseSchema(**section(0.0, contour=False))
        assert xsec.contour is None
        assert xsec.model_dump()["contour"] is None

    def test_a_valid_contour_is_kept_point_for_point(self):
        payload = section(0.0)
        xsec = schemas.FuselageXSecSuperEllipseSchema(**payload)
        assert [list(p) for p in xsec.contour] == payload["contour"]

    def test_fewer_than_eight_points_are_refused_at_the_contour(self):
        with pytest.raises(ValidationError) as caught:
            schemas.FuselageXSecSuperEllipseSchema(**section(0.0, count=7))
        (error,) = caught.value.errors()
        assert error["loc"] == ("contour",)
        assert "at least 8" in error["msg"]

    def test_a_point_on_the_left_half_is_refused_naming_the_point(self):
        payload = section(0.0)
        payload["contour"][4][0] = -0.001
        with pytest.raises(ValidationError, match=r"contour\[4\].*y >= 0"):
            schemas.FuselageXSecSuperEllipseSchema(**payload)

    def test_a_contour_from_top_to_bottom_is_refused(self):
        payload = section(0.0)
        payload["contour"].reverse()
        with pytest.raises(ValidationError, match="bottom centre"):
            schemas.FuselageXSecSuperEllipseSchema(**payload)

    def test_points_out_of_order_are_refused(self):
        payload = section(0.0)
        payload["contour"][3], payload["contour"][4] = payload["contour"][4], payload["contour"][3]
        with pytest.raises(ValidationError, match="turns back"):
            schemas.FuselageXSecSuperEllipseSchema(**payload)

    @pytest.mark.parametrize("bad", [math.nan, math.inf])
    def test_a_non_finite_point_is_refused(self, bad):
        payload = section(0.0)
        payload["contour"][2][1] = bad
        with pytest.raises(ValidationError):
            schemas.FuselageXSecSuperEllipseSchema(**payload)

    def test_a_point_needs_exactly_two_numbers(self):
        payload = section(0.0)
        payload["contour"][2] = [0.01, 0.02, 0.0]
        with pytest.raises(ValidationError):
            schemas.FuselageXSecSuperEllipseSchema(**payload)


class TestFuselageSchema:
    def test_no_contour_anywhere_is_valid(self):
        schemas.FuselageSchema(**body(section(0.0, contour=False), section(0.5, contour=False)))

    def test_contours_with_one_count_everywhere_are_valid(self):
        schemas.FuselageSchema(**body(section(0.0), section(0.5, a=0.02, b=0.04)))

    def test_a_section_without_contour_among_contours_is_refused(self):
        with pytest.raises(ValidationError, match=r"x_secs\[1\] has no contour"):
            schemas.FuselageSchema(**body(section(0.0), section(0.5, contour=False)))

    def test_different_point_counts_are_refused(self):
        with pytest.raises(ValidationError, match=r"x_secs\[1\] has a contour of 11 points"):
            schemas.FuselageSchema(**body(section(0.0), section(0.5, count=11)))


# --------------------------------------------------------------------------- converters


def test_the_mirrored_cad_copy_keeps_the_contour():
    fuselage = schemas.FuselageSchema(**body(section(0.0), section(0.5)))
    mirrored = _mirror_fuselage_schema_y(fuselage)
    # the half contour is relative to the section's own centre: mirroring the centre keeps it
    assert [xs.contour for xs in mirrored.x_secs] == [xs.contour for xs in fuselage.x_secs]


def test_the_model_round_trip_keeps_the_contour():
    fuselage = schemas.FuselageSchema(**body(section(0.0), section(0.5)))
    model = FuselageModel.from_dict(name="Rumpf", data=fuselage.model_dump())
    back = schemas.FuselageSchema.model_validate(model, from_attributes=True)
    assert back.x_secs[1].contour == fuselage.x_secs[1].contour


# --------------------------------------------------------------------------- REST


def _plane(client) -> str:
    return client.post("/aeroplanes", params={"name": "Contour"}).json()["id"]


def _points(contour) -> list[list[float]]:
    return [list(point) for point in contour]


def test_put_and_get_fuselage_keep_the_contour(client_and_db):
    client, _ = client_and_db
    plane_id = _plane(client)
    sent = body(section(0.0), section(0.5, a=0.02, b=0.04))
    assert client.put(f"/aeroplanes/{plane_id}/fuselages/Rumpf", json=sent).status_code == 201

    got = client.get(f"/aeroplanes/{plane_id}/fuselages/Rumpf").json()
    assert _points(got["x_secs"][1]["contour"]) == sent["x_secs"][1]["contour"]
    xsec = client.get(f"/aeroplanes/{plane_id}/fuselages/Rumpf/cross_sections/0").json()
    assert _points(xsec["contour"]) == sent["x_secs"][0]["contour"]


def test_a_fuselage_without_contours_reads_contour_null(client_and_db):
    client, _ = client_and_db
    plane_id = _plane(client)
    sent = body(section(0.0, contour=False), section(0.5, contour=False))
    assert client.put(f"/aeroplanes/{plane_id}/fuselages/Rumpf", json=sent).status_code == 201
    got = client.get(f"/aeroplanes/{plane_id}/fuselages/Rumpf").json()
    assert [xs["contour"] for xs in got["x_secs"]] == [None, None]
    assert [xs["a"] for xs in got["x_secs"]] == [0.03, 0.03]


def test_an_invalid_contour_is_a_422_at_the_contour(client_and_db):
    client, _ = client_and_db
    plane_id = _plane(client)
    sent = body(section(0.0), section(0.5, count=7))
    response = client.put(f"/aeroplanes/{plane_id}/fuselages/Rumpf", json=sent)
    assert response.status_code == 422
    (detail,) = response.json()["detail"]
    assert detail["loc"] == ["body", "x_secs", 1, "contour"]
    assert "at least 8" in detail["msg"]


def test_a_mixed_fuselage_is_a_422_naming_the_section(client_and_db):
    client, _ = client_and_db
    plane_id = _plane(client)
    sent = body(section(0.0), section(0.5, contour=False))
    response = client.put(f"/aeroplanes/{plane_id}/fuselages/Rumpf", json=sent)
    assert response.status_code == 422
    (detail,) = response.json()["detail"]
    assert detail["loc"] == ["body", "x_secs"]
    assert "x_secs[1] has no contour" in detail["msg"]


def test_updating_a_section_keeps_the_all_or_none_rule(client_and_db):
    client, _ = client_and_db
    plane_id = _plane(client)
    url = f"/aeroplanes/{plane_id}/fuselages/Rumpf"
    client.put(url, json=body(section(0.0), section(0.5)))

    stripped = client.put(f"{url}/cross_sections/1", json=section(0.5, contour=False))
    assert stripped.status_code == 422
    assert "x_secs[1] has no contour" in stripped.json()["detail"]

    edited = client.put(f"{url}/cross_sections/1", json=section(0.5, a=0.031))
    assert edited.status_code == 200
    stored = client.get(f"{url}/cross_sections/1").json()
    assert stored["a"] == 0.031
    assert _points(stored["contour"]) == section(0.5, a=0.031)["contour"]


def test_inserting_a_section_without_contour_into_a_contour_fuselage_is_refused(client_and_db):
    client, _ = client_and_db
    plane_id = _plane(client)
    url = f"/aeroplanes/{plane_id}/fuselages/Rumpf"
    client.put(url, json=body(section(0.0), section(0.5)))

    refused = client.post(f"{url}/cross_sections/1", json=section(0.25, contour=False))
    assert refused.status_code == 422
    assert "x_secs[1] has no contour" in refused.json()["detail"]
    other_count = client.post(f"{url}/cross_sections/-1", json=section(0.7, count=9))
    assert other_count.status_code == 422
    assert "x_secs[2] has a contour of 9 points" in other_count.json()["detail"]

    accepted = client.post(f"{url}/cross_sections/1", json=section(0.25))
    assert accepted.status_code == 201
    assert len(client.get(f"{url}/cross_sections").json()) == 3


def test_sections_of_a_fuselage_without_contours_are_edited_as_before(client_and_db):
    client, _ = client_and_db
    plane_id = _plane(client)
    url = f"/aeroplanes/{plane_id}/fuselages/Rumpf"
    client.put(url, json=body(section(0.0, contour=False), section(0.5, contour=False)))
    added = client.post(f"{url}/cross_sections/-1", json=section(0.7, contour=False))
    assert added.status_code == 201
    edited = client.put(f"{url}/cross_sections/0", json=section(0.0, a=0.04, contour=False))
    assert edited.status_code == 200


# --------------------------------------------------------------------------- clone


def test_cloning_an_aeroplane_copies_the_contours(client_and_db):
    client, session_factory = client_and_db
    plane_id = _plane(client)
    sent = body(section(0.0), section(0.5, a=0.02, b=0.04))
    client.put(f"/aeroplanes/{plane_id}/fuselages/Rumpf", json=sent)

    with session_factory() as db:
        source = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == plane_id).one()
        clone = clone_aeroplane_subgraph(
            db, source, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db.flush()
        cloned = db.query(FuselageModel).filter(FuselageModel.aeroplane_id == clone.id).one()
        contours = [_points(xs.contour) for xs in cloned.x_secs]
    assert contours == [xs["contour"] for xs in sent["x_secs"]]


# --------------------------------------------------------------------------- no fit warning


def test_a_contour_off_the_fit_is_not_a_design_warning(client_and_db):
    """The contour exists because the fit deviates; that is expected (maintainer 2026-11-04)."""
    client, _ = client_and_db
    plane_id = _plane(client)
    off = section(0.5)
    off["a"] = 0.033  # the fit is 3 mm wider than the contour
    assert (
        client.put(
            f"/aeroplanes/{plane_id}/fuselages/Rumpf", json=body(section(0.0), off)
        ).status_code
        == 201
    )
    warnings = client.get(f"/aeroplanes/{plane_id}/assumptions").json()["design_warnings"]
    assert warnings == []
