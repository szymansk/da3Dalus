"""Checks for the calculation canon: dimensions and authoring.

Three checks, all authoring aids for the canon document (`_reversa_sdd/calculations/canon/`):

**Dimensional.** Parses each canonical form, substitutes the declared unit of every symbol
from the quantity register, and evaluates the dimension of the right-hand side. Reports a
formula whose result does not match its declared output quantity, or which adds two
quantities of unlike dimension. Informational; it does not fail the run.

**Dimensional, per statement (#1379).** Reads every line of every canonical form, also the
multi-line procedures and optimisation problems the first check leaves out, and checks each
statement `lhs = rhs` it can read. Symbols resolve through the formula's own bindings first.
A dimension that does not balance, a sum of unlike quantities, a quantity in degrees that meets
radians without a visible conversion (`180/pi`, `pi/180`), or millimetres that meet metres
without one, fails the run. What the check cannot read reliably it never judges: such a
statement is counted as unparseable or as using an unknown symbol.

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
import math
import pathlib
import re
import sys
import unicodedata

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from canon_to_json import build as build_canon_json  # noqa: E402
from dimensions import BASES, ONE, Dim, parse_unit  # noqa: E402

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


#: how many trailing qualifiers a symbol may carry: `C_L,max,clean,cfg`
_QUALIFIER_DEPTH = 3
#: two exponents, or two length scales, closer than this are the same
_TOLERANCE = 1e-9
#: a name of fewer letters matches only as it stands, case kept: `Q` is not `q`
_SHORTEST_FOLDED_NAME = 2


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
    for _ in range(_QUALIFIER_DEPTH):
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
            elif abs(d.scale / want.scale - 1.0) > _TOLERANCE:
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

#: the mathematical functions a statement may call, by what they ask of their argument
_ROOTS = FUNCS
_TRIGONOMETRIC = ("sin", "cos", "tan")
_OF_A_PURE_NUMBER = ("exp", "log", "atan", "asin")
_OVER_LIKE_ARGUMENTS = ("max", "min")
_ABSOLUTE = "abs"
_MATH_CALLS = (*_ROOTS, *_TRIGONOMETRIC, *_OF_A_PURE_NUMBER, *_OVER_LIKE_ARGUMENTS, _ABSOLUTE)
#: other spellings a canonical form uses for a function above
_CALL_ALIASES = {"ln": "log"}
#: the only named number of the statement check; every other name is a quantity (`tau` and
#: `euler` are ordinary names here)
_NAMED_NUMBERS = {"pi": math.pi}
#: a plain `=`: never `:=`, `>=`, `<=`, `==`
_EQUALS = re.compile(r"(?<![:<>=!])=(?!=)")
#: an explicit conversion between degrees and radians
_ANGLE_CONVERSION = re.compile(r"180\s*/\s*pi|pi\s*/\s*180")
#: an explicit conversion between length scales: a power of ten other than one
_SCALE_CONVERSION = re.compile(
    r"(?<![\w.])(?:10+(?:\.0*)?|0?\.0*1|1(?:\.0*)?e[-+]?\d+)(?![\w.])", re.I
)
_ANGLE_SLOT = BASES.index("ANG")
#: verdicts of the statement check that fail the run
STATEMENT_ERRORS = ("MISMATCH", "ANGLE", "ADDS_UNLIKE", "SCALE")
#: marks of a unit in degrees / in radians, and what a defined name carries of them
_IN_DEGREES = re.compile(r"deg|°")
_IN_RADIANS = re.compile(r"\brad\b")
_DEGREES, _RADIANS, _NO_ANGLE_UNIT = "deg", "rad", ""

_NUMBER_TOKEN = re.compile(r"(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?")
_OPERATOR_SPELLINGS = {"·": "*", "×": "*", "−": "-"}
_OPENING = {"(": ")", "[": "]"}
_CLOSING = tuple(_OPENING.values())
_ALL_OPENING, _ALL_CLOSING = "([{", ")]}"
#: the comment that ends a line: a `#` that stands alone (`(#1208)` is none)
_COMMENT = re.compile(r"(?:^|\s)#(?:\s|$)")
#: a group in square brackets at the end of a line, set off by a blank
_TRAILING_BRACKET = re.compile(r"(?<=\S)\s+\[([^\[\]]*)\]$")
#: what separates two statements on one line: two blanks or more, or a semicolon
_SEPARATOR = re.compile(r";\s+|;$|\s{2,}")
#: an operator left dangling at the start or the end of a piece: the piece is no statement of
#: its own (`->` is no operator)
_OPENS_WITH_OPERATOR = re.compile(r"^(?:[+*/^=)\]·×−]|-(?!>))")
_ENDS_WITH_OPERATOR = re.compile(r"[-+*/^=(\[·×−]$")
#: a relation that is no plain `=`
_ASSIGNMENT = re.compile(r":=")
_RELATION = re.compile(r":=|[<>]")
#: a label before a statement: "subject to:", "route B:", "world avl:"
_LABEL = re.compile(r"^[^=()]*?:\s+")
_LABEL_END, _LIST_END = ":", ","


@dataclasses.dataclass(frozen=True)
class Statement:
    """One `lhs = rhs` statement of a canonical form and what the check made of it.

    Verdicts: `OK`; `DEFINES` (the left side is a name the register does not know, so the
    statement defines it for the rest of the form); `CONSTANT` (one side is a number: nothing to
    balance); `MISMATCH`, `ANGLE`, `ADDS_UNLIKE`, `SCALE` (findings); `UNKNOWN_SYMBOL`,
    `UNPARSEABLE` (not judged).
    """

    formula: str
    text: str
    verdict: str
    detail: str = ""


class _Unreadable(Exception):
    """The statement is not in a form the check reads reliably: it is not judged."""


class _Finding(Exception):
    """The statement is wrong in itself, whatever stands on its other side."""

    def __init__(self, verdict: str, detail: str):
        super().__init__(detail)
        self.verdict = verdict
        self.detail = detail


def _key(symbol: str) -> str:
    """A symbol without its punctuation, case kept: `C_L,max` -> `CLmax`."""
    return re.sub(r"[^A-Za-z0-9]", "", symbol or "")


def _name_key(name: str) -> str:
    """The key of a name in a statement: `K_v'` -> `Kvprime`."""
    return _key(name.replace("'", "prime"))


# -- the statements of a canonical form --


def _depth_zero(text: str) -> list[bool]:
    """For every character, whether it stands outside all parentheses, brackets and braces."""
    depth, flags = 0, []
    for ch in text:
        if ch in _ALL_CLOSING:
            depth -= 1
        flags.append(depth <= 0)
        if ch in _ALL_OPENING:
            depth += 1
    return flags


def _left_open(text: str) -> bool:
    """Whether a parenthesis, bracket or brace of the text is still open at its end."""
    return sum(ch in _ALL_OPENING for ch in text) > sum(ch in _ALL_CLOSING for ch in text)


def _assigns(text: str) -> bool:
    """Whether a `:=` stands outside all parentheses: an assignment, no statement to balance."""
    outside = _depth_zero(text)
    return any(outside[m.start()] for m in _ASSIGNMENT.finditer(text))


def _wrapped(text: str) -> bool:
    """Whether one pair of parentheses encloses the whole text."""
    if not (text.startswith("(") and text.endswith(")")):
        return False
    return not any(_depth_zero(text)[1:-1])


def _reads_as_expression(text: str) -> bool:
    try:
        _Parser(text).expression_to_the_end()
    except _Unreadable:
        return False
    return True


def _without_comment_and_citation(line: str) -> str:
    """A line without its `# comment` and without a trailing `[citation]`. A trailing bracket
    that reads as an expression (`[1 + V]`) is no citation and stays."""
    line = _COMMENT.split(line, maxsplit=1)[0].rstrip()
    while (m := _TRAILING_BRACKET.search(line)) and not _reads_as_expression(m.group(1)):
        line = line[: m.start()]
    return line


def _logical_lines(form: str) -> list[str]:
    """The lines of a form, a line joined to the one before while that one has an open
    parenthesis, or while an operator dangles between the two and the line states nothing of its
    own (no `=`, no other relation)."""
    out: list[str] = []
    for raw in form.splitlines():
        line = _without_comment_and_citation(raw).strip()
        if not line:
            continue
        dangling = out and (_ENDS_WITH_OPERATOR.search(out[-1]) or _OPENS_WITH_OPERATOR.match(line))
        states = _EQUALS.search(line) or _RELATION.search(line)
        if out and (_left_open(out[-1]) or (dangling and not states)):
            out[-1] = f"{out[-1]} {line}"
        else:
            out.append(line)
    return out


@dataclasses.dataclass
class _Piece:
    """A part of a line between two separators. `kind`: `statement` (has a plain `=`), `loose`
    (text of no recognised kind: it may belong to the statement beside it), or `aside` (a label,
    another relation, a remark: it belongs to no statement). `detached`: a semicolon stands
    before it."""

    text: str
    kind: str
    detached: bool


def _split(line: str) -> list[tuple[str, bool]]:
    """Cut a line at its separators outside all parentheses; rejoin where an operator dangles
    at the cut, so that no statement is cut in two. Each part with whether a semicolon stands
    before it."""
    outside = _depth_zero(line)
    parts: list[tuple[str, bool]] = []
    start, detached = 0, False
    for m in _SEPARATOR.finditer(line):
        if not outside[m.start()]:
            continue
        parts.append((line[start : m.start()], detached))
        start, detached = m.end(), m.group().startswith(";")
    parts.append((line[start:], detached))
    joined: list[tuple[str, bool]] = []
    for text, cut_by_semicolon in parts:
        text = text.strip()
        if not text:
            continue
        dangling = joined and (
            _ENDS_WITH_OPERATOR.search(joined[-1][0]) or _OPENS_WITH_OPERATOR.match(text)
        )
        if dangling and not cut_by_semicolon:
            joined[-1] = (f"{joined[-1][0]} {text}", joined[-1][1])
        else:
            joined.append((text, cut_by_semicolon))
    return joined


def _pieces(line: str) -> list[_Piece]:
    pieces: list[_Piece] = []

    def label_ends_here() -> None:
        """What stands loose before a label colon is part of the label."""
        for p in reversed(pieces):
            if p.kind != "loose":
                break
            p.kind = "aside"

    for text, detached in _split(line):
        text = text.rstrip(_LIST_END).strip()
        if text.startswith(_LABEL_END + " "):  # `s_max     : V_S0(s_max) = V_app`
            label_ends_here()
            text = text[1:].strip()
        if _assigns(text):
            kind = "aside"
        elif _EQUALS.search(text):
            kind = "statement"
        elif text.endswith(_LABEL_END):
            label_ends_here()
            kind = "aside"
        elif _RELATION.search(text) or (_wrapped(text) and not _reads_as_expression(text)):
            kind = "aside"
        else:
            kind = "loose"
        if text:
            pieces.append(_Piece(text, kind, detached))
    return pieces


def _line_statements(line: str) -> list[str]:
    pieces = _pieces(line)
    out: list[str] = []
    for i, piece in enumerate(pieces):
        if piece.kind != "statement":
            continue
        text = piece.text
        before = pieces[i - 1] if i else None
        after = pieces[i + 1] if i + 1 < len(pieces) else None
        # loose text beside a statement may be a part of it: the two are read together, and
        # what cannot be read together is unparseable
        if before is not None and before.kind == "loose" and not piece.detached:
            text = f"{before.text} {text}"
        if after is not None and after.kind == "loose" and not after.detached:
            text = f"{text} {after.text}"
        if _wrapped(text):  # `(V = V_app)`: a line of its own inside the parentheses
            out += _line_statements(text[1:-1].strip())
            continue
        text = _LABEL.sub("", text)
        out.append(re.sub(r"\s+", " ", _EQUALS.sub(" = ", text)).strip())
    return out


def _statements(form: str) -> list[str]:
    """The statements of a canonical form: every piece of a line with a plain `=`.

    Dropped: a `# comment`; a trailing `[citation]`; a label that ends in a colon; a piece with
    another relation (`:=`, `>=`); a parenthesised remark set off by two blanks. A citation or a
    remark is only what does not read as an expression: `[1 + V]` and `(m)` stay in the
    statement. A line is cut in several statements at two blanks or a semicolon, never where an
    operator dangles at the cut; text of no recognised kind beside a statement stays with it. A
    piece with more than one `=` is returned as it stands, for the caller to report.
    """
    return [s for line in _logical_lines(form) for s in _line_statements(line)]


# -- reading one side of a statement --


@dataclasses.dataclass(frozen=True)
class _Number:
    value: float


@dataclasses.dataclass(frozen=True)
class _Name:
    name: str


@dataclasses.dataclass(frozen=True)
class _Negation:
    operand: object


@dataclasses.dataclass(frozen=True)
class _Operation:
    op: str
    left: object
    right: object


@dataclasses.dataclass(frozen=True)
class _Call:
    function: str
    arguments: tuple


@dataclasses.dataclass(frozen=True)
class _Token:
    kind: str  # "number", "name", or the character itself
    text: str
    spaced: bool  # a blank stands before it


def _is_name_character(ch: str) -> bool:
    """Letters and digits of any script, the underscore, and combining marks (`V̄`)."""
    return ch.isalnum() or ch == "_" or unicodedata.category(ch).startswith("M")


def _tokens(text: str) -> list[_Token]:
    out: list[_Token] = []
    i, spaced = 0, False
    while i < len(text):
        ch = _OPERATOR_SPELLINGS.get(text[i], text[i])
        if ch.isspace():
            i, spaced = i + 1, True
            continue
        number = _NUMBER_TOKEN.match(text, i) if ch.isascii() else None
        if number:
            out.append(_Token("number", number.group(), spaced))
            i = number.end()
        elif ch.isalpha() or ch == "_":
            end = i
            while end < len(text) and (
                _is_name_character(text[end])
                # `C_L,max`: a comma inside a name has no blank after it
                or (text[end] == "," and end + 1 < len(text) and _is_name_character(text[end + 1]))
            ):
                end += 1
            while end < len(text) and text[end] == "'":
                end += 1
            out.append(_Token("name", text[i:end], spaced))
            i = end
        elif text.startswith("**", i):
            out.append(_Token("^", "**", spaced))
            i += 2
        elif ch in "+-*/^,|" or ch in _OPENING or ch in _CLOSING:
            out.append(_Token(ch, ch, spaced))
            i += 1
        else:
            raise _Unreadable(f"unexpected character {text[i]!r}")
        spaced = False
    return out


class _Parser:
    """Reads one side of a statement into a tree.

    Products are written with `*`; a number directly before a name or a parenthesis (`2W`,
    `2(x)`) and two adjacent groups (`(a)(b)`) multiply too. Two terms separated by a blank only
    are not read as a product: that is prose as often as it is a product. `name(a, b)` with a
    plain list of names and numbers is the quantity `name` taken at a point; any other
    parenthesis directly after a name is unreadable.
    """

    def __init__(self, text: str):
        self.tokens = _tokens(text)
        self.at = 0
        #: per open group: whether its commas separate the arguments of `max` / `min`
        self.groups: list[bool] = []

    def peek(self) -> _Token | None:
        return self.tokens[self.at] if self.at < len(self.tokens) else None

    def take(self, kind: str | None = None) -> _Token:
        token = self.peek()
        if token is None or (kind is not None and token.kind != kind):
            raise _Unreadable(f"expected {kind or 'a term'}")
        self.at += 1
        return token

    def expression_to_the_end(self):
        tree = self.sum()
        if self.peek() is not None:
            raise _Unreadable(f"unexpected {self.peek().text!r}")
        return tree

    def sum(self):
        left = self.product()
        while (token := self.peek()) is not None and token.kind in "+-":
            self.take()
            left = _Operation(token.kind, left, self.product())
        return left

    def product(self):
        left = self.signed()
        while (token := self.peek()) is not None:
            if token.kind in "*/":
                self.take()
                left = _Operation(token.kind, left, self.signed())
            elif self._multiplies_unwritten(token):
                left = _Operation("*", left, self.signed())
            elif token.kind in ("number", "name") or token.kind in _OPENING:
                raise _Unreadable("two terms with no operator between them")
            else:
                break
        return left

    def _multiplies_unwritten(self, token: _Token) -> bool:
        before = self.tokens[self.at - 1]
        if token.spaced:
            return False
        if before.kind == "number":
            return token.kind == "name" or token.kind in _OPENING
        return before.kind in _CLOSING and token.kind in _OPENING

    def signed(self):
        token = self.peek()
        if token is not None and token.kind in "+-":
            self.take()
            operand = self.signed()
            return _Negation(operand) if token.kind == "-" else operand
        return self.power()

    def power(self):
        base = self.primary()
        token = self.peek()
        if token is not None and token.kind == "^":
            self.take()
            return _Operation("^", base, self.signed())
        return base

    def primary(self):
        token = self.take()
        if token.kind == "number":
            return _Number(float(token.text))
        if token.kind in _OPENING:
            return self.group(token, variadic=False)[0]
        if token.kind == "|":
            inner = self.sum()
            self.take("|")
            return _Call(_ABSOLUTE, (inner,))
        if token.kind != "name":
            raise _Unreadable(f"unexpected {token.text!r}")
        function = _CALL_ALIASES.get(token.text, token.text)
        following = self.peek()
        called = following is not None and following.kind in _OPENING and not following.spaced
        if function in _MATH_CALLS:
            if not called or following.kind != "(":
                raise _Unreadable(f"{token.text} without its argument")
            arguments = self.group(self.take(), variadic=function in _OVER_LIKE_ARGUMENTS)
            return _Call(function, tuple(arguments))
        if called:
            self.point(self.take())
        elif "," in token.text and self.groups and self.groups[-1]:
            # `min(V_app,b_ref)`: one name with a qualifier, or two arguments?
            raise _Unreadable(f"{token.text!r} in an argument list: a name or two arguments?")
        return _Name(token.text)

    def group(self, opening: _Token, variadic: bool) -> list:
        """The expressions between `opening` and its closing bracket, separated by commas when
        `variadic`."""
        self.groups.append(variadic)
        items = [self.sum()]
        while variadic and self.peek() is not None and self.peek().kind == ",":
            self.take()
            items.append(self.sum())
        self.take(_OPENING[opening.kind])
        self.groups.pop()
        return items

    def point(self, opening: _Token) -> None:
        """Skip the `(V, alpha)` of a quantity taken at a point."""
        if opening.kind != "(":
            raise _Unreadable("an index in brackets")
        while (token := self.take()).kind != ")":
            if token.kind not in ("name", "number", ","):
                raise _Unreadable("a name before a parenthesis that holds no plain list of names")


def _names(tree) -> set[str]:
    if isinstance(tree, _Name):
        return set() if tree.name in _NAMED_NUMBERS else {tree.name}
    if isinstance(tree, _Negation):
        return _names(tree.operand)
    if isinstance(tree, _Operation):
        return _names(tree.left) | _names(tree.right)
    if isinstance(tree, _Call):
        return set().union(*map(_names, tree.arguments))
    return set()


# -- the symbols of one formula --


def _folded(table: dict[str, tuple[Dim, str]]) -> dict[str, tuple[Dim, str] | None]:
    """A table for the match without regard to case: names of more than one letter, in lower
    case; `None` where two names that differ only in case stand for different units."""
    out: dict[str, tuple[Dim, str] | None] = {}
    for key, value in table.items():
        if len(key) < _SHORTEST_FOLDED_NAME:
            continue
        low = key.lower()
        out[low] = value if out.get(low, value) == value else None
    return out


@dataclasses.dataclass
class _Symbols:
    """The symbols one formula may use, and the declared unit behind each.

    A name is looked up as it stands in the formula's own bindings (parameter name, or the symbol
    of a bound quantity), then there without regard to case, then in the register in the same
    two ways. A name the four do not know is tried again without its last qualifier (`_max`,
    `,clean`), as long as a separator stands before the qualifier: `psi` is never `P_s`. A single
    letter matches only as it stands: `Q` is not `q`. A name with a letter outside ASCII is never
    known: the tables hold ASCII names only.
    """

    local: dict[str, tuple[Dim, str]]
    register: dict[str, tuple[Dim, str]]
    register_folded: dict[str, tuple[Dim, str] | None]

    def resolve(self, name: str) -> tuple[Dim, str] | None:
        segments = [s for s in re.split(r"[_,]", name.replace("'", "prime")) if s]
        local_folded = _folded(self.local)
        for dropped in range(_QUALIFIER_DEPTH + 1):
            kept = segments[: len(segments) - dropped]
            key = "".join(kept)
            if dropped and (
                len(key) < _SHORTEST_FOLDED_NAME or segments[-dropped].lower() not in QUALIFIERS
            ):
                break
            if not key:
                break
            for exact, folded in (
                (self.local, local_folded),
                (self.register, self.register_folded),
            ):
                if key in exact:
                    return exact[key]
                if folded.get(key.lower()) is not None:
                    return folded[key.lower()]
        return None


def _symbol_keys(*names) -> list[str]:
    """The keys under which a quantity is stored; a name with a letter outside ASCII, an empty
    key and a named number give none."""
    keys = []
    for name in names:
        key = _key(str(name)) if name and str(name).isascii() else ""
        if key and key not in _NAMED_NUMBERS:
            keys.append(key)
    return keys


def _declared(canon: Canon, slug) -> tuple[Dim, str, object] | None:
    """Dimension, unit and symbol of a quantity, or None when it has no readable unit."""
    q = canon.quantities.get(slug) if isinstance(slug, str) else None
    unit = q.front.get("unit") if q is not None else None
    d = parse_unit(str(unit)) if unit is not None else None
    return None if d is None else (d, str(unit), q.front.get("symbol"))


def _register_symbols(canon: Canon) -> dict[str, tuple[Dim, str]]:
    table: dict[str, tuple[Dim, str]] = {}
    for slug in canon.quantities:
        declared = _declared(canon, slug)
        if declared is None:
            continue
        d, unit, symbol = declared
        for key in _symbol_keys(symbol, slug):
            table.setdefault(key, (d, unit))
    return table


def _formula_symbols(e: Entry, canon: Canon) -> dict[str, tuple[Dim, str]]:
    """Parameter names and bound symbols of one formula, over all its applications.

    Parameter names are written in lower case. A one-letter parameter therefore also stands for
    the capital the symbol of its quantity begins with: `p` bound to `P_shaft` is the `P` of the
    form.
    """
    mappings = [e.front.get("inputs"), e.front.get("outputs")]
    applications = e.front.get("applications")
    for app in applications if isinstance(applications, list) else []:
        if isinstance(app, dict):
            mappings += [app.get("bind"), app.get("produce")]
    table: dict[str, tuple[Dim, str]] = {}
    for mapping in mappings:
        for param, slug in (mapping or {}).items() if isinstance(mapping, dict) else ():
            declared = _declared(canon, slug)
            if declared is None:
                continue
            d, unit, symbol = declared
            keys = _symbol_keys(param, symbol)
            initial = str(symbol or "")[:1]
            if (
                len(str(param)) < _SHORTEST_FOLDED_NAME
                and initial.lower() == str(param).lower()
                and _symbol_keys(initial)
            ):
                keys.append(initial)
            for key in keys:
                table.setdefault(key, (d, unit))
    return table


# -- judging a statement --


def _differs(a: float, b: float = 0.0) -> bool:
    return abs(a - b) > _TOLERANCE


def _like(a: Dim, b: Dim) -> bool:
    """The same dimension, the angle left aside: radians count as dimensionless."""
    return not any(
        _differs(x, y) for i, (x, y) in enumerate(zip(a.e, b.e, strict=True)) if i != _ANGLE_SLOT
    )


def _same_scale(a: Dim, b: Dim) -> bool:
    return not _differs(a.scale / b.scale, 1.0)


@dataclasses.dataclass
class _Reading:
    """Evaluates the tree of one side: its dimension, and its value where it is a pure number."""

    resolved: dict[str, tuple[Dim, str]]
    degrees_in_function: bool = False
    scales_mixed: bool = False

    def in_degrees(self, tree) -> bool:
        return any(_IN_DEGREES.search(self.resolved[n][1]) for n in _names(tree))

    def of(self, tree) -> tuple[Dim, float | None]:
        if isinstance(tree, _Number):
            return ONE, tree.value
        if isinstance(tree, _Name):
            if tree.name in _NAMED_NUMBERS:
                return ONE, _NAMED_NUMBERS[tree.name]
            return self.resolved[tree.name][0], None
        if isinstance(tree, _Negation):
            d, value = self.of(tree.operand)
            return d, None if value is None else -value
        if isinstance(tree, _Call):
            return self.call(tree), None
        return self.operation(tree)

    def operation(self, tree: _Operation) -> tuple[Dim, float | None]:
        (left, a), (right, b) = self.of(tree.left), self.of(tree.right)
        both = a is not None and b is not None
        if tree.op == "*":
            return left * right, a * b if both else None
        if tree.op == "/":
            return left / right, a / b if both else None
        if tree.op == "^":
            if b is None:
                raise _Unreadable("an exponent that is no number")
            value = a**b if both else None
            if isinstance(value, complex):
                raise ArithmeticError("root of a negative number")
            return left**b, value
        self.alike(left, right, f"adds {left} to {right}")
        angle = (
            left if _differs(left.e[_ANGLE_SLOT]) or not _differs(right.e[_ANGLE_SLOT]) else right
        )
        return angle, (a + b if tree.op == "+" else a - b) if both else None

    def alike(self, a: Dim, b: Dim, detail: str) -> None:
        if not _like(a, b):
            raise _Finding("ADDS_UNLIKE", detail)
        if not _same_scale(a, b):
            self.scales_mixed = True

    def call(self, tree: _Call) -> Dim:
        fn = tree.function
        dims = [self.of(a)[0] for a in tree.arguments]
        if fn in _OVER_LIKE_ARGUMENTS:
            for d in dims[1:]:
                self.alike(dims[0], d, f"{fn} of {dims[0]} and {d}")
            return dims[0]
        (d,) = dims  # the parser gives every other function exactly one argument
        if fn == _ABSOLUTE:
            return d
        if fn in _ROOTS:
            return d ** _ROOTS[fn]
        if not _like(d, ONE):
            raise _Finding("MISMATCH", f"{fn} of {d}")
        if not _same_scale(d, ONE):
            self.scales_mixed = True
        if fn in _TRIGONOMETRIC and _differs(d.e[_ANGLE_SLOT]) and self.in_degrees(tree):
            self.degrees_in_function = True
        return ONE


def _is_number(tree) -> bool:
    return isinstance(tree.operand if isinstance(tree, _Negation) else tree, _Number)


def _judge(lhs: str, rhs: str, text: str, symbols: _Symbols) -> tuple[str, str]:
    try:
        return _judge_read(lhs, rhs, text, symbols)
    except _Finding as finding:
        return finding.verdict, finding.detail
    except _Unreadable as exc:
        return "UNPARSEABLE", str(exc)
    except ArithmeticError as exc:  # an exponent the arithmetic cannot carry
        return "UNPARSEABLE", f"arithmetic: {exc}"


def _judge_read(lhs: str, rhs: str, text: str, symbols: _Symbols) -> tuple[str, str]:
    left_tree, right_tree = (_Parser(side).expression_to_the_end() for side in (lhs, rhs))
    names = _names(left_tree) | _names(right_tree)
    resolved = {n: r for n in names if (r := symbols.resolve(n)) is not None}
    unknown = sorted(names - set(resolved))
    reading = _Reading(resolved)
    converts_angle = bool(_ANGLE_CONVERSION.search(text))
    angle = "a quantity in degrees meets radians and the statement converts nothing"

    numbers = [t for t in (left_tree, right_tree) if _is_number(t)]
    if numbers:
        other = right_tree if numbers[0] is left_tree else left_tree
        if isinstance(other, _Name | _Number):  # `g_0 = 9.81`
            return "CONSTANT", ""
        if unknown:
            return "UNKNOWN_SYMBOL", ", ".join(unknown)
        reading.of(other)  # nothing to balance, but the side must be sound in itself
        if reading.degrees_in_function and not converts_angle:
            return "ANGLE", angle
        return "CONSTANT", ""

    units = [unit for _, unit in resolved.values()]
    degrees = any(_IN_DEGREES.search(u) for u in units)
    radians = any(_IN_RADIANS.search(u) for u in units)
    defined = left_tree.name if isinstance(left_tree, _Name) else None
    if defined is not None and unknown == [defined] and defined.isascii() and _name_key(defined):
        right, _ = reading.of(right_tree)
        if reading.degrees_in_function and not converts_angle:
            return "ANGLE", angle
        if converts_angle:
            unit = _NO_ANGLE_UNIT  # converted, in a direction the check does not read
        else:
            unit = _DEGREES if degrees else _RADIANS if radians else _NO_ANGLE_UNIT
        symbols.local[_name_key(defined)] = (right, unit)
        return "DEFINES", ""
    if unknown:
        return "UNKNOWN_SYMBOL", ", ".join(unknown)
    (left, _), (right, _) = reading.of(left_tree), reading.of(right_tree)
    if not _like(left, right):
        return "MISMATCH", f"{left}  =  {right}"
    angle_differs = _differs(left.e[_ANGLE_SLOT], right.e[_ANGLE_SLOT])
    if not converts_angle and (
        reading.degrees_in_function or (degrees and (angle_differs or radians))
    ):
        return "ANGLE", angle
    if (reading.scales_mixed or not _same_scale(left, right)) and not _SCALE_CONVERSION.search(
        text
    ):
        return "SCALE", "two length scales (mm, m) meet and the statement converts nothing"
    return "OK", ""


def check_statements(canon: Canon) -> list[Statement]:
    """Check every `lhs = rhs` statement of every canonical form for its dimension.

    Findings: a dimension that does not balance (`MISMATCH`, also a function such as `sin` or
    `exp` of a quantity that is not dimensionless); a sum, `max` or `min` over unlike quantities
    (`ADDS_UNLIKE`); a quantity in degrees that meets radians, or stands inside `sin`, `cos`,
    `tan`, without a visible conversion (`ANGLE`); millimetres that meet metres without a visible
    power of ten (`SCALE`).

    Symbols resolve through the formula's own bindings first. A name the register does not know
    is defined by the first statement that has it alone on the left, and keeps the degrees of
    that statement's right side. What the check cannot read reliably is never judged: a statement
    that does not parse, has more than one `=`, or uses an unknown symbol is reported as such.

    Known limit: any `180/pi` or `pi/180` in the text of a statement settles `ANGLE`, whatever
    its direction and whatever it multiplies; likewise any power of ten settles `SCALE`. The
    check sees that a conversion is written, not that it is the right one.
    """
    register = _register_symbols(canon)
    register_folded = _folded(register)
    rows: list[Statement] = []
    for slug, e in canon.formulas.items():
        m = re.search(r"\*\*Canonical form\*\*\s*\n+```[a-z]*\n(.*?)\n```", e.body, re.S)
        if not m:
            continue
        symbols = _Symbols(_formula_symbols(e, canon), register, register_folded)
        for text in _statements(m.group(1)):
            try:
                lhs, rhs = _EQUALS.split(text)
            except ValueError:
                verdict, detail = "UNPARSEABLE", "more than one '=' in one statement"
            else:
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
