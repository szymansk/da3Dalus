"""The navigator embeds the canon figures named in an entry's front matter, and rejects a dangling or orphan one."""

import importlib.util
import pathlib
from typing import Any

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "build_canon_navigator", REPO / "scripts" / "build_canon_navigator.py"
)
assert _SPEC is not None
assert _SPEC.loader is not None
nav = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(nav)

SVG = '<svg xmlns="http://www.w3.org/2000/svg"><title>t</title><desc id="fg-desc">A caption.</desc></svg>\n'


def canon(
    tmp_path: pathlib.Path, front: str = "figure: demo\n", svg: str | None = SVG
) -> pathlib.Path:
    (tmp_path / "quantities").mkdir()
    (tmp_path / "figures").mkdir()
    (tmp_path / "quantities" / "q.md").write_text(
        f"---\ncanon: q\nkind: quantity\n{front}---\n\n# Q\n", encoding="utf-8"
    )
    if svg is not None:
        (tmp_path / "figures" / "demo.svg").write_text(svg, encoding="utf-8")
    return tmp_path


def data_of() -> dict[str, Any]:
    return {"Q": {"q": {}}}


def test_a_figure_is_embedded_once_with_its_caption(tmp_path: pathlib.Path) -> None:
    data = data_of()
    nav.figure_marks(data, canon(tmp_path))
    assert data["Q"]["q"]["fig"] == "demo"
    assert data["figs"]["demo"] == {"svg": SVG, "caption": "A caption."}


def test_a_quantity_without_a_figure_gets_no_mark(tmp_path: pathlib.Path) -> None:
    data = data_of()
    nav.figure_marks(data, canon(tmp_path, front="", svg=None))
    assert "fig" not in data["Q"]["q"]
    assert data["figs"] == {}


def test_a_missing_svg_is_an_error(tmp_path: pathlib.Path) -> None:
    root = canon(tmp_path, svg=None)
    with pytest.raises(SystemExit, match="demo"):
        nav.figure_marks(data_of(), root)


def test_an_svg_no_entry_names_is_an_error(tmp_path: pathlib.Path) -> None:
    root = canon(tmp_path, front="", svg=SVG)
    with pytest.raises(SystemExit, match="demo"):
        nav.figure_marks(data_of(), root)


def test_a_figure_without_a_caption_is_an_error(tmp_path: pathlib.Path) -> None:
    root = canon(tmp_path, svg="<svg xmlns='http://www.w3.org/2000/svg'></svg>\n")
    with pytest.raises(SystemExit, match="caption"):
        nav.figure_marks(data_of(), root)


def test_the_real_canon_embeds_every_figure() -> None:
    _, data = nav.build()
    assert {"mean-aerodynamic-chord", "wing-area-span", "stall-break"} <= set(data["figs"])
    assert data["Q"]["wing-span"]["fig"] == "wing-area-span"
    assert data["Q"]["wing-reference-area"]["fig"] == "wing-area-span"
