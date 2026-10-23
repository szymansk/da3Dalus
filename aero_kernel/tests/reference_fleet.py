"""Loading the reference fleet (``reference/``) as kernel input; see ``reference/README.md``."""

import json
from enum import Enum
from pathlib import Path
from typing import Any

REFERENCE_DIR = Path(__file__).resolve().parent / "reference"

# ``Any`` is the raw-JSON boundary: the document is validated by ``AirplaneGeometry`` afterwards.


class FleetMember(Enum):
    """An aircraft of the reference fleet.

    Attributes:
        json_path: The copy of the geometry document.
        mass_kg: The mass the tests pass as ``aircraft-mass`` (README for its source).
    """

    BRYAN = ("bryan/bryan.airplane.json", 0.151)
    JAGUAR = ("jaguar/flugzeug.json", 0.160)

    def __init__(self, relative_path: str, mass_kg: float) -> None:
        self.json_path = REFERENCE_DIR / relative_path
        self.mass_kg = mass_kg


def read_selig_coordinates(path: Path) -> list[list[float]]:
    """Read a Selig ``.dat`` file: an optional name line, then ``x y`` pairs."""
    points: list[list[float]] = []
    for line in path.read_text().splitlines():
        fields = line.split()
        try:
            x, y = (float(field) for field in fields)
        except ValueError:
            continue  # the name line
        points.append([x, y])
    return points


def reference_document(member: FleetMember) -> dict[str, Any]:
    """Load a copy with every airfoil file path resolved into inline coordinates.

    The path is resolved by its file name next to the JSON (the README says why).

    Args:
        member: The aircraft.

    Returns:
        The document as a dict, ready for ``AirplaneGeometry.model_validate``.
    """
    document: dict[str, Any] = json.loads(member.json_path.read_text())
    for wing in document["wings"].values():
        for section in wing["x_secs"]:
            name = Path(section["airfoil"]).name
            section["airfoil"] = {
                "coordinates": read_selig_coordinates(member.json_path.parent / name)
            }
    return document
