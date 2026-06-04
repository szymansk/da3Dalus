"""Regression test for gh-523: ``from-wingconfig`` must NOT silently
drop trailing-edge devices on tip-marked segments.

Before the fix, an aileron (or any TED) attached to a segment that
also carried ``tip_type`` was silently dropped on the way through
the converter chain — the wing was persisted with
``control_surface=None`` and ``trailing_edge_device=None`` while
the endpoint returned 201 Created. This is the silent-failure mode
gh-577 set out to eliminate.

Per the issue's option B (cleanest given the architectural mismatch
— ``WingConfiguration.add_tip_segment`` does not accept TEDs at
all), the fix is to refuse the input with 422 + a clear message
pointing at the user's options. The two tests exercise:

1. Tip-segment + TED → 422 with actionable detail (the buggy case
   from the issue).
2. Non-tip segment + asymmetric TED → 201 + round-trip preserves
   ``symmetric=False`` (the happy path).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


airfoil_path = str(
    (Path(__file__).resolve().parents[2] / "components" / "airfoils" / "mh32.dat").resolve()
)


def _post_wingconfig_with_asymmetric_ted(client: TestClient, aeroplane_id: str, wing_name: str):
    """POST a 1-segment wing with an aileron whose ``symmetric=False``."""
    wing_config = {
        "nose_pnt": [0, 0, 0],
        "symmetric": True,
        "segments": [
            {
                "root_airfoil": {
                    "airfoil": airfoil_path,
                    "chord": 200.0,
                    "incidence": 0.0,
                },
                "tip_airfoil": {
                    "airfoil": airfoil_path,
                    "chord": 150.0,
                    "incidence": 0.0,
                },
                "length": 1000.0,
                "sweep": 0.0,
                "number_interpolation_points": 20,
                "trailing_edge_device": {
                    "name": "aileron",
                    "rel_chord_root": 0.7,
                    "rel_chord_tip": 0.7,
                    "symmetric": False,
                    "positive_deflection_deg": 20.0,
                    "negative_deflection_deg": -10.0,
                },
            }
        ],
    }
    resp = client.post(
        f"/aeroplanes/{aeroplane_id}/wings/{wing_name}/from-wingconfig",
        json=wing_config,
    )
    assert resp.status_code == 201, resp.text


def _create_aeroplane(client: TestClient, name: str) -> str:
    resp = client.post("/aeroplanes", params={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture()
def client(client_and_db):
    c, _ = client_and_db
    yield c


class TestFromWingConfigAsymmetricTed:
    def test_asymmetric_ted_persisted_on_non_tip_segment(self, client):
        """gh-523 happy path: an aileron with symmetric=False on a
        regular (non-tip) segment must round-trip through
        ``POST /from-wingconfig`` + ``GET /wings/{name}``.
        """
        aid = _create_aeroplane(client, "gh-523-ailerons")
        _post_wingconfig_with_asymmetric_ted(client, aid, "main_wing")

        # GET back as ASB wing — the canonical persistence view.
        resp = client.get(f"/aeroplanes/{aid}/wings/main_wing")
        assert resp.status_code == 200, resp.text
        wing = resp.json()

        # Find xsecs that should carry the aileron. For a 1-segment
        # wing the TED spans root → tip; both endpoint xsecs must
        # reflect the asymmetric surface.
        asym_xsecs = [
            xs
            for xs in wing["x_secs"]
            if (xs.get("control_surface") is not None)
            or (xs.get("trailing_edge_device") is not None)
        ]
        assert asym_xsecs, (
            f"NO xsec carries the aileron — the TED was silently dropped. "
            f"x_secs payload: {wing['x_secs']}"
        )

        # Every xsec that carries the surface must report symmetric=False.
        for xs in asym_xsecs:
            cs = xs.get("control_surface")
            ted = xs.get("trailing_edge_device")
            if cs is not None:
                assert cs["symmetric"] is False, (
                    f"control_surface.symmetric should be False, got {cs}"
                )
            if ted is not None:
                assert ted["symmetric"] is False, (
                    f"trailing_edge_device.symmetric should be False, got {ted}"
                )

    def test_tip_segment_with_ted_rejected_with_422(self, client):
        """gh-523 buggy case: a tip-marked segment (tip_type=round)
        that carries a TED. The cad_designer's tip_segment is a
        cosmetic wing-end cap and architecturally cannot hold a
        control surface. Before the fix this was silently dropped;
        now it returns 422 with an actionable message.
        """
        aid = _create_aeroplane(client, "gh-523-tip-with-ted")
        wing_config = {
            "nose_pnt": [0, 0, 0],
            "symmetric": True,
            "segments": [
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 200.0, "incidence": 0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 150.0, "incidence": 0},
                    "length": 1000.0,
                    "sweep": 0.0,
                    "number_interpolation_points": 20,
                    "tip_type": "round",  # tip cap …
                    "trailing_edge_device": {  # … but also a TED → invalid combo
                        "name": "aileron",
                        "rel_chord_root": 0.7,
                        "rel_chord_tip": 0.7,
                        "symmetric": False,
                    },
                }
            ],
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/main_wing/from-wingconfig", json=wing_config)
        assert resp.status_code == 422, resp.text
        detail = resp.json().get("detail", "")
        # Message must call out the exact fields that conflict and
        # tell the user how to fix it.
        assert "tip_type" in detail
        assert "trailing_edge_device" in detail
        assert "non-tip" in detail or "remove" in detail

    def test_c172_pattern_split_into_aero_plus_tip_caps(self, client):
        """C172N-style wing done right: inner segment has the flap
        (symmetric), middle segment has the aileron (asymmetric), and
        a separate trailing segment is the rounded tip cap with no
        control surface. Both TEDs must survive the round trip.
        """
        aid = _create_aeroplane(client, "gh-523-c172-split")
        wing_config = {
            "nose_pnt": [0, 0, 0],
            "symmetric": True,
            "segments": [
                # inner segment: flap (symmetric)
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 1625.0, "incidence": 0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 1321.0, "incidence": 0},
                    "length": 3300.0,
                    "sweep": 0.0,
                    "number_interpolation_points": 20,
                    "trailing_edge_device": {
                        "name": "flap",
                        "rel_chord_root": 0.7,
                        "rel_chord_tip": 0.7,
                        "symmetric": True,
                    },
                },
                # middle segment: aileron (asymmetric), NO tip_type
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 1321.0, "incidence": 0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 1118.0, "incidence": 0},
                    "length": 2200.0,
                    "sweep": 0.0,
                    "number_interpolation_points": 20,
                    "trailing_edge_device": {
                        "name": "aileron",
                        "rel_chord_root": 0.7,
                        "rel_chord_tip": 0.7,
                        "symmetric": False,
                    },
                },
                # separate tip cap (cosmetic), no TED
                {
                    "root_airfoil": {"airfoil": airfoil_path, "chord": 1118.0, "incidence": 0},
                    "tip_airfoil": {"airfoil": airfoil_path, "chord": 600.0, "incidence": 0},
                    "length": 100.0,
                    "sweep": 0.0,
                    "number_interpolation_points": 10,
                    "tip_type": "round",
                },
            ],
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/main_wing/from-wingconfig", json=wing_config)
        assert resp.status_code == 201, resp.text
        wing = client.get(f"/aeroplanes/{aid}/wings/main_wing").json()

        # Locate xsecs by their surface name. For 3 xsecs (root / mid / tip)
        # the inner segment's TED lives on xsec[0]/xsec[1], the outer's on
        # xsec[1]/xsec[2]. We're tolerant of whichever convention the
        # converter picks — as long as BOTH surfaces are persisted.
        surfaces_by_name: dict[str, dict] = {}
        for xs in wing["x_secs"]:
            cs = xs.get("control_surface")
            ted = xs.get("trailing_edge_device")
            if cs is not None:
                # Surfaces carry a role tag like ``[other]aileron``;
                # strip it to match against the user-supplied name.
                name = cs.get("name", "").split("]")[-1] if cs.get("name") else None
                if name:
                    surfaces_by_name.setdefault(
                        name, {"control_surface": cs, "trailing_edge_device": ted}
                    )
            if ted is not None and ted.get("name"):
                surfaces_by_name.setdefault(
                    ted["name"],
                    {"control_surface": cs, "trailing_edge_device": ted},
                )

        assert "flap" in surfaces_by_name, f"flap dropped — surfaces={list(surfaces_by_name)}"
        assert "aileron" in surfaces_by_name, (
            f"aileron dropped — surfaces={list(surfaces_by_name)} (gh-523)"
        )

        flap_cs = surfaces_by_name["flap"]["control_surface"]
        aileron_cs = surfaces_by_name["aileron"]["control_surface"]
        assert flap_cs["symmetric"] is True
        assert aileron_cs["symmetric"] is False, (
            f"aileron.symmetric should be False, got {aileron_cs}"
        )

    def test_symmetric_ted_remains_symmetric(self, client):
        """Control case: a flap with symmetric=True keeps the flag."""
        aid = _create_aeroplane(client, "gh-523-flap-control")
        wing_config = {
            "nose_pnt": [0, 0, 0],
            "symmetric": True,
            "segments": [
                {
                    "root_airfoil": {
                        "airfoil": airfoil_path,
                        "chord": 200.0,
                        "incidence": 0.0,
                    },
                    "tip_airfoil": {
                        "airfoil": airfoil_path,
                        "chord": 150.0,
                        "incidence": 0.0,
                    },
                    "length": 1000.0,
                    "sweep": 0.0,
                    "number_interpolation_points": 20,
                    "trailing_edge_device": {
                        "name": "flap",
                        "rel_chord_root": 0.7,
                        "rel_chord_tip": 0.7,
                        "symmetric": True,
                        "positive_deflection_deg": 30.0,
                        "negative_deflection_deg": 0.0,
                    },
                }
            ],
        }
        resp = client.post(f"/aeroplanes/{aid}/wings/main_wing/from-wingconfig", json=wing_config)
        assert resp.status_code == 201, resp.text
        wing = client.get(f"/aeroplanes/{aid}/wings/main_wing").json()
        sym_xsecs = [
            xs
            for xs in wing["x_secs"]
            if (xs.get("control_surface") is not None)
            or (xs.get("trailing_edge_device") is not None)
        ]
        assert sym_xsecs, "flap should be persisted"
        for xs in sym_xsecs:
            cs = xs.get("control_surface")
            if cs is not None:
                assert cs["symmetric"] is True
