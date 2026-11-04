"""gh-1146 / Q-FD-3 ③: the fuselage aspect-ratio band ``2a/2b ∈ [0.3, 3.0]`` as a DesignWarning."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import fuselage_plausibility_service as fps
from app.tests.conftest import make_aeroplane


def _xs(a: float, b: float) -> SimpleNamespace:
    return SimpleNamespace(a=a, b=b)


def _body(name: str, *sections: tuple[float, float]) -> SimpleNamespace:
    return SimpleNamespace(name=name, x_secs=[_xs(a, b) for a, b in sections])


class TestBand:
    def test_band_is_the_decided_one(self):
        assert fps.FUSELAGE_ASPECT_RATIO_BAND == (0.3, 3.0)

    @pytest.mark.parametrize("a, b", [(0.02, 0.02), (0.0226, 0.042), (0.03, 0.01), (0.01, 0.0333)])
    def test_inside_the_band_no_warning(self, a, b):
        assert fps.fuselage_aspect_ratio_warnings([_body("Body", (0.0, 0.0), (a, b))]) == []

    def test_too_wide_body_is_declared(self):
        (warning,) = fps.fuselage_aspect_ratio_warnings([_body("Flat", (0.0, 0.0), (0.08, 0.02))])
        assert warning.code == fps.FUSELAGE_ASPECT_RATIO_OUTSIDE_BAND_CODE
        assert warning.severity == "warning"
        assert warning.category == "substituted_assumption"
        assert warning.context["fuselage"] == "Flat"
        assert warning.context["width_over_height"] == pytest.approx(4.0)
        assert warning.context["max_width_m"] == pytest.approx(0.16)
        assert warning.context["max_height_m"] == pytest.approx(0.04)
        assert warning.context["band"] == [0.3, 3.0]
        assert "Flat" in warning.message

    def test_too_tall_body_is_declared(self):
        (warning,) = fps.fuselage_aspect_ratio_warnings([_body("Tall", (0.01, 0.05))])
        assert warning.context["width_over_height"] == pytest.approx(0.2)

    def test_ratio_uses_the_largest_section_of_each_axis(self):
        # Narrow nose and tall fin root: each axis is judged by its own maximum.
        body = _body("Pod", (0.03, 0.005), (0.01, 0.03))
        assert fps.fuselage_aspect_ratio_warnings([body]) == []

    def test_one_warning_per_offending_fuselage(self):
        bodies = [_body("Ok", (0.02, 0.02)), _body("Flat", (0.1, 0.01)), _body("Tall", (0.01, 0.1))]
        names = [w.context["fuselage"] for w in fps.fuselage_aspect_ratio_warnings(bodies)]
        assert names == ["Flat", "Tall"]

    @pytest.mark.parametrize("sections", [[], [(0.0, 0.0)], [(0.02, 0.0)], [(0.0, 0.02)]])
    def test_body_without_area_has_no_ratio(self, sections):
        # Zero-area bodies are dropped by the degenerate guards (gh-790, gh-804); no ratio exists.
        assert fps.fuselage_aspect_ratio_warnings([_body("Ribbon", *sections)]) == []

    def test_none_x_secs_is_an_empty_body(self):
        assert fps.fuselage_aspect_ratio_warnings([SimpleNamespace(name="E", x_secs=None)]) == []


def _fuselage_body(a: float, b: float) -> dict:
    return {
        "name": "ignored",
        "x_secs": [
            {"xyz": [0.0, 0.0, 0.0], "a": 0.0, "b": 0.0, "n": 2.0},
            {"xyz": [0.2, 0.0, 0.0], "a": a, "b": b, "n": 2.0},
            {"xyz": [0.5, 0.0, 0.0], "a": 0.0, "b": 0.0, "n": 2.0},
        ],
    }


def test_assumptions_summary_declares_an_implausible_fuselage(client_and_db) -> None:
    client, session_factory = client_and_db
    with session_factory() as db:
        plane_id = str(make_aeroplane(db).uuid)
    put = client.put(f"/aeroplanes/{plane_id}/fuselages/Flat", json=_fuselage_body(0.1, 0.02))
    assert put.status_code == 201, put.text
    put = client.put(f"/aeroplanes/{plane_id}/fuselages/Round", json=_fuselage_body(0.02, 0.02))
    assert put.status_code == 201, put.text

    warnings = client.get(f"/aeroplanes/{plane_id}/assumptions").json()["design_warnings"]

    assert [w["context"]["fuselage"] for w in warnings] == ["Flat"]
    assert warnings[0]["code"] == "FUSELAGE_ASPECT_RATIO_OUTSIDE_BAND"
    assert warnings[0]["severity"] == "warning"
