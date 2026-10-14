"""Checks for the calculation canon: dimensions and structure.

Two checks, both authoring aids for the canon document (`_reversa_sdd/calculations/canon/`):

**Dimensional.** Parses each canonical form, substitutes the declared unit of every symbol
from the quantity register, and evaluates the dimension of the right-hand side. Reports a
formula whose result does not match its declared output quantity, or which adds two
quantities of unlike dimension. Informational; it does not fail the run.

**Structural (#1181).** Cross-checks the machine-readable front matter defined in the canon
README ("Machine-readable fields") against itself and against the prose links: `inputs` /
`outputs` / `applications` against the "Produces … from" line, the quantities' "Used by" /
"Produced by" links, every referenced slug, the closed `when` vocabulary and `type` set,
every parameter bound in every application. A structural error fails the run. A gap in an
entry whose front matter carries an `# ESCALATED:` comment is reported as *open* instead:
the question is with the maintainer, the gap is known.

Run:  poetry run python scripts/check_canon.py [canon-dir | canon.json]
      (default: _reversa_sdd/calculations/canon; a .json file runs the dimensional check only)
"""

from __future__ import annotations

import ast
import dataclasses
import json
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from canon_to_json import build as build_canon_json  # noqa: E402
from dimensions import ONE, Dim, parse_unit  # noqa: E402

DEFAULT_CANON = pathlib.Path("_reversa_sdd/calculations/canon")

FUNCS = {"sqrt": 0.5, "cbrt": 1 / 3}

#: forms that are definitions or procedures, not algebraic laws — a dimensional
#: check does not apply to them, and failing them would be noise.
PROCEDURAL = re.compile(
    r"minimi[sz]e|maximi[sz]e|\bsolve for\b|\broute [AB]\b|argmax|argmin|max over|min over|first i|interp\(|:=|\bfor V\b|\bwhere\b|"
    r"crossing|detection|_ISA\(|table|converted to|optionally|standard atmosphere",
    re.I,
)

#: dimensionless mathematical constants that may appear in a canonical form
MATH_CONSTANTS = {"pi", "tau", "euler"}

#: qualifiers a canonical form may append to a registered symbol
QUALIFIERS = (
    "clean",
    "cfg",
    "config",
    "target",
    "ref",
    "max",
    "min",
    "total",
    "req",
    "static",
    "mean",
    "eff",
    "i",
    "j",
    "0",
    "1",
    "s0",
    "s1",
    "op",
    "turn",
)


def norm(sym: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (sym or "").lower())


def build_symbols(quantities):
    """normalised symbol/slug -> Dim, with qualifier-stripping aliases."""
    table = {}
    for q in quantities:
        d = parse_unit(q.get("unit"))
        if d is None:
            continue
        for key in (q.get("symbol"), q.get("slug"), q.get("name")):
            k = norm(key)
            if k and k not in table:
                table[k] = d
    for c in MATH_CONSTANTS:
        table.setdefault(c, ONE)
    # Single-letter conventions the canonical forms use for registered quantities.
    # These OVERRIDE whatever a quantity's own symbol happened to claim first: norm()
    # folds case, so `w` (sink rate, m/s) and `W` (weight, N) collide, and sink-rate
    # sorts first. That one collision made three correct formulas report as dimensional
    # errors. The conventions below are declared for exactly this purpose, so they win.
    for alias, target in (
        ("s", "sref"),
        ("b", "bref"),
        ("v", "flightspeed"),
        ("w", "weight"),
        ("m", "aircraftmass"),
        ("h", "altitude"),
    ):
        if target in table:
            table[alias] = table[target]
    return table


def lookup(name, table):
    """Resolve a symbol, tolerating appended qualifiers: C_L,max,clean -> C_L,max."""
    k = norm(name)
    if k in table:
        return table[k]
    for _ in range(3):
        for q in QUALIFIERS:
            if k.endswith(q) and len(k) > len(q):
                cand = k[: -len(q)]
                if cand in table:
                    return table[cand]
        # drop one trailing qualifier and retry
        cut = next((k[: -len(q)] for q in QUALIFIERS if k.endswith(q) and len(k) > len(q)), None)
        if not cut:
            break
        k = cut
    return None


def prepare(expr: str) -> str:
    """Make the canonical form parseable: implicit products, unicode, powers."""
    e = expr.strip()
    e = e.replace("^", "**").replace("·", "*").replace("×", "*").replace("−", "-")
    e = re.sub(r"\bln\b|\blog\b", "log", e)
    e = re.sub(r"(\d)\s*\(", r"\1*(", e)  # 2(x) -> 2*(x)
    e = re.sub(r"(\d)\s*([A-Za-z_])", r"\1*\2", e)  # 2W -> 2*W
    e = re.sub(r"\)\s*([A-Za-z_(])", r")*\1", e)  # )( -> )*(
    e = re.sub(r"[,_{}]", "", e)  # C_L,max -> CLmax
    return e


def dim_of(node, table, unknown):
    if isinstance(node, ast.BinOp):
        left = dim_of(node.left, table, unknown)
        right = dim_of(node.right, table, unknown)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            n = node.right
            if isinstance(n, ast.Constant) and isinstance(n.value, int | float):
                return left**n.value
            return None
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if not left.same_dim(right):
                raise ValueError(f"adds {left} to {right}")
            return left
        return None
    if isinstance(node, ast.UnaryOp):
        return dim_of(node.operand, table, unknown)
    if isinstance(node, ast.Call):
        fn = getattr(node.func, "id", "")
        inner = dim_of(node.args[0], table, unknown) if node.args else None
        if fn in FUNCS and inner is not None:
            return inner ** FUNCS[fn]
        if fn in ("sin", "cos", "tan", "exp", "log", "atan", "asin"):
            return ONE
        if fn in ("max", "min", "abs", "clip"):
            dims = [dim_of(a, table, unknown) for a in node.args]
            dims = [x for x in dims if x is not None]
            return dims[0] if dims else None
        return None
    if isinstance(node, ast.Constant):
        return ONE
    if isinstance(node, ast.Name):
        d = lookup(node.id, table)
        if d is None:
            unknown.add(node.id)
        return d
    return None


def check_formula(f, table):
    form = f.get("canonical_form", "")
    if PROCEDURAL.search(form):
        return "PROCEDURAL", None, set(), ""
    # "E = C_L / C_D = L / D": take the first right-hand side only
    rhs = form.split("=")[1] if "=" in form else form
    rhs = re.sub(r"\s*\[.*?\]\s*", " ", rhs)  # drop [citation] tails
    rhs = re.sub(
        r"\s*\((?:small|large|with|where|assuming|per|note|i\.e\.)[^)]*\)", " ", rhs, flags=re.I
    )
    rhs = re.sub(r"\|([^|]+)\|", r"abs(\1)", rhs)  # |x| -> abs(x)
    rhs = re.sub(r"\b(\d+(?:\.\d+)?)\s*(m/s|m|s|kg|N|Pa|W)\b", r"\1", rhs)  # "1 m/s" literal
    rhs = rhs.split(",  ")[0]  # drop a trailing second statement
    rhs = rhs.split("(", 1)[0] if rhs.strip().startswith("(") and "=" not in rhs else rhs
    unknown: set[str] = set()
    try:
        tree = ast.parse(prepare(rhs), mode="eval").body
    except SyntaxError:
        return "UNPARSEABLE", None, unknown, ""
    try:
        d = dim_of(tree, table, unknown)
    except ValueError as exc:
        return "ADDS_UNLIKE", None, unknown, str(exc)
    if d is None:
        return ("UNKNOWN_SYMBOL" if unknown else "UNEVALUABLE"), None, unknown, ""
    return "OK", d, unknown, ""


def dimensional_rows(data):
    p = data["proposal"]
    table = build_symbols(p["quantities"])
    qbyslug = {q["slug"]: q for q in p["quantities"]}
    rows = []
    for f in p.get("formulas", []):
        status, d, unknown, msg = check_formula(f, table)
        out = qbyslug.get(f.get("output_quantity"), {})
        want = parse_unit(out.get("unit"))
        verdict = status
        if status == "OK" and want is not None:
            if not d.same_dim(want):
                verdict = "MISMATCH"
            elif abs(d.scale / want.scale - 1.0) > 1e-9:
                verdict = "SCALE"
            else:
                verdict = "BALANCES"
        rows.append((verdict, f, d, want, unknown, msg))
    return rows


def main(path):
    """Dimensional rows for an extraction JSON (the format canon_to_json.py writes)."""
    with open(path) as fh:
        return dimensional_rows(json.load(fh))


def print_dimensional(rows):
    tally: dict[str, int] = {}
    for v, *_ in rows:
        tally[v] = tally.get(v, 0) + 1
    print("dimensional check over", len(rows), "canonical formulas:", tally, "\n")
    for v, f, d, want, unknown, msg in rows:
        if v == "BALANCES":
            continue
        print(f"  {v:15s} {f['slug'][:44]:46s} {f.get('canonical_form', '')[:70]}")
        if v == "MISMATCH":
            print(f"       rhs -> {d}   declared {want}  ({f.get('output_quantity')})")
        if msg:
            print(f"       {msg}")
        if unknown and v in ("UNKNOWN_SYMBOL",):
            print(f"       unknown symbols: {sorted(unknown)[:8]}")


# --- structural check (#1181) -----------------------------------------------------------------

#: parameter names, application ids, precondition ids, world names, vocabulary terms
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
#: quantity slugs
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK = re.compile(r"\[\[([^\]|]+)\]\]")
ON_VIOLATION = {"warning", "error"}
COST = {"instant", "seconds", "minutes"}
APPLICATION_KEYS = {"id", "bind", "produce", "when", "given"}
#: roles a `given` quantity may have: supplied from outside, never computed
GIVEN_ROLES = {"input", "target"}
PRECONDITION_KEYS = {"id", "parameter", "on_violation"}
#: what an escalated gap looks like in the front matter
ESCALATED = re.compile(r"^\s*#\s*ESCALATED\b", re.M)


@dataclasses.dataclass(frozen=True)
class Entry:
    slug: str
    front: dict
    raw_front: str
    body: str

    @property
    def escalated(self) -> bool:
        return bool(ESCALATED.search(self.raw_front))


@dataclasses.dataclass(frozen=True)
class Canon:
    formulas: dict[str, Entry]
    quantities: dict[str, Entry]
    vocabulary: set[str]
    types: set[str]


@dataclasses.dataclass(frozen=True)
class Finding:
    entry: str
    field: str
    message: str
    #: True for a gap in an escalated entry: known, waiting for the maintainer
    open: bool = False


#: plain scalars YAML 1.1 reads as booleans; the canon front matter avoids them entirely
YAML11_BOOLEANS = {"on", "off", "yes", "no", "y", "n"}


def yaml11_booleans(raw: str) -> list[str]:
    """Plain keys or values a YAML 1.1 reader would turn into booleans, in order."""
    return [
        tok.value
        for tok in yaml.scan(raw)
        if isinstance(tok, yaml.ScalarToken) and tok.plain and tok.value.lower() in YAML11_BOOLEANS
    ]


def _read_entry(path: pathlib.Path) -> Entry:
    text = path.read_text(encoding="utf-8")
    _, raw, body = text.split("---", 2)
    front = yaml.safe_load(raw) or {}
    return Entry(slug=front.get("canon") or path.stem, front=front, raw_front=raw, body=body)


def _table_terms(readme: str, heading: str) -> set[str]:
    """The backticked first-column terms of the table under a README heading."""
    m = re.search(rf"^#+ [^\n]*{re.escape(heading)}[^\n]*$(.*?)(?=^#+ |\Z)", readme, re.M | re.S)
    if not m:
        return set()
    return set(re.findall(r"^\|\s*`([a-z_]+)`\s*\|", m.group(1), re.M))


def load_canon(canon_dir: pathlib.Path) -> Canon:
    root = pathlib.Path(canon_dir)
    readme = (root / "README.md").read_text(encoding="utf-8")
    formulas = {}
    for f in sorted((root / "formulas").glob("*.md")):
        e = _read_entry(f)
        formulas[e.slug] = e
    quantities = {}
    for f in sorted((root / "quantities").glob("*.md")):
        e = _read_entry(f)
        quantities[e.slug] = e
    return Canon(
        formulas=formulas,
        quantities=quantities,
        vocabulary=_table_terms(readme, "Vocabulary of `when`"),
        types=_table_terms(readme, "Quantity types"),
    )


def _links_after(body: str, label: str) -> list[str] | None:
    """Slugs linked on the line that starts with a bold label, or None if there is none."""
    m = re.search(rf"^\*\*{re.escape(label)}\*\*(.*)$", body, re.M)
    return LINK.findall(m.group(1)) if m else None


def _produces_from(body: str) -> tuple[list[str], list[str]] | None:
    m = re.search(r"\*\*Produces\*\*(.*?)\*\*from\*\*(.*)", body)
    if not m:
        return None
    return LINK.findall(m.group(1)), LINK.findall(m.group(2))


def _is_const(value) -> bool:
    return isinstance(value, dict) and "const" in value


def _effective(defaults: dict, overrides) -> dict:
    out = dict(defaults)
    if isinstance(overrides, dict):
        out.update(overrides)
    return out


def _check_parameters(e: Entry, field: str, add) -> dict:
    params = e.front.get(field)
    if not isinstance(params, dict) or not params:
        add(e.slug, field, f"missing or not a mapping of parameter -> quantity: {params!r}")
        return {}
    for name in params:
        if not isinstance(name, str) or not SNAKE.match(name):
            add(e.slug, field, f"parameter {name!r} is not snake_case")
    return params


def _check_formula(e: Entry, canon: Canon, add, gap) -> tuple[set[str], set[str]]:
    """Check one formula entry; return the quantity slugs it reads and writes."""
    q = canon.quantities
    inputs = _check_parameters(e, "inputs", add)
    outputs = _check_parameters(e, "outputs", add)
    reads: set[str] = set()
    writes: set[str] = set()

    def target(field: str, param: str, value, *, allow_const: bool) -> None:
        if value is None:
            return
        if allow_const and _is_const(value):
            src = value.get("source")
            if not isinstance(src, str) or not src.strip():
                add(e.slug, field, f"constant for {param!r} has no source")
            extra = set(value) - {"const", "source"}
            if extra:
                add(e.slug, field, f"constant for {param!r} has unknown keys {sorted(extra)}")
            return
        if not isinstance(value, str) or not KEBAB.match(value):
            add(e.slug, field, f"{param!r} is bound to {value!r}, not a quantity slug")
        elif value not in q:
            add(e.slug, field, f"{param!r} is bound to unknown quantity {value!r}")
        else:
            (reads if field.endswith(("inputs", "bind")) else writes).add(value)

    for name, value in inputs.items():
        target("inputs", name, value, allow_const=False)
    for name, value in outputs.items():
        target("outputs", name, value, allow_const=False)

    apps = e.front.get("applications")
    if apps is None:
        apps_checked = [{"id": "default"}]
    elif not isinstance(apps, list) or not apps:
        add(e.slug, "applications", "must be a non-empty list")
        apps_checked = []
    else:
        apps_checked = apps
    ids: set[str] = set()
    for app in apps_checked:
        if not isinstance(app, dict):
            add(e.slug, "applications", f"application is not a mapping: {app!r}")
            continue
        aid = app.get("id")
        where = f"application {aid}"
        if apps is not None:
            if not isinstance(aid, str) or not SNAKE.match(aid):
                add(e.slug, "applications", f"application id {aid!r} is not snake_case")
            if aid in ids:
                add(e.slug, "applications", f"application id {aid!r} is used twice")
            ids.add(aid)
            unknown = set(app) - APPLICATION_KEYS
            if unknown:
                add(e.slug, "applications", f"{where}: unknown keys {sorted(unknown)}")
        bind, produce = app.get("bind") or {}, app.get("produce") or {}
        for field, given, params in (("bind", bind, inputs), ("produce", produce, outputs)):
            if not isinstance(given, dict):
                add(e.slug, "applications", f"{where}: {field} is not a mapping")
                continue
            for name, value in given.items():
                if name not in params:
                    add(e.slug, "applications", f"{where}: {field} key {name!r} is not a parameter")
                target(f"applications {field}", name, value, allow_const=field == "bind")
        when = app.get("when")
        if when is not None and when not in canon.vocabulary:
            add(e.slug, "applications", f"{where}: when term {when!r} is not in the vocabulary")
        given = app.get("given") or []
        bound = {v for v in _effective(inputs, bind).values() if isinstance(v, str)}
        if not isinstance(given, list):
            add(e.slug, "applications", f"{where}: given is not a list")
            given = []
        for slug in given:
            if slug not in q:
                add(e.slug, "applications", f"{where}: given names unknown quantity {slug!r}")
                continue
            if q[slug].front.get("role") not in GIVEN_ROLES:
                add(
                    e.slug,
                    "applications",
                    f"{where}: given {slug!r} has role "
                    f"{q[slug].front.get('role')!r}, not input or target",
                )
            if q[slug].front.get("default") is not None:
                add(e.slug, "applications", f"{where}: given {slug!r} has a default")
            if slug not in bound:
                add(e.slug, "applications", f"{where}: given {slug!r} is not bound by it")
        for name, value in _effective(inputs, bind).items():
            if value is None:
                gap(e, "applications", f"{where}: input parameter {name!r} is not bound")
        for name, value in _effective(outputs, produce).items():
            if value is None:
                gap(e, "applications", f"{where}: output parameter {name!r} is not produced")

    for pre in e.front.get("preconditions") or []:
        if not isinstance(pre, dict) or set(pre) != PRECONDITION_KEYS:
            add(e.slug, "preconditions", f"needs exactly {sorted(PRECONDITION_KEYS)}: {pre!r}")
            continue
        if not SNAKE.match(str(pre["id"])):
            add(e.slug, "preconditions", f"id {pre['id']!r} is not snake_case")
        if pre["parameter"] not in inputs and pre["parameter"] not in outputs:
            add(e.slug, "preconditions", f"{pre['id']}: names no parameter: {pre['parameter']!r}")
        if pre["on_violation"] not in ON_VIOLATION:
            add(e.slug, "preconditions", f"{pre['id']}: on_violation {pre['on_violation']!r}")

    interval = e.front.get("uncertainty") == "interval"
    worlds = e.front.get("worlds")
    if interval and not (isinstance(worlds, list) and worlds):
        add(e.slug, "worlds", "uncertainty: interval needs a non-empty list of worlds")
    if worlds is not None and not interval:
        add(e.slug, "worlds", "worlds without uncertainty: interval")
    for w in worlds or []:
        if not isinstance(w, str) or not SNAKE.match(w):
            add(e.slug, "worlds", f"world {w!r} is not snake_case")

    cost = e.front.get("cost")
    if cost is not None and cost not in COST:
        add(e.slug, "cost", f"unknown cost class {cost!r}")

    # front matter against the prose line and the output field
    line = _produces_from(e.body)
    if line is None:
        add(e.slug, "body", "no '**Produces** … **from** …' line")
    else:
        produces, sources = line
        if set(sources) != reads:
            add(e.slug, "inputs", _diff("from line", set(sources), reads))
        if set(produces) != writes:
            add(e.slug, "outputs", _diff("Produces line", set(produces), writes))
    declared = {o.strip() for o in str(e.front.get("output") or "").split(",") if o.strip()}
    if declared != writes:
        add(e.slug, "outputs", _diff("output field", declared, writes))
    return reads, writes


def _diff(name: str, prose: set[str], front: set[str]) -> str:
    parts = []
    if prose - front:
        parts.append(f"only in the {name}: {sorted(prose - front)}")
    if front - prose:
        parts.append(f"only in the front matter: {sorted(front - prose)}")
    return "; ".join(parts)


def check_structure(canon: Canon) -> list[Finding]:
    findings: list[Finding] = []

    def add(entry: str, field: str, message: str) -> None:
        findings.append(Finding(entry, field, message))

    def gap(e: Entry, field: str, message: str) -> None:
        findings.append(Finding(e.slug, field, message, open=e.escalated))

    used_by: dict[str, set[str]] = {s: set() for s in canon.quantities}
    produced_by: dict[str, set[str]] = {s: set() for s in canon.quantities}
    for slug, e in canon.formulas.items():
        reads, writes = _check_formula(e, canon, add, gap)
        for r in reads:
            used_by[r].add(slug)
        for w in writes:
            produced_by[w].add(slug)

    for slug, e in canon.quantities.items():
        t = e.front.get("type")
        if t is None:
            add(slug, "type", "missing")
        elif t not in canon.types:
            add(slug, "type", f"{t!r} is not in the type set of the README")
        if "default" in e.front and e.front["default"] is not None:
            d = e.front["default"]
            if not isinstance(d, dict) or set(d) != {"value", "source"}:
                add(slug, "default", f"must be {{value, source}}: {d!r}")
            elif not isinstance(d["source"], str) or not d["source"].strip():
                add(slug, "default", "has no source")
        for label, field, actual in (
            ("Used by.", "used_by", used_by[slug]),
            ("Produced by.", "produced_by", produced_by[slug]),
        ):
            listed = set(_links_after(e.body, label) or [])
            if listed != actual:
                add(slug, field, _diff(f"'{label}' line", listed, actual))
    return findings


def cli(argv: list[str]) -> int:
    target = pathlib.Path(argv[0]) if argv else DEFAULT_CANON
    if target.suffix == ".json":
        print_dimensional(main(target))
        return 0
    print_dimensional(dimensional_rows(build_canon_json(target)))
    canon = load_canon(target)
    findings = check_structure(canon)
    errors = [f for f in findings if not f.open]
    opened = [f for f in findings if f.open]
    print(
        f"structural check over {len(canon.formulas)} formulas and "
        f"{len(canon.quantities)} quantities: {len(errors)} errors, {len(opened)} open (escalated)"
    )
    for title, group in (("errors", errors), ("open (escalated)", opened)):
        if group:
            print(f"\n  {title}:")
        for f in group:
            print(f"    {f.entry} [{f.field}] {f.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
