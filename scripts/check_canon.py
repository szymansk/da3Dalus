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
every parameter bound in every application. A structural error fails the run. A gap on a
parameter that an `# ESCALATED: <reason>` comment names in its reason is reported as *open*
instead: the question is with the maintainer, the gap is known. Every other gap of the same
entry stays an error.

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
#: optional on a precondition: the application ids it applies to (absent: all of them)
PRECONDITION_OPTIONAL = {"applications"}
#: an escalation states its reason: '# ESCALATED: <reason>'
ESCALATED_REASON = re.compile(r"^\s*#\s*ESCALATED\b:?(.*)$", re.M)
UNCERTAINTY = {"interval"}
ROLES = {"input", "derived", "output", "target"}
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
#: the fields of a defaults.yaml entry (#1174)
DEFAULT_KEYS = ("value", "unit", "source", "regime")


@dataclasses.dataclass(frozen=True)
class Entry:
    slug: str
    front: dict
    raw_front: str
    body: str
    #: the file it was read from, relative to the canon directory
    file: str = ""

    def escalates(self, name: str) -> bool:
        """Whether an '# ESCALATED: <reason>' comment names this parameter or field."""
        return any(
            re.search(rf"(?<![A-Za-z0-9_-]){re.escape(name)}(?![A-Za-z0-9_-])", m.group(1))
            for m in ESCALATED_REASON.finditer(self.raw_front)
        )


@dataclasses.dataclass(frozen=True)
class Canon:
    formulas: dict[str, Entry]
    quantities: dict[str, Entry]
    vocabulary: set[str]
    types: set[str]
    #: README "One example per kind": (slug, parsed example) pairs
    examples: list = dataclasses.field(default_factory=list)
    #: (file, message) problems found while reading the entries: duplicate or misnamed slugs
    load_errors: list = dataclasses.field(default_factory=list)
    #: defaults.yaml: slug -> {value, unit, source, regime}
    defaults: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class Finding:
    entry: str
    field: str
    message: str
    #: True for a gap an '# ESCALATED:' comment names, or an open warning: known, not an error
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
    file = f"{path.parent.name}/{path.name}"
    slug = front.get("canon")  # no fallback to the file name (ADR 0020): checked in load_canon
    return Entry(slug=slug or "", front=front, raw_front=raw, body=body, file=file)


def _table_terms(readme: str, heading: str) -> set[str]:
    """The backticked first-column terms of the table under a README heading."""
    m = re.search(rf"^#+ [^\n]*{re.escape(heading)}[^\n]*$(.*?)(?=^#+ |\Z)", readme, re.M | re.S)
    if not m:
        return set()
    return set(re.findall(r"^\|\s*`([a-z_]+)`\s*\|", m.group(1), re.M))


def load_canon(canon_dir: pathlib.Path) -> Canon:
    root = pathlib.Path(canon_dir)
    readme = (root / "README.md").read_text(encoding="utf-8")
    load_errors: list = []

    def read_all(sub: str) -> dict[str, Entry]:
        entries: dict[str, Entry] = {}
        for f in sorted((root / sub).glob("*.md")):
            e = _read_entry(f)
            if not e.slug:
                load_errors.append((e.file, "missing canon slug: the entry needs a 'canon:' field"))
                continue
            if e.slug != f.stem:
                load_errors.append(
                    (e.file, f"canon slug {e.slug!r} differs from the file name {f.stem!r}")
                )
            if e.slug in entries:
                load_errors.append(
                    (e.file, f"duplicate canon slug {e.slug!r}, also in {entries[e.slug].file}")
                )
                continue
            entries[e.slug] = e
        return entries

    formulas = read_all("formulas")
    quantities = read_all("quantities")
    defaults: dict = {}
    if (root / "defaults.yaml").exists():
        text = (root / "defaults.yaml").read_text(encoding="utf-8")
        node = yaml.compose(text)
        seen = [k.value for k, _ in node.value] if isinstance(node, yaml.MappingNode) else []
        for slug in sorted({s for s in seen if seen.count(s) > 1}):
            load_errors.append(("defaults.yaml", f"duplicate slug {slug!r}"))
        defaults = yaml.safe_load(text) or {}
    return Canon(
        formulas=formulas,
        quantities=quantities,
        vocabulary=_table_terms(readme, "Vocabulary of `when`"),
        types=_table_terms(readme, "Quantity types"),
        examples=_readme_examples(readme),
        load_errors=load_errors,
        defaults=defaults,
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


def _check_formula(e: Entry, canon: Canon, add, gap) -> tuple[set[str], set[str], dict]:
    """Check one formula entry; return the quantity slugs it reads and writes, overall and per
    application id ('default' for an entry without applications)."""
    q = canon.quantities
    inputs = _check_parameters(e, "inputs", add)
    outputs = _check_parameters(e, "outputs", add)
    reads: set[str] = set()
    writes: set[str] = set()
    per_app: dict[str, tuple[set[str], set[str]]] = {}

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
        if when is not None and not isinstance(when, str):
            add(e.slug, "applications", f"{where}: when must be one vocabulary term: {when!r}")
        elif when is not None and when not in canon.vocabulary:
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
            if slug in canon.defaults:
                add(e.slug, "applications", f"{where}: given {slug!r} has a default")
            if slug not in bound:
                add(e.slug, "applications", f"{where}: given {slug!r} is not bound by it")
        # what this application actually reads and writes (a default overridden by every
        # application is never read and does not belong on the from line)
        app_reads = {v for v in _effective(inputs, bind).values() if isinstance(v, str) and v in q}
        app_writes = {
            v for v in _effective(outputs, produce).values() if isinstance(v, str) and v in q
        }
        reads |= app_reads
        writes |= app_writes
        per_app[str(aid)] = (app_reads, app_writes)
        for name, value in _effective(inputs, bind).items():
            if value is None:
                gap(e, "applications", f"{where}: input parameter {name!r} is not bound", name)
        # An output may be produced explicitly as null: the implementation returns it, the
        # application does not expose it. Only an output absent from the merged produce is a gap.
        explicit_null = (
            {n for n, v in produce.items() if v is None} if isinstance(produce, dict) else set()
        )
        for name, value in _effective(outputs, produce).items():
            if value is None and name not in explicit_null:
                gap(e, "applications", f"{where}: output parameter {name!r} is not produced", name)

    # preconditions run before the call and check inputs; postconditions run after it and check
    # outputs (also those an application writes as null)
    # only a per_control_surface quantity may be produced by several applications (README):
    # counted on each application's effective outputs, explicit produce and inherited defaults
    if apps is not None:
        producers: dict[str, list[str]] = {}
        for aid, (_, app_writes) in per_app.items():
            for w in app_writes:
                producers.setdefault(w, []).append(aid)
        for w, aids in sorted(producers.items()):
            if len(aids) > 1 and q[w].front.get("type") != "per_control_surface":
                add(e.slug, "applications", f"{w!r} is produced by applications {sorted(aids)}")

    for field, params, kind in (
        ("preconditions", inputs, "input"),
        ("postconditions", outputs, "output"),
    ):
        for pre in e.front.get(field) or []:
            if not isinstance(pre, dict) or not (
                PRECONDITION_KEYS <= set(pre) <= PRECONDITION_KEYS | PRECONDITION_OPTIONAL
            ):
                add(
                    e.slug,
                    field,
                    f"needs {sorted(PRECONDITION_KEYS)}, optionally {sorted(PRECONDITION_OPTIONAL)}: "
                    f"{pre!r}",
                )
                continue
            scope = pre.get("applications")
            if scope is not None:
                if not isinstance(scope, list) or not scope:
                    add(e.slug, field, f"{pre['id']}: applications must be a non-empty list")
                else:
                    for aid in scope:
                        if aid not in ids:
                            add(e.slug, field, f"{pre['id']}: unknown application {aid!r}")
            if not SNAKE.match(str(pre["id"])):
                add(e.slug, field, f"id {pre['id']!r} is not snake_case")
            if pre["parameter"] not in params:
                add(e.slug, field, f"{pre['id']}: {pre['parameter']!r} is not an {kind} parameter")
            if pre["on_violation"] not in ON_VIOLATION:
                add(e.slug, field, f"{pre['id']}: on_violation {pre['on_violation']!r}")

    unc = e.front.get("uncertainty")
    if unc is not None and unc not in UNCERTAINTY:
        add(e.slug, "uncertainty", f"{unc!r} is not one of {sorted(UNCERTAINTY)}")
    interval = unc == "interval"
    worlds = e.front.get("worlds")
    if interval and not (isinstance(worlds, list) and worlds):
        add(e.slug, "worlds", "uncertainty: interval needs a non-empty list of worlds")
    if worlds is not None and not interval:
        add(e.slug, "worlds", "worlds without uncertainty: interval")
    for w in worlds or []:
        if not isinstance(w, str) or not SNAKE.match(w):
            add(e.slug, "worlds", f"world {w!r} is not snake_case")

    embeds = e.front.get("embeds") or []
    if not isinstance(embeds, list):
        add(e.slug, "embeds", f"not a list: {embeds!r}")
        embeds = []
    for item in embeds:
        slug, _, app = str(item).partition(".")
        target_f = canon.formulas.get(slug)
        if slug == e.slug:
            add(e.slug, "embeds", "a formula cannot embed itself")
        elif target_f is None:
            add(e.slug, "embeds", f"unknown formula {item!r}")
        else:
            app_ids = [
                a.get("id") for a in target_f.front.get("applications") or [] if isinstance(a, dict)
            ]
            if app and app not in app_ids:
                add(e.slug, "embeds", f"{item!r}: {slug} has no application {app!r}")
            elif not app and len(app_ids) > 1:
                add(
                    e.slug,
                    "embeds",
                    f"{slug!r} has several applications: name one as {slug}.<application>",
                )
    if "variables" in e.front and not embeds:
        add(e.slug, "variables", "variables without embeds: only an embedder declares variables")
    if embeds and not isinstance(e.front.get("variables"), list):
        add(
            e.slug,
            "variables",
            "embeds needs variables: the quantities the formula solves for or sweeps itself",
        )
    for v in e.front.get("variables") or []:
        if v not in q:
            add(e.slug, "variables", f"unknown quantity {v!r}")

    optional = e.front.get("optional") or []
    if not isinstance(optional, list):
        add(e.slug, "optional", f"not a list: {optional!r}")
        optional = []
    for name in optional:
        if name not in inputs:
            add(e.slug, "optional", f"{name!r} is not an input parameter")

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
    return reads, writes, per_app


def _diff(name: str, prose: set[str], front: set[str]) -> str:
    parts = []
    if prose - front:
        parts.append(f"only in the {name}: {sorted(prose - front)}")
    if front - prose:
        parts.append(f"only in the front matter: {sorted(front - prose)}")
    return "; ".join(parts)


def _direct_embeds(e: Entry) -> list[str]:
    """Embedded formula slugs, for the cycle check. An item 'slug.application' embeds that
    application as written — its bindings and its checks (see _embedded_items)."""
    embeds = e.front.get("embeds") or []
    if not isinstance(embeds, list):
        return []
    return list(dict.fromkeys(s.partition(".")[0] for s in embeds if isinstance(s, str)))


def _embedded_items(e: Entry, canon: Canon) -> list[tuple[str, str | None]]:
    """(formula, application) pairs of an entry's embeds; None selects the single application."""
    embeds = e.front.get("embeds") or []
    if not isinstance(embeds, list):
        return []
    out = []
    for item in embeds:
        if isinstance(item, str):
            slug, _, app = item.partition(".")
            if slug in canon.formulas:
                out.append((slug, app or None))
    return out


def _check_embeds(
    canon: Canon, reads_of: dict, writes_of: dict, per_app_of: dict, add, warn
) -> None:
    """The embeds closure: acyclic, no worlds inside, every embedded input accounted for.

    An item embeds that application as written — its bindings and its checks — so the input
    rule applies to what the listed applications bind (after defaults), not to the union of all.
    """
    graph = {
        s: [x for x in _direct_embeds(e) if x in canon.formulas] for s, e in canon.formulas.items()
    }

    state: dict[str, int] = {}  # 1 = on the DFS stack, 2 = done
    reported: set[frozenset] = set()

    def visit(node: str, path: list[str]) -> None:
        state[node] = 1
        for nxt in graph[node]:
            if state.get(nxt) == 1:
                cycle = path[path.index(nxt) :] + [nxt]
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    add(nxt, "embeds", "cycle: " + " -> ".join(cycle))
            elif state.get(nxt) is None:
                visit(nxt, [*path, nxt])
        state[node] = 2

    for slug in graph:
        if slug not in state:
            visit(slug, [slug])
    if reported:
        return  # a closure over a cycle is not defined

    def rw(slug: str, app: str | None) -> tuple[set[str], set[str]]:
        apps = per_app_of[slug]
        if app is None and len(apps) == 1:
            return next(iter(apps.values()))
        if app in apps:
            return apps[app]
        return reads_of[slug], writes_of[slug]  # malformed item, reported elsewhere

    def closure(slug: str) -> list[tuple[str, str | None]]:
        seen: list[tuple[str, str | None]] = []
        stack = _embedded_items(canon.formulas[slug], canon)
        while stack:
            nxt = stack.pop(0)
            if nxt not in seen:
                seen.append(nxt)
                stack.extend(_embedded_items(canon.formulas[nxt[0]], canon))
        return seen

    for slug in canon.formulas:
        inner = closure(slug)
        if not inner:
            continue
        produced = set().union(*(rw(*x)[1] for x in inner))
        variables = set(canon.formulas[slug].front.get("variables") or [])
        supplied = reads_of[slug] | produced | variables
        read_inside = set().union(*(rw(*x)[0] for x in inner))
        for v in sorted(variables - read_inside):
            add(slug, "variables", f"{v!r} is read by no formula in the embeds closure")
        # a swept or solved quantity that only arrives through an embedder input looks like an
        # undeclared variable: report it (open), never fail on it
        embedder = canon.formulas[slug].front
        params: dict[str, str] = {}
        for name, value in (embedder.get("inputs") or {}).items():
            if isinstance(value, str):
                params.setdefault(value, name)
        for app in embedder.get("applications") or []:
            for name, value in ((app or {}).get("bind") or {}).items():
                if isinstance(value, str):
                    params.setdefault(value, name)
        # a straight pass-through — the embedder hands its input on under the same parameter name
        # the embedded application binds it to — is not a hidden variable
        inner_names: dict[str, set[str]] = {}
        for x, app in inner:
            fx = canon.formulas[x].front
            binds = next(
                (a.get("bind") or {} for a in fx.get("applications") or [] if a.get("id") == app),
                {},
            )
            for name, value in _effective(fx.get("inputs") or {}, binds).items():
                if isinstance(value, str):
                    inner_names.setdefault(value, set()).add(name)
        for qslug in sorted((read_inside & reads_of[slug]) - variables - produced):
            qf = canon.quantities[qslug].front
            if params.get(qslug) in inner_names.get(qslug, set()):
                continue
            if (
                qf.get("type") == "scalar"
                and qf.get("role") in ("input", "target")
                and qslug not in canon.defaults
            ):
                warn(
                    slug,
                    "variables",
                    f"closure binds {qslug} via embedder input {params.get(qslug, '?')}; if the "
                    "form sweeps or solves it, list it in `variables`",
                )
        for x, app in inner:
            if canon.formulas[x].front.get("uncertainty") == "interval":
                add(slug, "embeds", f"{x} has uncertainty: interval and may not be embedded")
            for q in sorted(rw(x, app)[0] - supplied):
                add(
                    slug,
                    "embeds",
                    f"input {q!r} of embedded {x} is neither a variable of {slug}, an input of "
                    f"{slug}, nor produced inside the closure",
                )


def check_structure(canon: Canon) -> list[Finding]:
    findings: list[Finding] = []

    def add(entry: str, field: str, message: str) -> None:
        findings.append(Finding(entry, field, message))

    def gap(e: Entry, field: str, message: str, name: str) -> None:
        # open only when an escalation comment names this parameter
        findings.append(Finding(e.slug, field, message, open=e.escalates(name)))

    used_by: dict[str, set[str]] = {s: set() for s in canon.quantities}
    produced_by: dict[str, set[str]] = {s: set() for s in canon.quantities}
    reads_of: dict[str, set[str]] = {}
    per_app_of: dict[str, dict] = {}
    writes_of: dict[str, set[str]] = {}
    for slug, e in canon.formulas.items():
        reads, writes, per_app = _check_formula(e, canon, add, gap)
        reads_of[slug], writes_of[slug] = reads, writes
        per_app_of[slug] = per_app
        for r in reads:
            used_by[r].add(slug)
        for w in writes:
            produced_by[w].add(slug)

    def warn(entry: str, field: str, message: str) -> None:
        findings.append(Finding(entry, field, message, open=True))

    _check_embeds(canon, reads_of, writes_of, per_app_of, add, warn)

    for e in [*canon.formulas.values(), *canon.quantities.values()]:
        booleans = yaml11_booleans(e.raw_front)
        if booleans:
            add(e.slug, "yaml", f"YAML 1.1 booleans as plain keys or values: {booleans}")
        for m in ESCALATED_REASON.finditer(e.raw_front):
            if not m.group(1).strip():
                add(
                    e.slug,
                    "ESCALATED",
                    "an escalation comment needs a reason: '# ESCALATED: <reason>'",
                )

    for slug, example in canon.examples:
        entry = canon.formulas.get(slug) or canon.quantities.get(slug)
        if entry is None:
            add("README", "examples", f"example names no entry: {slug!r}")
            continue
        keys = EXAMPLE_KEYS_FORMULA if slug in canon.formulas else EXAMPLE_KEYS_QUANTITY
        for key in dict.fromkeys([*example, *keys]):
            if entry.front.get(key) != example.get(key):
                add("README", "examples", f"{slug}: {key} differs from the entry's front matter")

    for file, message in canon.load_errors:
        add(file, "default" if file == "defaults.yaml" else "canon", message)
    for slug, d in canon.defaults.items():
        qe = canon.quantities.get(slug)
        if qe is None:
            add("defaults.yaml", "default", f"unknown quantity {slug!r}")
            continue
        if qe.front.get("role") not in ("input", "target"):
            add(slug, "default", "only a quantity with role input or target has a default")
        d = d if isinstance(d, dict) else {}
        for key in DEFAULT_KEYS:
            if d.get(key) is None or str(d[key]).strip() == "":
                add(slug, "default", f"{key!r} is missing or empty")
        if d.get("unit") is not None and str(d["unit"]) != str(qe.front.get("unit")):
            add(
                slug,
                "default",
                f"unit {d['unit']!r} is not the quantity's unit {str(qe.front.get('unit'))!r}",
            )

    for slug, e in canon.quantities.items():
        if e.front.get("role") not in ROLES:
            add(slug, "role", f"{e.front.get('role')!r} is not one of {sorted(ROLES)}")
        if "positive" in e.front:
            pos = e.front["positive"]
            if pos is not True:
                add(slug, "positive", f"must be true (omit the field otherwise): {pos!r}")
            elif e.front.get("role") not in ("input", "target"):
                add(slug, "positive", "allowed only on a quantity with role input or target")
            elif e.front.get("type") != "scalar":
                add(
                    slug,
                    "positive",
                    "allowed only on type scalar: positivity is a property of a number",
                )
            else:
                d = canon.defaults.get(slug)
                value = d.get("value") if isinstance(d, dict) else None
                is_number = isinstance(value, int | float) and not isinstance(value, bool)
                if d is not None and not is_number:
                    add(
                        slug, "default", f"a positive quantity needs a number as default: {value!r}"
                    )
                elif is_number and value <= 0:
                    add(
                        slug, "default", f"a positive quantity needs a default value > 0: {value!r}"
                    )
        unc = e.front.get("uncertainty")
        if unc is not None and unc not in UNCERTAINTY:
            add(slug, "uncertainty", f"{unc!r} is not one of {sorted(UNCERTAINTY)}")
        t = e.front.get("type")
        if t is None:
            add(slug, "type", "missing")
        elif t not in canon.types:
            add(slug, "type", f"{t!r} is not in the type set of the README")
        if "default" in e.front:
            add(slug, "default", "belongs in defaults.yaml, not in the front matter (#1174)")
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
        f"{len(canon.quantities)} quantities: {len(errors)} errors, {len(opened)} open (escalated or warning)"
    )
    for title, group in (("errors", errors), ("open (escalated or warning)", opened)):
        if group:
            print(f"\n  {title}:")
        for f in group:
            print(f"    {f.entry} [{f.field}] {f.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
