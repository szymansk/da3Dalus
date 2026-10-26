"""The reference fleet copies equal their sources except for the recorded additions."""

import hashlib
import json
from pathlib import Path

import pytest
from aero_kernel.schema import AircraftInput
from aero_kernel.tests.reference_fleet import (
    FLAP_DEFLECTIONS_DEG,
    REFERENCE_DIR,
    FleetMember,
    reference_document,
)
from aero_kernel.validate import validate_aircraft

# Recorded in reference/README.md: the SHA-256 of each source as canonical JSON.
SOURCE_CANONICAL_SHA256 = {
    FleetMember.BRYAN: "09952f107c1204abdd160fb59e668c0bc13131b2a4112a270d77470c9c15d4e1",
    FleetMember.JAGUAR: "92e8ad7c5b29df99175b1c2306b5a4b5509bf753736e853b12114660c2f1bed6",
    FleetMember.CHEKKER: "01779a0cc90e44b98ea4a49ab8fd949472f0305f1701f60b39b0e8aaf755e3c4",
    FleetMember.BELEMNITOS: "747c570e5527ccfc604a7e466ed2049d96b04b29b05550d07940230241a5754e",
    # WIESEL and RV-7 have no source file: the source is the null-stripped export of the app's
    # GET /aeroplanes/{id} from a copy of db/test.db (README).
    FleetMember.WIESEL: "f8528c5a688219caa834ac73eb190f1d7aa3cd04045d6abfaaed48b77f423e06",
    FleetMember.RV7: "72e8f9e0c5307a001b89b841d6f486eb23624c2ce71f54503dad56350abd06b2",
}
AIRFOIL_SHA256 = {
    "bryan/bryan_profil.dat": "75fc1827fb3059c6525464032b3a9c95f48c1205ef513750fd34532ebb69eb62",
    "bryan/bryan_platte.dat": "d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595",
    "jaguar/jaguar_test_da3dalus_export__tragflaeche_kulfan.dat": "51eadb6d6121bd31cacfb08dead004223142b4f665eedc90e273953af4b92755",
    "jaguar/jaguar_test_da3dalus_export__hoehenleitwerk_kulfan.dat": "b902ac2c03d07c19921cbdaf522a4bd47aacf2c6d7f7c7365b8065856ba06003",
    "jaguar/jaguar_test_da3dalus_export__seitenleitwerk_kulfan.dat": "9a24aa95dc458b6c5a67965ad97a3797dc638ad06ec76250f8b4dbae651d8cb6",
    "chekker/chekker_test_da3dalus_export__tragflaeche_kulfan.dat": "67fd4dedb24e60450644ac2820fc6ac999b54802af4c253b5e27c9785d516e5b",
    "chekker/chekker_test_da3dalus_export__hoehenleitwerk_kulfan.dat": "7b3d6d3664542a344b0485c6ba3f54978dfdcf580acb5e50b56a17fe63da8b47",
    "chekker/chekker_test_da3dalus_export__seitenleitwerk_kulfan.dat": "a246dcdebed289a8acb57ac88afd05e48c0d3df6085c5cc8d866fb4ad09f41bd",
    "belemnitos/mh32.dat": "ad0928ce919261d66d0f58fa22bb450c5cb7f5f5710f8c5bd334005c5e48af4c",
    "belemnitos/belemnitos_vlw_00.dat": "55a9987860ab6f75de8c1c3c94f109eabf77d4a389cb8ba54a5e3258c63c0afb",
    "belemnitos/belemnitos_vlw_01.dat": "10c7e2d9c33fe6e8ef0dbafd3c9182886864b53e3f43a2cfd4c6165a1afdfec6",
    "belemnitos/belemnitos_vlw_02.dat": "ce30712593da820c9a1cbc3de18e92217325c4d92837289404753cbdf536659e",
    "belemnitos/belemnitos_vlw_03.dat": "1b1984d95564d7b828c96045c45e2dd86749d74b6df4dcd8fa02c53c12187dd3",
    "belemnitos/belemnitos_vlw_04.dat": "fe7f88c0651a1e4bf83e14719b53873b937cb4c07b32cfd2d9944892c3fe5c42",
    "belemnitos/belemnitos_vlw_05.dat": "15e69a3bd5289e786682db8fae5ecece396b43eac50b59dbba29604863d455c2",
    "belemnitos/belemnitos_vlw_06.dat": "5991bde121db4dd967c47580e74242b4a5b30a545ca07ee3b5844f541a185e8e",
    "belemnitos/belemnitos_vlw_07.dat": "c4fc111644816911b722c3ce0b1756311a0d16afa8e37f89f7e94f985614b84d",
    "belemnitos/belemnitos_vlw_08.dat": "32299353ef395127caf81fee23404854f110e872ec3e57e464b4b7e0fe79cb11",
    "belemnitos/belemnitos_vlw_09.dat": "93171808ee6f7171b6df2a60beb656095296ea1f2ae78ef3906e764164eed109",
    "wiesel/wiesel_main_wing_kulfan.dat": "3d9c5083d2b78957c9dbd9d1d062d5705106502fd0e4547238991e7ab7549f4a",
    "wiesel/wiesel_horizontal_tail_kulfan.dat": "433c17dc888ef530cccb0485ff2d691e23545c963f39cd99825f719c90cb2917",
    "wiesel/wiesel_vertical_tail_kulfan.dat": "43f596a38e6291726dee681c7b3b50e45faa2f60014f4e1fc1aed48778cebfcf",
    "rv7/naca23013.5.dat": "54262966a988b6e3839e035a860e7030fd41b8a4a1bb554ca0a1e93d98baa882",
    "rv7/naca0015.dat": "645e867c98ddbc808b315c0c0a672cf390aac23fe32112f83b560efb1b0e7bf9",
    "rv7/n12.dat": "82c981d6576fe7793e6657774b2d12ed36c14ec69237a9b72e99dbdbf9d8ddc0",
}
CONVENTIONAL = {
    "Tragflaeche": "main_wing",
    "Hoehenleitwerk": "horizontal_tail",
    "Seitenleitwerk": "vertical_tail",
}
# The role follows the function, per aircraft (README), keyed by the wing name of the copy.
SURFACE_TYPES = {
    FleetMember.BRYAN: CONVENTIONAL,
    FleetMember.JAGUAR: CONVENTIONAL,
    FleetMember.CHEKKER: CONVENTIONAL,
    FleetMember.BELEMNITOS: {"Tragflaeche": "main_wing", "V-Leitwerk": "v_tail"},
    FleetMember.WIESEL: {
        "main_wing": "main_wing",
        "horizontal_tail": "horizontal_tail",
        "vertical_tail": "vertical_tail",
    },
    # the DB names the surfaces "rudder" and "elevator"; the function decides, not the name
    FleetMember.RV7: {
        "main_wing": "main_wing",
        "rudder": "vertical_tail",
        "elevator": "horizontal_tail",
    },
}
# RV-7's root rib of the main wing is a bare designation in the export; the copy gives it the path
# its other five ribs have (an addition: the kernel resolves airfoil files by their path).
# BELEMNITOS' source carries a provenance note the format has no field for; the copy omits it.
BELEMNITOS_NOTE = ("quelle", "e-Hawk_Segler.airplane.json (aiHawk), umgewandelt 2026-10-13")
RV7_ROOT_AIRFOIL = ("naca23013.5", "./components/airfoils/naca23013.5.dat")


def canonical_sha256(document: object) -> str:
    """SHA-256 of the document as canonical JSON (sorted keys, compact)."""
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.mark.parametrize("member", list(FleetMember))
def test_a_copy_without_its_additions_is_the_source(member: FleetMember) -> None:
    document = json.loads(member.json_path.read_text())
    added = {name: wing.pop("surface_type") for name, wing in document["wings"].items()}
    assert added == SURFACE_TYPES[member]
    if member is FleetMember.BELEMNITOS:
        assert BELEMNITOS_NOTE[0] not in document
        document[BELEMNITOS_NOTE[0]] = BELEMNITOS_NOTE[1]
    if member is FleetMember.RV7:
        root = document["wings"]["main_wing"]["x_secs"][0]
        assert root["airfoil"] == RV7_ROOT_AIRFOIL[1]
        root["airfoil"] = RV7_ROOT_AIRFOIL[0]
    assert canonical_sha256(document) == SOURCE_CANONICAL_SHA256[member]


@pytest.mark.parametrize(("name", "digest"), sorted(AIRFOIL_SHA256.items()))
def test_the_airfoil_files_are_byte_identical_copies(name: str, digest: str) -> None:
    assert hashlib.sha256((REFERENCE_DIR / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("member", list(FleetMember))
def test_every_airfoil_path_resolves_into_inline_selig_coordinates(member: FleetMember) -> None:
    document = reference_document(member)
    for wing in document["wings"].values():
        for section in wing["x_secs"]:
            coordinates = section["airfoil"]["coordinates"]
            assert len(coordinates) > 20
            xs = [x for x, _ in coordinates]
            assert abs(xs[0] - 1.0) < 1e-3  # Selig order starts at the trailing edge
            assert abs(min(xs)) < 1e-3
            assert max(xs) <= 1.0 + 1e-6


def test_the_masses_are_the_recorded_ones() -> None:
    assert FleetMember.BRYAN.mass_kg == 0.151  # total_mass_kg of the source
    assert FleetMember.JAGUAR.mass_kg == 0.160  # approx., maintainer 2026-10-14
    assert json.loads(FleetMember.JAGUAR.json_path.read_text())["total_mass_kg"] is None
    assert FleetMember.CHEKKER.mass_kg == 0.439  # total_mass_kg of the source
    assert json.loads(FleetMember.CHEKKER.json_path.read_text())["total_mass_kg"] == 0.439
    # estimated total mass, maintainer 2026-10-26; exact value after the build: equal to the source's
    assert FleetMember.BELEMNITOS.mass_kg == 0.280
    assert json.loads(FleetMember.BELEMNITOS.json_path.read_text())["total_mass_kg"] == 0.28
    assert FleetMember.WIESEL.mass_kg == 0.625  # aeroplanes.total_mass_kg of the app DB
    assert "total_mass_kg" not in json.loads(FleetMember.WIESEL.json_path.read_text())

    assert FleetMember.RV7.mass_kg == 0.500  # approx., maintainer 2026-10-25
    # the export carries no mass, so there is nothing to conflict with
    assert "total_mass_kg" not in json.loads(FleetMember.RV7.json_path.read_text())
    # flaps without a deflection in the DB: the maintainer's guess, 2026-10-26
    assert FLAP_DEFLECTIONS_DEG == {
        FleetMember.RV7: {"flap-deflection-takeoff": 15.0, "flap-deflection-landing": 30.0}
    }


def test_the_readme_records_every_hash_the_tests_check() -> None:
    readme = Path(REFERENCE_DIR / "README.md").read_text()
    for digest in (*SOURCE_CANONICAL_SHA256.values(), *AIRFOIL_SHA256.values()):
        assert digest in readme


@pytest.mark.parametrize("member", list(FleetMember))
def test_a_reference_aircraft_parses_and_is_admissible(member: FleetMember) -> None:
    aircraft = AircraftInput.model_validate(
        {"airplane": reference_document(member), "values": {"aircraft-mass": member.mass_kg}}
    )
    assert validate_aircraft(aircraft).errors == ()
