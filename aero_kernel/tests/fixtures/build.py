"""Builder of the fixture canon model ``flight_canon.json`` (ARCHITECTURE ch. 8.9).

Hand-authored content in the normalised model shape; the builder only adds the content hash.
Regenerate with ``python -m aero_kernel.tests.fixtures.build``; a test fails while the committed
JSON differs from the built text.
"""

import json
from pathlib import Path
from typing import Any

from aero_kernel.canon.model import Namespace, compute_content_hash
from aero_kernel.tests.canon_builders import world_taxonomy
from pydantic import TypeAdapter

# ``Any`` in this module is the raw-JSON boundary: the entries below are hand-written JSON-shaped
# dicts that the canon model types validate (and normalise) before anything is written.
FIXTURE_PATH = Path(__file__).resolve().parent / "flight_canon.json"


def q(symbol: str, unit: str, role: str, type_: str = "scalar", **extra: Any) -> dict[str, Any]:
    """A quantity entry of the model."""
    return {"symbol": symbol, "unit": unit, "role": role, "type": type_, **extra}


def app(id_: str, bind: dict[str, Any], produce: dict[str, Any], **extra: Any) -> dict[str, Any]:
    """An application entry of the model."""
    return {"id": id_, "bind": bind, "produce": produce, **extra}


def const(value: float, source: str) -> dict[str, Any]:
    """A constant binding with its source."""
    return {"const": value, "source": source}


LOAD_FACTOR_SOURCE = "definition of the load factor n = L/W; straight level flight means L = W"
quantities = {
    "airplane": q("airplane", "1", "input", "airplane"),
    "aircraft-mass": q("m", "kg", "input", positive=True),
    "gravity": q(
        "g",
        "m/s^2",
        "input",
        positive=True,
    ),
    "air-density": q(
        "rho",
        "kg/m^3",
        "input",
        positive=True,
    ),
    "flap-deflection-landing": q("delta_f_ldg", "deg", "input"),
    "cruise-speed-target": q("V_c", "m/s", "target", positive=True),
    "approach-speed-margin-target": q("k_S_app", "1", "target"),
    "airplane-landing": q("airplane_ldg", "1", "derived", "airplane"),
    "stall-speed": q("V_S", "m/s", "output"),
    "stall-speed-landing": q("V_S_ldg", "m/s", "output"),
    "max-lift-coefficient": q("C_L_max", "1", "derived"),
    "max-lift-coefficient-landing": q("C_L_max_ldg", "1", "derived"),
    "inverted-max-lift-coefficient": q("C_L_max_inv", "1", "derived"),
    "polar-stall": q("polar_S", "1", "output", "polar"),
    "approach-speed": q("V_app", "m/s", "output"),
    "neutral-point": q("x_np", "m", "output", uncertainty="interval"),
    "roll-rate-cruise": q("p_c", "deg/s", "output"),
    "max-mass-level-flight": q("m_max_level", "kg", "output"),
    "butterfly-stall-speed-curve": q("V_S0(s)", "m/s", "output", "curve"),
    "butterfly-speed-range": q("V_range", "m/s", "output", "curve_pair"),
}

defaults = {
    "gravity": {
        "value": 9.80665,
        "unit": "m/s^2",
        "basis": "standard",
        "source": "ISO 80000-3, standard acceleration of gravity",
        "regime": "RC and UAV, sea level",
    },
    "air-density": {
        "value": 1.225,
        "unit": "kg/m^3",
        "basis": "standard",
        "source": "U.S. Standard Atmosphere 1976, sea-level density",
        "regime": "RC and UAV, sea level",
    },
    "approach-speed-margin-target": {
        "value": 1.3,
        "unit": "1",
        "basis": "sourced",
        "source": "Sadraey 2013, ch. 10: approach speed 1.3 V_S (fixture value)",
        "regime": "RC and UAV, fixture value",
    },
}


stall_inputs = {
    "airplane": "calc:airplane",
    "m": "calc:aircraft-mass",
    "g": "calc:gravity",
    "n_load": None,
    "rho": "calc:air-density",
}
stall_outputs = {"v_s": None, "cl_max": None, "polar": None}


def stall_bind(n: float, airplane: str = "calc:airplane") -> dict[str, Any]:
    """Bind the inputs of ``stall-speed``: the load factor ``n`` as a sourced constant."""
    return {
        "airplane": airplane,
        "m": "calc:aircraft-mass",
        "g": "calc:gravity",
        "n_load": const(n, LOAD_FACTOR_SOURCE),
        "rho": "calc:air-density",
    }


formulas = {
    "airplane-configuration": {
        "kind": "procedure",
        "tool": "GEO",
        "cost": "instant",
        "inputs": {"airplane": "calc:airplane", "flap_deflection": "calc:flap-deflection-landing"},
        "outputs": {"airplane_cfg": "calc:airplane-landing"},
        "optional": ["flap_deflection"],
        "applications": [
            app(
                "default",
                {"airplane": "calc:airplane", "flap_deflection": "calc:flap-deflection-landing"},
                {"airplane_cfg": "calc:airplane-landing"},
            )
        ],
    },
    "stall-speed": {
        "kind": "optimization",
        "tool": "OPT",
        "cost": "seconds",
        "inputs": stall_inputs,
        "outputs": stall_outputs,
        "applications": [
            app(
                "clean",
                stall_bind(1),
                {
                    "v_s": "calc:stall-speed",
                    "cl_max": "calc:max-lift-coefficient",
                    "polar": "calc:polar-stall",
                },
            ),
            app(
                "landing",
                stall_bind(1, "calc:airplane-landing"),
                {
                    "v_s": "calc:stall-speed-landing",
                    "cl_max": "calc:max-lift-coefficient-landing",
                    "polar": None,
                },
            ),
            app(
                "inverted",
                stall_bind(-1),
                {"v_s": None, "cl_max": "calc:inverted-max-lift-coefficient", "polar": None},
            ),
        ],
        "preconditions": [
            {"id": "rho_at_evaluation_altitude", "parameter": "rho", "on_violation": "warning"},
            {
                "id": "landing_configuration_given",
                "parameter": "airplane",
                "on_violation": "warning",
                "applications": ["landing"],
            },
        ],
        "postconditions": [
            {
                "id": "cl_max_at_stall_reynolds_number",
                "parameter": "cl_max",
                "on_violation": "error",
            },
            {
                "id": "optimum_at_first_cl_peak",
                "parameter": "cl_max",
                "on_violation": "error",
                "applications": ["clean", "landing"],
            },
            {
                "id": "alpha_range_past_inverted_stall",
                "parameter": "polar",
                "on_violation": "error",
                "applications": ["inverted"],
            },
        ],
    },
    "speed-from-stall-margin": {
        "kind": "rating",
        "tool": "APP",
        "cost": "instant",
        "inputs": {"v_s_cfg": None, "k_s": None},
        "outputs": {"v": None},
        "applications": [
            app(
                "approach",
                {"v_s_cfg": "calc:stall-speed-landing", "k_s": "calc:approach-speed-margin-target"},
                {"v": "calc:approach-speed"},
            )
        ],
    },
    "neutral-point": {
        "kind": "procedure",
        "tool": "AVL",
        "cost": "seconds",
        "inputs": {
            "airplane": "calc:airplane",
            "m": "calc:aircraft-mass",
            "g": "calc:gravity",
            "rho": "calc:air-density",
        },
        "outputs": {"x_np": "calc:neutral-point"},
        "applications": [
            app(
                "default",
                {
                    "airplane": "calc:airplane",
                    "m": "calc:aircraft-mass",
                    "g": "calc:gravity",
                    "rho": "calc:air-density",
                },
                {"x_np": "calc:neutral-point"},
            )
        ],
        "uncertainty": "interval",
        "worlds": ["textbook", "pappas", "avl"],
    },
    "roll-rate-cruise": {
        "kind": "procedure",
        "tool": "AB",
        "cost": "seconds",
        "inputs": {"airplane": "calc:airplane", "v": "calc:cruise-speed-target"},
        "outputs": {"p": "calc:roll-rate-cruise"},
        "applications": [
            app(
                "cruise",
                {"airplane": "calc:airplane", "v": "calc:cruise-speed-target"},
                {"p": "calc:roll-rate-cruise"},
                when="has_aileron",
                given=["calc:cruise-speed-target"],
            )
        ],
    },
    "max-mass-level-flight": {
        "kind": "optimization",
        "tool": "OPT",
        "cost": "minutes",
        "inputs": {
            "airplane": "calc:airplane",
            "m_current": "calc:aircraft-mass",
            "g": "calc:gravity",
            "rho": "calc:air-density",
        },
        "outputs": {"m_max_level": "calc:max-mass-level-flight"},
        "applications": [
            app(
                "default",
                {
                    "airplane": "calc:airplane",
                    "m_current": "calc:aircraft-mass",
                    "g": "calc:gravity",
                    "rho": "calc:air-density",
                },
                {"m_max_level": "calc:max-mass-level-flight"},
            )
        ],
        "embeds": ["calc:stall-speed.clean"],
        "variables": ["calc:aircraft-mass"],
        "embeds_closure": ["calc:stall-speed.clean"],
    },
    "butterfly-approach": {
        "kind": "optimization",
        "tool": "OPT",
        "cost": "minutes",
        "inputs": {
            "airplane": None,
            "m": "calc:aircraft-mass",
            "g": "calc:gravity",
            "rho": "calc:air-density",
        },
        "outputs": {
            "v_s0_curve": "calc:butterfly-stall-speed-curve",
            "v_range": "calc:butterfly-speed-range",
        },
        "applications": [
            app(
                "crow",
                {
                    "airplane": "calc:airplane-landing",
                    "m": "calc:aircraft-mass",
                    "g": "calc:gravity",
                    "rho": "calc:air-density",
                },
                {
                    "v_s0_curve": "calc:butterfly-stall-speed-curve",
                    "v_range": "calc:butterfly-speed-range",
                },
                when="has_separate_flap_and_aileron",
            )
        ],
        "postconditions": [
            {"id": "optimum_at_first_cl_peak", "parameter": "v_s0_curve", "on_violation": "error"}
        ],
    },
}


def build_flight_canon() -> str:
    """Return the text of ``flight_canon.json``: sorted keys, two-space indent, final newline."""
    namespaces: dict[str, Any] = {
        "calc": {
            "quantities": quantities,
            "formulas": formulas,
            "defaults": defaults,
            "taxonomy": world_taxonomy({"formulas": formulas}),
        }
    }
    parsed = TypeAdapter(dict[str, Namespace]).validate_python(namespaces)
    # The model file holds the normalised form: every absent optional field is written out.
    normalised = {name: namespace.model_dump(mode="json") for name, namespace in parsed.items()}
    model = {
        "schema_version": 1,
        "content_hash": compute_content_hash(parsed),
        "importer_version": "0.0.0-fixture",
        "namespaces": normalised,
    }
    return json.dumps(model, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    FIXTURE_PATH.write_text(build_flight_canon(), encoding="utf-8")
