"""Generate the canon's figures: one SVG per script in ``canon/figures/``.

Each figure script defines ``CAPTION`` and ``build() -> str`` (SVG text) and draws its numbers from
a stated hand example computed in pure Python. The output is deterministic, so CI compares it.

Run:   poetry run python scripts/build_canon_figures.py
Check: poetry run python scripts/build_canon_figures.py --check   (fails if a committed SVG is stale)
"""

import importlib.util
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
FIGURES = REPO / "_reversa_sdd/calculations/canon/figures"


def figure_names() -> list[str]:
    """The names of the figures: the scripts without a leading underscore, with dashes."""
    return sorted(p.stem.replace("_", "-") for p in FIGURES.glob("[a-z]*.py"))


def build_figure(name: str) -> tuple[str, str]:
    """Run one figure script: its caption and its SVG text."""
    path = FIGURES / f"{name.replace('-', '_')}.py"
    sys.path.insert(0, str(FIGURES))  # the scripts import the shared _svg and _example next to them
    try:
        spec = importlib.util.spec_from_file_location(f"canon_figure_{path.stem}", path)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(FIGURES))
    return module.CAPTION, module.build()


def main(argv: list[str]) -> int:
    """Write the figures, or with ``--check`` fail on a stale or missing one."""
    stale = []
    for name in figure_names():
        _, svg = build_figure(name)
        target = FIGURES / f"{name}.svg"
        if "--check" in argv:
            if not target.exists() or target.read_text(encoding="utf-8") != svg:
                stale.append(target.name)
        else:
            target.write_text(svg, encoding="utf-8")
    if stale:
        print(
            f"stale figures: {', '.join(stale)}: run `poetry run python scripts/build_canon_figures.py`"
        )
        return 1
    print("figures are current" if "--check" in argv else f"{len(figure_names())} figures written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
