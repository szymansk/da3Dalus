"""Loading the reference fleet (``reference/``) as kernel input; see ``reference/README.md``."""

import json
from collections.abc import Sequence
from enum import Enum
from pathlib import Path
from typing import Any

from aero_kernel.geometry_properties import MainWingProperties
from aero_kernel.schema import QuantityResult, QuantityStatus

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
        0.280,  # estimated total mass, maintainer 2026-10-26; exact value after the build
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


# The fuselages AeroSandbox cannot take: a section whose upper and lower shape exponents differ
# (``n_lower != n``; AeroSandbox has one exponent per section). The kernel declares this as an
# ``unsupported_configuration`` error naming the first such section, so every quantity that needs
# the AeroSandbox airplane is recorded as that error for these two aircraft (README, "Results").
# The kernel will take such a section as an equivalent symmetric one: #1307. Until then the error is
# the expected result; when #1307 lands these entries and their tests are re-recorded as values.
FUSELAGE_REJECTED = {
    FleetMember.CHEKKER: ("Rumpf", 0),
    FleetMember.WIESEL: ("fuselage", 9),
}


def assert_rejected_for_the_fuselage(
    member: FleetMember, quantities: Sequence[QuantityResult], *, rooted: bool = True
) -> None:
    """Every quantity is an error: the fuselage itself, or a quantity that waits for one.

    ``rooted``: at least one quantity carries the fuselage error itself (not so when every quantity
    only waits for another that is not among them).
    """
    name, section = FUSELAGE_REJECTED[member]
    roots: list[QuantityResult] = []
    for quantity in quantities:
        assert quantity.status is QuantityStatus.ERROR, quantity.slug
        assert quantity.value is None, quantity.slug
        assert quantity.error is not None, quantity.slug
        if quantity.error.code == "upstream_failed":
            continue
        roots.append(quantity)
        assert quantity.error.code == "unsupported_configuration", quantity.slug
        assert quantity.error.detail == {"fuselage": name}, quantity.slug
        assert quantity.error.message == (
            f"section {section} of the fuselage '{name}' has n_lower != n; "
            "AeroSandbox has one shape exponent per section"
        ), quantity.slug
    assert roots or not rooted, "no quantity carries the fuselage error itself"


# RV-7 has flaps and the DB gives no deflection: the take-off and landing configurations are the
# maintainer's guess (2026-10-26), passed as caller parameters like any design input. The other
# aircraft have no flap, so they take none.
FLAP_DEFLECTIONS_DEG = {
    FleetMember.RV7: {"flap-deflection-takeoff": 15.0, "flap-deflection-landing": 30.0},
}


def flap_values(member: FleetMember) -> dict[str, float]:
    """The flap deflection inputs of this aircraft (empty without flaps)."""
    return dict(FLAP_DEFLECTIONS_DEG.get(member, {}))
