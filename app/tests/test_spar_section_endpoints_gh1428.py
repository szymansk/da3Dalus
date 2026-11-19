"""gh-1428: the spar endpoints take and return metres; the table stores mm (gh-402)."""

from __future__ import annotations

import pytest

from app.models.aeroplanemodel import WingXSecSpareModel
from app.tests.test_spar_and_ted_crud import _seed_wing

URL = "/aeroplanes/{aid}/wings/w/cross_sections/0/spars"


@pytest.fixture
def plane(client_and_db):
    client, session_factory = client_and_db
    with session_factory() as db:
        aid = _seed_wing(client, "spar_section", db=db)
    return client, session_factory, aid


def body(**extra) -> dict:
    return {
        "spare_support_dimension_width": 0.006,
        "spare_support_dimension_height": 0.016,
        "spare_position_factor": 0.3,
        "spare_start": 0.0,
        "spare_mode": "standard",
        "spare_vector": [0, 1, 0],
        "spare_origin": [0, 0, 0],
        **extra,
    }


def test_post_then_get_returns_the_section_in_metres_and_stores_mm(plane):
    client, session_factory, aid = plane
    section = {"shape": "tube", "outer_diameter": 0.016, "wall_thickness": 0.001}
    resp = client.post(URL.format(aid=aid), json=body(section=section, material="Carbon tube"))
    assert resp.status_code in (200, 201), resp.text
    spars = client.get(URL.format(aid=aid)).json()
    got = spars[-1]["section"]
    assert got["shape"] == "tube"
    assert got["outer_diameter"] == pytest.approx(0.016)
    assert got["wall_thickness"] == pytest.approx(0.001)
    assert spars[-1]["material"] == "Carbon tube"
    with session_factory() as db:
        row = (
            db.query(WingXSecSpareModel).filter(WingXSecSpareModel.material == "Carbon tube").one()
        )
        assert row.section["outer_diameter"] == pytest.approx(16.0)
        assert row.section["wall_thickness"] == pytest.approx(1.0)
        assert row.section["shape"] == "tube"


def test_put_replaces_and_clears_the_section(plane):
    client, _, aid = plane
    url = URL.format(aid=aid) + "/0"
    section = {"shape": "rod", "diameter": 0.01}
    assert client.put(url, json=body(section=section, material="m")).status_code == 200
    assert client.get(URL.format(aid=aid)).json()[0]["section"] == section
    assert client.put(url, json=body()).status_code == 200
    first = client.get(URL.format(aid=aid)).json()[0]
    assert first["section"] is None and first["material"] is None


def test_existing_spars_without_a_section_keep_working(plane):
    client, _, aid = plane
    (spar,) = client.get(URL.format(aid=aid)).json()
    assert spar["section"] is None and spar["material"] is None


def test_an_inadmissible_section_is_a_422(plane):
    client, _, aid = plane
    bad = {"shape": "tube", "outer_diameter": 0.016, "wall_thickness": 0.009}
    resp = client.post(URL.format(aid=aid), json=body(section=bad))
    assert resp.status_code == 422
