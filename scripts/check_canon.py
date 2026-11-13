"""Checks for the calculation canon: dimensions and authoring.

Three checks, all authoring aids for the canon document (`_reversa_sdd/calculations/canon/`):

**Dimensional.** Parses each canonical form, substitutes the declared unit of every symbol
from the quantity register, and evaluates the dimension of the right-hand side. Reports a
formula whose result does not match its declared output quantity, or which adds two
quantities of unlike dimension. Informational; it does not fail the run.

**Dimensional, per statement (#1379).** Reads every line of every canonical form, also the
multi-line procedures and optimisation problems the first check leaves out, and checks each
statement `lhs = rhs` it can parse. Symbols resolve through the formula's own bindings first.
A dimension that does not balance, or a quantity in degrees that meets radians without a
visible conversion (`180/pi`, `pi/180`), fails the run; what it cannot read is counted.

**Authoring.** Cross-checks the front matter against the prose the importer never reads
(`python -m aero_kernel.importer` owns every structural rule, #1174): the "Produces … from"
line of a formula against its `inputs` / `outputs` / `applications`, the `output` field
against what the formula produces, the quantities' "Used by" / "Produced by" links, and the
README examples against the entries they show. A disagreement fails the run.

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

LINK = re.compile(r"\[\[([^\]|]+)\]\]")
#: the machine-readable keys a README example must reproduce in full (when/given are compared
#: as part of applications)
EXAMPLE_KEYS_FORMULA = (
    "inputs",
    "outputs",
    "applications",
    "preconditions",
    "postconditions",
    "embeds",
    "variables",
    "optional",
    "uncertainty",
    "worlds",
    "cost",
)
EXAMPLE_KEYS_QUANTITY = ("type", "uncertainty", "positive")


@dataclasses.dataclass(frozen=True)
class Entry:
    slug: str
    front: dict
    body: str


@dataclasses.dataclass(frozen=True)
class Canon:
    formulas: dict[str, Entry]
    quantities: dict[str, Entry]
    #: README "One example per kind": (slug, parsed example) pairs
    examples: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class Finding:
    entry: str
    field: str
    message: str


def _read_entry(path: pathlib.Path) -> Entry:
    """An entry's front matter and prose; an unreadable front matter is left empty (the importer
    reports it)."""
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:  # no front matter between '---' lines: the importer reports it
        return Entry(slug=path.stem, front={}, body=text)
    _, raw, body = parts
    try:
        front = yaml.safe_load(raw)
    except yaml.YAMLError:
        front = None
    return Entry(slug=path.stem, front=front if isinstance(front, dict) else {}, body=body)


def load_canon(canon_dir: pathlib.Path) -> Canon:
    root = pathlib.Path(canon_dir)

    def read_all(sub: str) -> dict[str, Entry]:
        return {f.stem: _read_entry(f) for f in sorted((root / sub).glob("*.md"))}

    readme = (root / "README.md").read_text(encoding="utf-8")
    return Canon(
        formulas=read_all("formulas"),
        quantities=read_all("quantities"),
        examples=_readme_examples(readme),
    )


def _readme_examples(readme: str) -> list:
    """The YAML examples of the README section "One example per kind", each with the slug the
    sentence before it names in parentheses."""
    m = re.search(r"^#+ One example per kind[^\n]*$(.*?)(?=^#{1,3} |\Z)", readme, re.M | re.S)
    if not m:
        return []
    out, last = [], 0
    for block in re.finditer(r"```yaml\n(.*?)```", m.group(1), re.S):
        slug = re.search(r"\(`([a-z0-9-]+)`\)", m.group(1)[last : block.start()])
        out.append((slug.group(1) if slug else None, yaml.safe_load(block.group(1)) or {}))
        last = block.end()
    return out


def _links_after(body: str, label: str) -> list[str] | None:
    """Slugs linked on the line that starts with a bold label, or None if there is none."""
    m = re.search(rf"^\*\*{re.escape(label)}\*\*(.*)$", body, re.M)
    return LINK.findall(m.group(1)) if m else None


def _produces_from(body: str) -> tuple[list[str], list[str]] | None:
    m = re.search(r"\*\*Produces\*\*(.*?)\*\*from\*\*(.*)", body)
    if not m:
        return None
    return LINK.findall(m.group(1)), LINK.findall(m.group(2))


def _slugs(mapping, known) -> set[str]:
    """The quantity slugs a parameter mapping names, ignoring constants and unknown names."""
    if not isinstance(mapping, dict):
        return set()
    return {v for v in mapping.values() if isinstance(v, str) and v in known}


def _reads_writes(e: Entry, known) -> tuple[set[str], set[str]]:
    """The quantities a formula reads and writes: what its applications actually bind and
    produce (a default overridden by every application is never read)."""
    inputs, outputs = e.front.get("inputs") or {}, e.front.get("outputs") or {}
    applications = e.front.get("applications")
    if not isinstance(applications, list):
        applications = [{}]
    reads: set[str] = set()
    writes: set[str] = set()
    for app in applications:
        app = app if isinstance(app, dict) else {}
        for given, overrides, target in (
            (inputs, app.get("bind"), reads),
            (outputs, app.get("produce"), writes),
        ):
            merged = dict(given) if isinstance(given, dict) else {}
            if isinstance(overrides, dict):
                merged.update(overrides)
            target |= _slugs(merged, known)
    return reads, writes


def _diff(name: str, prose: set[str], front: set[str]) -> str:
    parts = []
    if prose - front:
        parts.append(f"only in the {name}: {sorted(prose - front)}")
    if front - prose:
        parts.append(f"only in the front matter: {sorted(front - prose)}")
    return "; ".join(parts)


def check_authoring(canon: Canon) -> list[Finding]:
    findings: list[Finding] = []

    def add(entry: str, field: str, message: str) -> None:
        findings.append(Finding(entry, field, message))

    used_by: dict[str, set[str]] = {s: set() for s in canon.quantities}
    produced_by: dict[str, set[str]] = {s: set() for s in canon.quantities}
    for slug, e in canon.formulas.items():
        reads, writes = _reads_writes(e, canon.quantities)
        for r in reads:
            used_by[r].add(slug)
        for w in writes:
            produced_by[w].add(slug)
        line = _produces_from(e.body)
        if line is None:
            add(slug, "body", "no '**Produces** … **from** …' line")
        else:
            produces, sources = line
            if set(sources) != reads:
                add(slug, "inputs", _diff("from line", set(sources), reads))
            if set(produces) != writes:
                add(slug, "outputs", _diff("Produces line", set(produces), writes))
        declared = {o.strip() for o in str(e.front.get("output") or "").split(",") if o.strip()}
        if declared != writes:
            add(slug, "outputs", _diff("output field", declared, writes))

    for slug, e in canon.quantities.items():
        for label, field, actual in (
            ("Used by.", "used_by", used_by[slug]),
            ("Produced by.", "produced_by", produced_by[slug]),
        ):
            listed = set(_links_after(e.body, label) or [])
            if listed != actual:
                add(slug, field, _diff(f"'{label}' line", listed, actual))

    for slug, example in canon.examples:
        entry = canon.formulas.get(slug) or canon.quantities.get(slug)
        if entry is None:
            add("README", "examples", f"example names no entry: {slug!r}")
            continue
        keys = EXAMPLE_KEYS_FORMULA if slug in canon.formulas else EXAMPLE_KEYS_QUANTITY
        for key in dict.fromkeys([*example, *keys]):
            if entry.front.get(key) != example.get(key):
                add("README", "examples", f"{slug}: {key} differs from the entry's front matter")
    return findings


# --- dimensional check per statement, through the formula's bindings (#1379) -------------------

#: a `name(args)` call that is not a mathematical function is a quantity taken at a point:
#: `L(V, alpha)` has the dimension of `L`
_MATH_CALLS = (
    "sqrt",
    "cbrt",
    "sin",
    "cos",
    "tan",
    "exp",
    "log",
    "atan",
    "asin",
    "max",
    "min",
    "abs",
)
_POINT_CALL = re.compile(r"\b([A-Za-z_][A-Za-z0-9_,]*)\(([^()=]*)\)")
#: a plain `=`: never `:=`, `>=`, `<=`, `==`
_EQUALS = re.compile(r"(?<![:<>=!])=(?!=)")
#: an explicit conversion between degrees and radians
_ANGLE_CONVERSION = re.compile(r"180\s*/\s*pi|pi\s*/\s*180")
_NUMBER = re.compile(r"^[-+]?\d+(\.\d+)?(e[-+]?\d+)?$", re.I)
_ANGLE_SLOT = 7  # index of ANG in dimensions.BASES
#: verdicts of the statement check that fail the run
STATEMENT_ERRORS = ("MISMATCH", "ANGLE", "ADDS_UNLIKE")


@dataclasses.dataclass(frozen=True)
class Statement:
    """One `lhs = rhs` statement of a canonical form and what the check made of it.

    Verdicts: `OK`; `DEFINES` (the left side is a name the register does not know, so the
    statement defines it for the rest of the form); `CONSTANT` (one side is a number: nothing to
    balance); `MISMATCH`, `ANGLE`, `ADDS_UNLIKE` (findings); `UNKNOWN_SYMBOL`, `UNPARSEABLE` (not
    judged).
    """

    formula: str
    text: str
    verdict: str
    detail: str = ""


def _key(symbol: str) -> str:
    """A symbol without its punctuation, case kept: `C_L,max` -> `CLmax`."""
    return re.sub(r"[^A-Za-z0-9]", "", symbol or "")


def _statements(form: str) -> list[str]:
    """The `lhs = rhs` statements of a canonical form: every line segment with exactly one plain
    `=`, without its label, its comment, its citation and a parenthesis around the whole."""
    out: list[str] = []
    for raw in form.splitlines():
        line = raw.split(" # ")[0]
        line = re.sub(r"\[[^\]]*\]", " ", line)
        line = re.sub(r"\s*(?<![:<>=!])=(?!=)\s*", " = ", line)  # aligned `name    = expr`
        for seg in re.split(r"\s{2,}|;\s+", line):
            seg = re.sub(
                r"^[^=()]*?:\s+", "", seg.strip()
            )  # "subject to:", "route B:", "world avl:"
            seg = seg.strip().rstrip(",").strip()
            if seg.startswith("(") and seg.endswith(")") and seg.count("(") == 1:
                seg = seg[1:-1].strip()
            if len(_EQUALS.findall(seg)) == 1 and seg.count("(") == seg.count(")"):
                out.append(seg)
    return out


def _collapse_point_calls(expr: str) -> str:
    """`L(V, alpha)` -> `L`; mathematical functions keep their arguments."""
    previous = None
    while previous != expr:
        previous = expr
        expr = _POINT_CALL.sub(
            lambda m: m.group(0) if m.group(1) in _MATH_CALLS else m.group(1), expr
        )
    return expr


def _parse_side(side: str) -> ast.expr:
    side = re.sub(r"\|([^|]+)\|", r"abs(\1)", side)
    side = _collapse_point_calls(side).replace("'", "prime")
    return ast.parse(prepare(side), mode="eval").body


@dataclasses.dataclass
class _Symbols:
    """The symbols one formula may use, and the declared unit behind each.

    A name resolves through the formula's own bindings first (parameter name, or the symbol of a
    bound quantity), then through the register. Case is kept: `Q` is not `q`. A name of more than
    one letter may also match without regard to case and with a trailing qualifier dropped.
    """

    local: dict[str, tuple[Dim, str]]
    register: dict[str, tuple[Dim, str]]

    def resolve(self, name: str) -> tuple[Dim, str] | None:
        key = _key(name)
        for table in (self.local, self.register):
            if key in table:
                return table[key]
        if len(key) < 2:
            return None
        for table in (self.local, self.register):
            folded = {k.lower(): v for k, v in table.items() if len(k) > 1}
            cand = key.lower()
            for _ in range(3):
                if cand in folded:
                    return folded[cand]
                cut = next(
                    (
                        cand[: -len(q)]
                        for q in QUALIFIERS
                        if cand.endswith(q) and len(cand) > len(q) + 1
                    ),
                    None,
                )
                if cut is None:
                    break
                cand = cut
        return None


def _register_symbols(canon: Canon) -> dict[str, tuple[Dim, str]]:
    table: dict[str, tuple[Dim, str]] = {}
    for slug, q in canon.quantities.items():
        unit = q.front.get("unit")
        d = parse_unit(str(unit)) if unit is not None else None
        if d is None:
            continue
        for name in (q.front.get("symbol"), slug):
            key = _key(str(name)) if name else ""
            if key and key not in MATH_CONSTANTS:
                table.setdefault(key, (d, str(unit)))
    return table


def _formula_symbols(e: Entry, canon: Canon) -> dict[str, tuple[Dim, str]]:
    """Parameter names and bound symbols of one formula, over all its applications."""
    mappings = [e.front.get("inputs"), e.front.get("outputs")]
    applications = e.front.get("applications")
    for app in applications if isinstance(applications, list) else []:
        if isinstance(app, dict):
            mappings += [app.get("bind"), app.get("produce")]
    table: dict[str, tuple[Dim, str]] = {}
    for mapping in mappings:
        for param, slug in (mapping or {}).items() if isinstance(mapping, dict) else ():
            q = canon.quantities.get(slug) if isinstance(slug, str) else None
            unit = q.front.get("unit") if q is not None else None
            d = parse_unit(str(unit)) if unit is not None else None
            if q is None or d is None:
                continue
            for name in (param, q.front.get("symbol")):
                key = _key(str(name)) if name else ""
                if key and key not in MATH_CONSTANTS:
                    table.setdefault(key, (d, str(unit)))
    return table


def _judge(lhs: str, rhs: str, text: str, symbols: _Symbols) -> tuple[str, str]:
    if _NUMBER.match(lhs.strip()) or _NUMBER.match(rhs.strip()):
        return "CONSTANT", ""
    try:
        trees = (_parse_side(lhs), _parse_side(rhs))
    except SyntaxError:
        return "UNPARSEABLE", ""
    names = {n.id for tree in trees for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names -= set(_MATH_CALLS) | MATH_CONSTANTS
    resolved = {n: symbols.resolve(n) for n in names}
    unknown = sorted(n for n, r in resolved.items() if r is None)
    left_name = trees[0].id if isinstance(trees[0], ast.Name) else None
    table = {norm(n): r[0] for n, r in resolved.items() if r is not None}
    table.update(dict.fromkeys(MATH_CONSTANTS, ONE))
    if len(table) < len({n for n, r in resolved.items() if r is not None}) + len(MATH_CONSTANTS):
        return "UNPARSEABLE", "two symbols of the statement differ only in case"
    sink: set[str] = set()
    try:
        if unknown == [left_name]:
            right = dim_of(trees[1], table, sink)
            if right is None:
                return "UNPARSEABLE", ""
            symbols.local[_key(left_name)] = (right, "")
            return "DEFINES", ""
        if unknown:
            return "UNKNOWN_SYMBOL", ", ".join(unknown)
        left, right = dim_of(trees[0], table, sink), dim_of(trees[1], table, sink)
    except ValueError as exc:
        return "ADDS_UNLIKE", str(exc)
    if left is None or right is None:
        return "UNPARSEABLE", ""
    differ = [a - b for a, b in zip(left.e, right.e, strict=True)]
    if any(abs(x) > 1e-9 for i, x in enumerate(differ) if i != _ANGLE_SLOT):
        return "MISMATCH", f"{left}  =  {right}"
    units = [r[1] for r in resolved.values() if r is not None]
    degrees = any(re.search(r"deg|°", u) for u in units)
    radians = any(re.search(r"\brad\b", u) for u in units)
    angle_differs = abs(differ[_ANGLE_SLOT]) > 1e-9
    if degrees and (angle_differs or radians) and not _ANGLE_CONVERSION.search(text):
        return "ANGLE", "a quantity in degrees meets radians and the statement converts nothing"
    return "OK", ""


def check_statements(canon: Canon) -> list[Statement]:
    """Check every `lhs = rhs` statement of every canonical form for its dimension, and for a
    quantity in degrees that meets radians without a visible conversion (`180/pi`, `pi/180`).

    Symbols resolve through the formula's own bindings first. A name the register does not know
    is defined by the first statement that has it alone on the left. A statement that does not
    parse, or that uses an unknown symbol, is reported as such and judged no further.
    """
    register = _register_symbols(canon)
    rows: list[Statement] = []
    for slug, e in canon.formulas.items():
        m = re.search(r"\*\*Canonical form\*\*\s*\n+```[a-z]*\n(.*?)\n```", e.body, re.S)
        if not m:
            continue
        symbols = _Symbols(local=_formula_symbols(e, canon), register=register)
        for text in _statements(m.group(1)):
            lhs, rhs = _EQUALS.split(text)
            verdict, detail = _judge(lhs, rhs, text, symbols)
            rows.append(Statement(slug, text, verdict, detail))
    return rows


def print_statements(rows: list[Statement]) -> int:
    """Print the per-statement findings; return the number that fail the run."""
    tally: dict[str, int] = {}
    for r in rows:
        tally[r.verdict] = tally.get(r.verdict, 0) + 1
    print("\ndimensional check over", len(rows), "statements of the canonical forms:", tally)
    failing = [r for r in rows if r.verdict in STATEMENT_ERRORS]
    for r in failing:
        print(f"    {r.formula} [{r.verdict}] {r.text}")
        if r.detail:
            print(f"         {r.detail}")
    return len(failing)


def cli(argv: list[str]) -> int:
    target = pathlib.Path(argv[0]) if argv else DEFAULT_CANON
    if target.suffix == ".json":
        print_dimensional(main(target))
        return 0
    print_dimensional(dimensional_rows(build_canon_json(target)))
    canon = load_canon(target)
    statement_errors = print_statements(check_statements(canon))
    findings = check_authoring(canon)
    print(
        f"authoring check over {len(canon.formulas)} formulas and "
        f"{len(canon.quantities)} quantities: {len(findings)} errors"
    )
    for f in findings:
        print(f"    {f.entry} [{f.field}] {f.message}")
    return 1 if findings or statement_errors else 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
