"""Loading the reference fleet (``reference/``) as kernel input; see ``reference/README.md``."""

import json
from enum import Enum
from pathlib import Path
from typing import Any

from aero_kernel.geometry_properties import MainWingProperties

REFERENCE_DIR = Path(__file__).resolve().parent / "reference"

# ``Any`` is the raw-JSON boundary: the document is validated by ``AirplaneGeometry`` afterwards.


class FleetMember(Enum):
    """An aircraft of the reference fleet.

    Attributes:
        json_path: The copy of the geometry document.
        mass_kg: The mass the tests pass as ``aircraft-mass`` (README for its source).
        asb_reference: AeroSandbox 4.2.9's ``(area(type="planform", include_centerline_distance=True),
            span(type="yz", include_centerline_distance=True), mean_aerodynamic_chord())`` of the main wing in m^2, m, m, frozen so the fast tier needs
            no AeroSandbox; ``test_geometry_properties`` checks them against the real one.
    """

    BRYAN = (
        "bryan/bryan.airplane.json",
        0.151,
        (0.0700246334494812, 0.5470385422650689, 0.13280160307833674),
    )
    JAGUAR = (
        "jaguar/flugzeug.json",
        0.160,
        (0.06465165601284742, 0.624210916480389, 0.10498485405652615),
    )
    CHEKKER = (
        "chekker/flugzeug.json",
        0.439,
        (0.13593819641333416, 0.8641237898707764, 0.16147835300713256),
    )
    BELEMNITOS = (
        "belemnitos/flugzeug.json",
        0.550,  # approx., maintainer 2026-10-25 (the source says 0.28)
        (0.1997453990895134, 1.4992332323342878, 0.1398699109383301),
    )
    WIESEL = (
        "wiesel/wiesel.airplane.json",
        0.625,
        (0.14046014819687722, 0.9146176960978459, 0.16265318641915597),
    )
    RV7 = (
        "rv7/rv7.airplane.json",
        0.500,  # approx., maintainer 2026-10-25
        (0.15006000000000005, 0.8200000000000003, 0.183),
    )

    def __init__(
        self, relative_path: str, mass_kg: float, asb_reference: tuple[float, float, float]
    ) -> None:
        self.json_path = REFERENCE_DIR / relative_path
        self.mass_kg = mass_kg
        self.asb_reference = asb_reference

    def wing_name(self, surface_type: str) -> str:
        """The name of the one wing of this type in the copy."""
        wings = json.loads(self.json_path.read_text())["wings"]
        (name,) = [n for n, w in wings.items() if w["surface_type"] == surface_type]
        return name

    @property
    def main_wing_name(self) -> str:
        """The name of the main wing."""
        return self.wing_name("main_wing")

    @property
    def tail_name(self) -> str:
        """The name of the surface that trims the pitch: the horizontal tail or the V-tail."""
        wings = json.loads(self.json_path.read_text())["wings"]
        (name,) = [
            n for n, w in wings.items() if w["surface_type"] in ("horizontal_tail", "v_tail")
        ]
        return name

    @property
    def reference(self) -> MainWingProperties:
        """The frozen AeroSandbox reference values of the main wing."""
        s_ref, b_ref, c_mac = self.asb_reference
        return MainWingProperties(s_ref=s_ref, b_ref=b_ref, c_mac=c_mac)


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
