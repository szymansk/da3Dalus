"""The canon figures: deterministic SVG from in-tree scripts, with numbers computed from a stated example."""

import importlib.util
import math
import pathlib
import xml.etree.ElementTree as ET
from types import ModuleType

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "build_canon_figures.py"
FIGURES = REPO / "_reversa_sdd" / "calculations" / "canon" / "figures"


def load(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load(SCRIPT, "build_canon_figures")


@pytest.fixture(scope="module")
def example() -> ModuleType:
    with pytest.MonkeyPatch.context() as patch:
        patch.syspath_prepend(str(FIGURES))
        return load(FIGURES / "_example.py", "canon_figure_example")


def test_every_figure_script_has_a_committed_svg_that_is_current() -> None:
    assert runner.main(["--check"]) == 0


def test_the_first_batch_of_figures_exists() -> None:
    assert set(runner.figure_names()) >= {
        "mean-aerodynamic-chord",
        "wing-area-span",
        "aspect-ratio",
        "neutral-point",
        "tail-arms",
        "stall-break",
        "spanwise-loads",
    }


@pytest.mark.parametrize("name", runner.figure_names())
def test_a_figure_is_deterministic_well_formed_svg_with_a_caption(name: str) -> None:
    caption, svg = runner.build_figure(name)
    assert runner.build_figure(name)[1] == svg
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "viewBox" in root.attrib
    assert caption.strip()
    assert "nan" not in svg.split("<style>")[0] + svg.split("</style>")[1].lower()
    assert f'<desc id="fg-desc">{caption}</desc>' in svg


def test_the_example_geometry_matches_the_hand_values(example: ModuleType) -> None:
    assert math.isclose(example.c_mac(), 0.23333, abs_tol=1e-4)
    assert math.isclose(example.s_ref(), 0.405, abs_tol=1e-9)
    assert math.isclose(example.b_ref(), 1.8, abs_tol=1e-9)
    assert math.isclose(example.aspect_ratio(), 1.8**2 / 0.405, abs_tol=1e-9)
    assert math.isclose(
        example.x_ac_wing() - example.x_le_mac(), 0.25 * example.c_mac(), abs_tol=1e-12
    )


def test_the_neutral_point_worlds_lie_aft_of_the_wing_and_ahead_of_the_tail(
    example: ModuleType,
) -> None:
    for x in (example.np_textbook(), example.np_pappas()):
        assert example.x_ac_wing() < x < example.X_AC_TAIL


def test_the_stall_break_procedure_brackets_the_crossing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(FIGURES))
    figure = load(FIGURES / "stall_break.py", "canon_figure_stall_break")
    samples = figure.polar()
    alpha_s, cl_max, alpha_break, width = figure.stall_break(samples, 0.10)
    assert math.isclose(alpha_s, 12.0)
    assert math.isclose(cl_max, 1.4)
    assert math.isclose(width, alpha_break - alpha_s)
    # past the peak the example falls as peak - FALL (alpha - alpha_s)^2; the sample interpolation is
    # within the sampling error of the exact crossing
    exact = alpha_s + math.sqrt(0.10 * cl_max / figure.FALL)
    assert abs(alpha_break - exact) < 0.1
    with pytest.raises(ValueError, match="does not fall"):
        figure.stall_break(samples, 0.9999)


def test_the_spanwise_loads_integrate_to_the_weight_and_the_elliptic_root_moment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(FIGURES))
    figure = load(FIGURES / "spanwise_loads.py", "canon_figure_spanwise_loads")
    example = load(FIGURES / "_example.py", "canon_figure_example2")
    _, _, shear, moment = figure.loads()
    weight = figure.LOAD_FACTOR * figure.MASS * figure.GRAVITY
    assert math.isclose(shear[0], weight / 2, rel_tol=1e-3)
    half = example.b_ref() / 2
    assert math.isclose(moment[0], weight / 2 * 4 / (3 * math.pi) * half, rel_tol=1e-3)
    assert math.isclose(shear[-1], 0.0, abs_tol=1e-12)
