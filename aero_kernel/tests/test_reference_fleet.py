"""The reference fleet copies equal their sources except for the recorded additions."""

import hashlib
import json
from pathlib import Path

import pytest
from aero_kernel.schema import AircraftInput
from aero_kernel.tests.reference_fleet import REFERENCE_DIR, FleetMember, reference_documentfrom aero_kernel.validate import validate_aircraft

# Recorded in reference/README.md: the SHA-256 of each source as canonical JSON.
SOURCE_CANONICAL_SHA256 = {
    FleetMember.BRYAN: "09952f107c1204abdd160fb59e668c0bc13131b2a4112a270d77470c9c15d4e1",
    FleetMember.JAGUAR: "92e8ad7c5b29df99175b1c2306b5a4b5509bf753736e853b12114660c2f1bed6",
}
AIRFOIL_SHA256 = {
    "bryan/bryan_profil.dat": "75fc1827fb3059c6525464032b3a9c95f48c1205ef513750fd34532ebb69eb62",
    "bryan/bryan_platte.dat": "d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595",
    "jaguar/jaguar_test_da3dalus_export__tragflaeche_kulfan.dat": "51eadb6d6121bd31cacfb08dead004223142b4f665eedc90e273953af4b92755",
    "jaguar/jaguar_test_da3dalus_export__hoehenleitwerk_kulfan.dat": "b902ac2c03d07c19921cbdaf522a4bd47aacf2c6d7f7c7365b8065856ba06003",
    "jaguar/jaguar_test_da3dalus_export__seitenleitwerk_kulfan.dat": "9a24aa95dc458b6c5a67965ad97a3797dc638ad06ec76250f8b4dbae651d8cb6",
}
SURFACE_TYPES = {
    "Tragflaeche": "main_wing",
    "Hoehenleitwerk": "horizontal_tail",
    "Seitenleitwerk": "vertical_tail",
}


def canonical_sha256(document: object) -> str:
    """SHA-256 of the document as canonical JSON (sorted keys, compact)."""
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.mark.parametrize("member", list(FleetMember))
def test_a_copy_without_its_additions_is_the_source(member: FleetMember) -> None:
    document = json.loads(member.json_path.read_text())
    added = {name: wing.pop("surface_type") for name, wing in document["wings"].items()}
    assert added == SURFACE_TYPES
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
