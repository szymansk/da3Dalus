"""The location check of ``data:`` sources against the repository's own files (#1251)."""

from pathlib import Path

import pytest
from aero_kernel.importer.data_sources import (
    Catalogue,
    find_repo_root,
    load_catalogue,
    location_problem,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CANON = REPO_ROOT / "_reversa_sdd" / "calculations" / "canon"
DEFAULTS = frozenset({"gravity"})


@pytest.fixture(scope="module")
def catalogue() -> Catalogue:
    return load_catalogue(REPO_ROOT)


def problem(source: str, catalogue: Catalogue) -> str | None:
    return location_problem(source, catalogue, DEFAULTS)


def test_the_repository_is_found_above_the_canon() -> None:
    assert find_repo_root(CANON) == REPO_ROOT


def test_no_repository_is_found_for_a_directory_outside_it(tmp_path: Path) -> None:
    assert find_repo_root(tmp_path) is None


@pytest.mark.parametrize(
    "source",
    [
        "geometry:$",
        "geometry:total_mass_kg",
        "geometry:xyz_ref",
        "geometry:wings.x_secs.chord",
        "geometry:wings.x_secs.trailing_edge_device.deflection_deg",
    ],
)
def test_a_geometry_path_of_the_schema_resolves(source: str, catalogue: Catalogue) -> None:
    assert problem(source, catalogue) is None


@pytest.mark.parametrize(
    "source", ["geometry:mass", "geometry:wings.x_secs.cord", "geometry:total_mass_kg.value"]
)
def test_a_geometry_path_the_schema_lacks_is_a_problem(source: str, catalogue: Catalogue) -> None:
    assert problem(source, catalogue) is not None


@pytest.mark.parametrize(
    "source",
    [
        "component:brushless_motor",
        "component:brushless_motor.kv_rpm_per_volt",
        "component:battery.mass_g",
    ],
)
def test_a_component_type_and_field_of_the_seed_resolve(source: str, catalogue: Catalogue) -> None:
    assert problem(source, catalogue) is None


@pytest.mark.parametrize("source", ["component:rocket", "component:brushless_motor.efficiency_pct"])
def test_a_component_type_or_field_the_seed_lacks_is_a_problem(
    source: str, catalogue: Catalogue
) -> None:
    assert problem(source, catalogue) is not None


def test_an_app_field_of_a_schema_class_resolves(catalogue: Catalogue) -> None:
    assert problem("app:OperatingPointSchema.velocity", catalogue) is None


@pytest.mark.parametrize(
    "source", ["app:OperatingPointSchema.speed", "app:Nonsense.velocity", "app:Goals"]
)
def test_an_app_field_the_schemas_lack_is_a_problem(source: str, catalogue: Catalogue) -> None:
    assert problem(source, catalogue) is not None


def test_a_default_is_a_key_of_defaults_yaml(catalogue: Catalogue) -> None:
    assert problem("default:gravity", catalogue) is None
    assert problem("default:thrust", catalogue) is not None


def test_a_kind_without_repository_facts_is_not_checked() -> None:
    assert problem("geometry:anything.at.all", Catalogue()) is None
    assert problem("evaluation:static-margin", Catalogue()) is None
