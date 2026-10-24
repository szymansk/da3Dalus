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


def with_hash(namespaces: dict[str, Any]) -> dict[str, Any]:
    """Wrap ``namespaces`` in a complete model dict with the correct content hash."""
    parsed = _NAMESPACES.validate_python(copy.deepcopy(namespaces))
    return {
        "schema_version": 1,
        "content_hash": compute_content_hash(parsed),
        "importer_version": "0.1.0",
        "namespaces": copy.deepcopy(namespaces),
    }


def base_model() -> dict[str, Any]:
    """Return a minimal valid model dict."""
    return with_hash(base_namespaces())
