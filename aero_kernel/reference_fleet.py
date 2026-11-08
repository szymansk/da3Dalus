"""Loading the reference fleet (``reference/``) as kernel input; see ``reference/README.md``.

Public: the application's expert view serves the fleet through this module (ADR 0030), and the
kernel tests load it as real input. One source for the documents, the masses and the flap
deflections.
"""

import json
from enum import Enum
from pathlib import Path
from typing import Any

from aero_kernel.geometry_properties import MainWingProperties
from aero_kernel.schema import AircraftInput

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
    # The 28 plan models of the plugin batch 2026-11-05 (DB ids 99-126, #1372): exported as WIESEL
    # and RV-7 were; each mass and its source are in the README (maintainer, 2026-11-07).
    A6M2_ZERO = (
        "a6m2_zero/a6m2_zero.airplane.json",
        0.36,  # DB value; the six 0.75 m warbirds share dimensions (maintainer)
        (0.09479807326962095, 0.7474914295219584, 0.13407792070363186),
    )
    AERONCA_CHAMP = (
        "aeronca_champ/aeronca_champ.airplane.json",
        0.39,  # median wing loading of comparable models x S (maintainer)
        (0.1294784806772935, 0.9056393264512532, 0.14573613857950724),
    )
    ALBATROS_4 = (
        "albatros_4/albatros_4.airplane.json",
        5.0,  # DB, unverified (plugin)
        (1.1311692134091602, 4.064558065525576, 0.29417471214604574),
    )
    BARRACUDA = (
        "barracuda/barracuda.airplane.json",
        1.54,  # median wing loading of comparable models x S (maintainer)
        (0.4023164909750201, 2.457015197486458, 0.16416371729872276),
    )
    BF109_E = (
        "bf109_e/bf109_e.airplane.json",
        0.36,  # DB value; the six 0.75 m warbirds share dimensions (maintainer)
        (0.0957230190752197, 0.7492411231287676, 0.13413742218102967),
    )
    D520_DEWOITINE = (
        "d520_dewoitine/d520_dewoitine.airplane.json",
        0.36,  # DB value; the six 0.75 m warbirds share dimensions (maintainer)
        (0.09476688109185386, 0.7474981146561575, 0.13404662459599262),
    )
    DARDO = (
        "dardo/dardo.airplane.json",
        1.35,  # DB, unverified (plugin)
        (0.36946099131525617, 1.927554320345861, 0.1958035204702476),
    )
    ESTRELA = (
        "estrela/estrela.airplane.json",
        1.7,  # plan, ~74 g/dm2, maintainer
        (0.23151605462, 1.018414, 0.22732999999999998),
    )
    EXTRA_300_EP = (
        "extra_300_ep/extra_300_ep.airplane.json",
        0.75,  # DB, unverified (plugin)
        (0.19197062149999997, 1.0406, 0.18985958664669428),
    )
    F3A_COMPETICION = (
        "f3a_competicion/f3a_competicion.airplane.json",
        4.7,  # DB, unverified; ~70 g/dm2 asked, not answered
        (0.6759957462548665, 1.9485249049007831, 0.37342847542564533),
    )
    FORCE_5 = (
        "force_5/force_5.airplane.json",
        1.22,  # DB, unverified (plugin)
        (0.5724266395037543, 2.527810402831847, 0.2299532119717108),
    )
    FORCE_FOUR = (
        "force_four/force_four.airplane.json",
        0.68,  # DB, unverified (plugin)
        (0.1797914721005986, 1.5527399940193276, 0.11761377164746496),
    )
    FW190_A8 = (
        "fw190_a8/fw190_a8.airplane.json",
        0.35,  # DB value; the six 0.75 m warbirds share dimensions (maintainer)
        (0.09577666253242607, 0.749720419961544, 0.13416719896227158),
    )
    GEE_BEE_R3 = (
        "gee_bee_r3/gee_bee_r3.airplane.json",
        12.0,  # plan's estimated dry weight 26-27 lb (maintainer); no fuel
        (1.287059606197243, 2.640250014911991, 0.5166963370124031),
    )
    KASTAWAY = (
        "kastaway/kastaway.airplane.json",
        0.65,  # median wing loading of comparable models x S (maintainer)
        (0.24415894831438648, 1.4997514240263492, 0.16709797334211204),
    )
    MILES_MAGISTER = (
        "miles_magister/miles_magister.airplane.json",
        0.36,  # DB value; the six 0.75 m warbirds share dimensions (maintainer)
        (0.08159563230371851, 0.7487165429539202, 0.11232509890328313),
    )
    MINI_FUNTANA = (
        "mini_funtana/mini_funtana.airplane.json",
        0.539,  # DB, unverified (plugin)
        (0.20968555679999998, 0.9398, 0.22814871664371625),
    )
    P36_HAWK = (
        "p36_hawk/p36_hawk.airplane.json",
        0.36,  # DB value; the six 0.75 m warbirds share dimensions (maintainer)
        (0.09532716016852054, 0.7638246544032625, 0.13333577980035768),
    )
    P39 = (
        "p39/p39.airplane.json",
        9.5,  # median wing loading of comparable models x S (maintainer)
        (1.0064408524931268, 2.3353239865776505, 0.45949137781802324),
    )
    SNOOPY = (
        "snoopy/snoopy.airplane.json",
        1.474,  # DB, unverified (plugin)
        (0.5972707311632537, 3.202277572817502, 0.190562377571955),
    )
    SONAS_40 = (
        "sonas_40/sonas_40.airplane.json",
        2.1,  # median wing loading of comparable models x S (maintainer)
        (0.3637375073024503, 1.4168474017450945, 0.2593836576159867),
    )
    SPIRIT_100 = (
        "spirit_100/spirit_100.airplane.json",
        1.26,  # median wing loading of comparable models x S (maintainer)
        (0.6147868353514252, 2.553729771840085, 0.24506431173279),
    )
    SPRITE = (
        "sprite/sprite.airplane.json",
        1.0,  # median wing loading of comparable models x S (maintainer)
        (0.18980244358684775, 0.9908482738198826, 0.1932739094141681),
    )
    SUPER_TRIDENT = (
        "super_trident/super_trident.airplane.json",
        1.05,  # DB, unverified (plugin)
        (0.42168247164334927, 2.5332538154891835, 0.16764138961672956),
    )
    ULTRA_MINI_STICK = (
        "ultra_mini_stick/ultra_mini_stick.airplane.json",
        0.35,  # DB, unverified (plugin)
        (0.1503972208444533, 0.831300002110264, 0.18592093571634968),
    )
    VOODOO = (
        "voodoo/voodoo.airplane.json",
        1.16,  # median wing loading of comparable models x S (maintainer)
        (0.5408542135972135, 1.7643736535977261, 0.3212452748241717),
    )
    WINDFREAK = (
        "windfreak/windfreak.airplane.json",
        2.6,  # median wing loading of comparable models x S (maintainer)
        (0.9073078179033027, 2.493476936709209, 0.3652262185601376),
    )
    WRISTOCRAT = (
        "wristocrat/wristocrat.airplane.json",
        0.34,  # DB, unverified (plugin)
        (0.21277910716807166, 1.4556142295425263, 0.14754900416659267),
    )

    def __init__(
        self, relative_path: str, mass_kg: float, asb_reference: tuple[float, float, float]
    ) -> None:
        """Bind the geometry copy, the mass and the frozen AeroSandbox reference of the member."""
        self.json_path = REFERENCE_DIR / relative_path
        self.mass_kg = mass_kg
        self.asb_reference = asb_reference

    def wing_name(self, surface_type: str) -> str:
        """The name of the one wing of this type in the copy."""
        wings = json.loads(self.json_path.read_text())["wings"]
        (name,) = [n for n, w in wings.items() if w["surface_type"] == surface_type]
        return name

    @property
    def display_name(self) -> str:
        """The name a person reads: the enum name with the hyphen of ``RV-7``."""
        return "RV-7" if self is FleetMember.RV7 else self.name

    @property
    def fleet_id(self) -> str:
        """The stable identifier of this aircraft in the application: its lower-case display name."""
        return self.display_name.lower()

    @classmethod
    def from_fleet_id(cls, fleet_id: str) -> "FleetMember | None":
        """Return the member with this identifier, or ``None`` if the fleet has none."""
        return next((member for member in cls if member.fleet_id == fleet_id), None)

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


# RV-7 has flaps and the DB gives no deflection: the take-off and landing configurations are the
# maintainer's guess (2026-10-26), passed as caller parameters like any design input. The other
# aircraft have no flap, so they take none.
FLAP_DEFLECTIONS_DEG = {
    FleetMember.RV7: {"flap-deflection-takeoff": 15.0, "flap-deflection-landing": 30.0},
}


def flap_values(member: FleetMember) -> dict[str, float]:
    """The flap deflection inputs of this aircraft (empty without flaps)."""
    return dict(FLAP_DEFLECTIONS_DEG.get(member, {}))


def fleet_values(member: FleetMember) -> dict[str, float]:
    """The input values the fleet fixes for this aircraft: its mass and its flap deflections."""
    return {"aircraft-mass": member.mass_kg, **flap_values(member)}


def aircraft_input(member: FleetMember, values: dict[str, float] | None = None) -> AircraftInput:
    """Build the kernel input of a fleet aircraft.

    Args:
        member: The aircraft.
        values: Caller values by canon slug; they replace the fleet's own values of the same slug.

    Returns:
        The geometry document with inline airfoils and the fleet values overlaid with ``values``.
    """
    return AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {**fleet_values(member), **(values or {})},
        }
    )
