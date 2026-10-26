"""Builders of small valid canon-model dicts for the canon tests."""

import copy
from typing import Any

# ``Any`` below is the raw-JSON boundary: these dicts are hand-edited JSON documents that the
# tests mutate before the canon model validates them; the model types are the typed side.
from aero_kernel.canon.model import Namespace, compute_content_hash
from pydantic import TypeAdapter

_NAMESPACES = TypeAdapter(dict[str, Namespace])


def base_namespaces() -> dict[str, Any]:
    """Return the ``namespaces`` of a minimal valid model: weight from mass and gravity."""
    return {
        "calc": {
            "quantities": {
                "aircraft-mass": {
                    "symbol": "m",
                    "unit": "kg",
                    "role": "input",
                    "type": "scalar",
                    "positive": True,
                },
                "gravity": {
                    "symbol": "g",
                    "unit": "m/s^2",
                    "role": "input",
                    "type": "scalar",
                    "positive": True,
                },
                "weight": {"symbol": "W", "unit": "N", "role": "output", "type": "scalar"},
            },
            "defaults": {
                "gravity": {
                    "value": 9.80665,
                    "unit": "m/s^2",
                    "basis": "standard",
                    "source": "ISO 80000-3",
                    "regime": "RC and UAV, sea level",
                }
            },
            "formulas": {
                "weight-from-mass": {
                    "kind": "law",
                    "tool": "APP",
                    "cost": "instant",
                    "inputs": {"m": "calc:aircraft-mass", "g": "calc:gravity"},
                    "outputs": {"w": "calc:weight"},
                    "applications": [
                        {
                            "id": "default",
                            "bind": {"m": "calc:aircraft-mass", "g": "calc:gravity"},
                            "produce": {"w": "calc:weight"},
                        }
                    ],
                }
            },
        }
    }


def world_taxonomy(content: dict[str, Any]) -> dict[str, Any]:
    """A taxonomy that maps every world of the formulas to the tool of its formula.

    A convenience for hand-made test models: the canon states the tool of each world in
    ``taxonomy.yaml``, and a model whose formula has a world the taxonomy lacks is invalid.
    """
    worlds: dict[str, str] = {}
    for formula in content["formulas"].values():
        for world in formula.get("worlds", ()):
            worlds.setdefault(world, formula["tool"])
    tools = sorted(set(worlds.values()))
    return {
        "tools": [{"id": tool, "name": tool} for tool in tools],
        "worlds": [{"id": world, "tool": tool} for world, tool in worlds.items()],
    }


GEOMETRY_RULES: dict[str, Any] = {
    "minimum-sections": {
        "applies_to": {"quantity": "airplane"},
        "kind": "input",
        "on_violation": "error",
        "criterion": "A wing and a fuselage have at least min_sections sections.",
        "codes": ["too_few_sections"],
        "parameters": {
            "min_sections": {
                "value": 2.0,
                "unit": "1",
                "basis": "definition",
                "status": "adopted",
                "source": "a lofted surface is defined by at least two sections",
                "regime": "regime-independent",
            }
        },
    },
    "airfoil-resolvable": {
        "applies_to": {"quantity": "airplane"},
        "kind": "input",
        "on_violation": "error",
        "criterion": "A contour has at least min_contour_points points.",
        "codes": ["invalid_airfoil_contour"],
        "parameters": {
            "min_contour_points": {
                "value": 3.0,
                "unit": "1",
                "basis": "definition",
                "status": "adopted",
                "source": "three points are the least that enclose an area",
                "regime": "regime-independent",
            }
        },
    },
    "one-main-wing": {
        "applies_to": {"quantity": "airplane"},
        "kind": "input",
        "on_violation": "error",
        "criterion": "The airplane has exactly required_main_wings main wings.",
        "codes": ["main_wing_count"],
        "parameters": {
            "required_main_wings": {
                "value": 1.0,
                "unit": "1",
                "basis": "definition",
                "status": "adopted",
                "source": "one reference wing per airplane",
                "regime": "regime-independent",
            }
        },
    },
    "main-wing-spanwise-extent": {
        "applies_to": {"quantity": "airplane"},
        "kind": "input",
        "on_violation": "error",
        "criterion": "A main wing is inclined by less than max_inclination.",
        "codes": ["main_wing_without_spanwise_extent"],
        "parameters": {
            "max_inclination": {
                "value": 45.0,
                "unit": "deg",
                "basis": "convention",
                "status": "adopted",
                "source": "adopted by the maintainer on 2026-10-25",
                "regime": "regime-independent",
            }
        },
    },
}
"""The geometry rules the kernel reads, as the shipped canon states them (a test pins the values)."""


def with_geometry_rules(content: dict[str, Any]) -> dict[str, Any]:
    """Give a hand-made namespace the geometry rules the kernel reads, and the ``airplane`` they guard.

    The kernel validates every aircraft against the rules of the canon it runs on; a test model
    that states none would have the kernel refuse every call.
    """
    quantities = content["quantities"]
    quantities.setdefault(
        "airplane", {"symbol": "airplane", "unit": "1", "role": "input", "type": "airplane"}
    )
    content.setdefault("rules", copy.deepcopy(GEOMETRY_RULES))
    return content


def with_hash(namespaces: dict[str, Any]) -> dict[str, Any]:
    """Wrap ``namespaces`` in a complete model dict with the correct content hash.

    A namespace without a ``taxonomy`` gets :func:`world_taxonomy`.
    """
    namespaces = copy.deepcopy(namespaces)
    for content in namespaces.values():
        if "taxonomy" not in content:
            content["taxonomy"] = world_taxonomy(content)
    parsed = _NAMESPACES.validate_python(copy.deepcopy(namespaces))
    return {
        "schema_version": 2,
        "content_hash": compute_content_hash(parsed),
        "importer_version": "0.1.0",
        "namespaces": copy.deepcopy(namespaces),
    }


def base_model() -> dict[str, Any]:
    """Return a minimal valid model dict."""
    return with_hash(base_namespaces())
