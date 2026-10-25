"""A small canon document written to a temporary directory, for the importer tests.

The importer is tested against this hand-written mini canon (one mutation per finding class) and
once against the real canon document.
"""

from pathlib import Path

__all__ = ["MINI_CANON", "MINI_TAXONOMY", "write_canon"]


def _quantity(
    slug: str, symbol: str, unit: str, role: str, extra: str = "", type_: str = "scalar"
) -> str:
    shown = f'"{unit}"' if unit == "N" else unit  # the newton is a YAML 1.1 boolean unless quoted
    return (
        f"---\ncanon: {slug}\nkind: quantity\nsymbol: {symbol}\nunit: {shown}\nrole: {role}\n"
        f"tags:\n  - canon/quantity\ntype: {type_}\n{extra}---\n\n# {slug}\n\nProse.\n"
    )


def _formula(slug: str, body: str) -> str:
    return (
        f"---\ncanon: {slug}\nentry: formula\nstatus: draft\nshape: law\noutput: weight\n"
        f"source_status: SOURCED\ndimensional_check: OK\ntags:\n  - canon/formula\n"
        f"tex: w = m g\n{body}---\n\n# {slug}\n\nProse that is never read: {{not: yaml\n"
    )


MINI_TAXONOMY = """\
tools:
  - {id: APP, name: App}
  - {id: AB, name: AeroBuildup}
  - {id: AVL, name: AVL}
  - {id: OPT, name: Optimisation}
  - {id: ATM, name: Atmosphere}
  - {id: GEO, name: Geometry}
  - {id: KAT, name: Catalogue}
  - {id: APC, name: Propeller tables}
worlds:
  - {id: simple, tool: APP}
  - {id: detailed, tool: AVL}
"""

MINI_CANON: dict[str, str] = {
    "taxonomy.yaml": MINI_TAXONOMY,
    "quantities/aircraft-mass.md": _quantity(
        "aircraft-mass", "m", "kg", "input", "positive: true\ndata: geometry:total_mass_kg\n"
    ),
    "quantities/gravity.md": _quantity("gravity", "g", "m/s^2", "input", "positive: true\n"),
    "quantities/weight.md": _quantity("weight", "W", "N", "derived"),
    "quantities/weight-estimate.md": _quantity(
        "weight-estimate", "W_e", "N", "derived", "uncertainty: interval\n"
    ),
    "quantities/weight-twice.md": _quantity("weight-twice", "W_2", "N", "derived"),
    "quantities/weight-outer.md": _quantity("weight-outer", "W_o", "N", "derived"),
    "quantities/weight-weighed.md": _quantity("weight-weighed", "W_w", "N", "derived"),
    "quantities/weight-flapped.md": _quantity("weight-flapped", "W_f", "N", "derived"),
    "quantities/airplane.md": _quantity("airplane", "airplane", "—", "input", type_="airplane"),
    "quantities/ratio.md": _quantity("ratio", "r", "1", "input"),
    "formulas/weight-from-mass.md": _formula(
        "weight-from-mass",
        "kind: law\ntool: APP\ninputs: {m: aircraft-mass, g: gravity}\noutputs: {w: weight}\n"
        "preconditions:\n  - {id: m_checked, parameter: m, on_violation: warning}\n"
        "postconditions:\n  - {id: w_checked, parameter: w, on_violation: error}\n",
    ),
    "formulas/weighing.md": _formula(
        "weighing",
        "kind: procedure\ntool: AB\n"
        "inputs: {m: aircraft-mass, g: gravity}\noutputs: {w: null}\n"
        "applications:\n"
        "  - id: clean\n    produce: {w: weight-weighed}\n"
        "  - id: flapped\n    bind: {g: {const: 9.81, source: test source}}\n"
        "    produce: {w: weight-flapped}\n    when: has_aileron\n    given: [aircraft-mass]\n"
        "postconditions:\n"
        "  - {id: clean_only, parameter: w, on_violation: warning, applications: [clean]}\n",
    ),
    "formulas/estimate.md": _formula(
        "estimate",
        "kind: procedure\ntool: AVL\nuncertainty: interval\nworlds: [simple, detailed]\n"
        "inputs: {m: aircraft-mass, g: gravity}\noutputs: {w: weight-estimate}\n",
    ),
    "formulas/weigh-twice.md": _formula(
        "weigh-twice",
        "kind: procedure\ntool: APP\ninputs: {m: aircraft-mass, g: gravity}\n"
        "outputs: {w: weight-twice}\nembeds: [weight-from-mass, weighing.clean]\n"
        "variables: [aircraft-mass]\n",
    ),
    "formulas/outer.md": _formula(
        "outer",
        "kind: optimization\ntool: OPT\ncost: minutes\ninputs: {m: aircraft-mass, g: gravity}\n"
        "outputs: {w: weight-outer}\nembeds: [weigh-twice]\nvariables: [aircraft-mass]\n"
        "optional: [g]\n",
    ),
    "defaults.yaml": (
        "gravity:\n  value: 9.80665\n  unit: m/s^2\n  basis: standard\n  source: standard gravity\n"
        "  regime: regime-independent\n"
    ),
}


def write_canon(root: Path, overrides: dict[str, str | None] | None = None) -> Path:
    """Write the mini canon under ``root / "canon"``.

    Args:
        root: Directory to write into (a pytest ``tmp_path``).
        overrides: File name (relative to the canon) to replacement text; ``None`` removes it.

    Returns:
        The canon directory.
    """
    canon = root / "canon"
    files = {**MINI_CANON, **(overrides or {})}
    for name, text in files.items():
        if text is None:
            continue
        target = canon / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    (canon / "formulas").mkdir(parents=True, exist_ok=True)
    (canon / "quantities").mkdir(parents=True, exist_ok=True)
    return canon
