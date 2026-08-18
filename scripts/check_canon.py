"""Dimensional check for canonical formulas.

Parses each canonical form, substitutes the declared unit of every symbol from the
quantity register, and evaluates the dimension of the right-hand side. Reports a
formula whose result does not match its declared output quantity, or which adds two
quantities of unlike dimension.
"""
from __future__ import annotations

import ast
import json
import re
import sys

sys.path.insert(0, "scripts")
from dimensions import ONE, Dim, parse_unit  # noqa: E402

FUNCS = {"sqrt": 0.5, "cbrt": 1 / 3}

#: forms that are definitions or procedures, not algebraic laws — a dimensional
#: check does not apply to them, and failing them would be noise.
PROCEDURAL = re.compile(
    r"argmax|argmin|max over|min over|first i|interp\(|:=|\bfor V\b|\bwhere\b|"
    r"crossing|detection|_ISA\(|table|converted to|optionally|standard atmosphere",
    re.I,
)

#: dimensionless mathematical constants that may appear in a canonical form
MATH_CONSTANTS = {"pi", "tau", "euler"}

#: qualifiers a canonical form may append to a registered symbol
QUALIFIERS = (
    "clean", "cfg", "config", "target", "ref", "max", "min", "total", "req",
    "static", "mean", "eff", "i", "j", "0", "1", "s0", "s1", "op", "turn",
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
    # single-letter conventions the canonical forms use for registered quantities
    for alias, target in (("s", "sref"), ("b", "bref"), ("v", "flightspeed"),
                          ("w", "weight"), ("m", "aircraftmass"), ("h", "altitude")):
        if target in table:
            table.setdefault(alias, table[target])
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
    e = re.sub(r"(\d)\s*\(", r"\1*(", e)          # 2(x) -> 2*(x)
    e = re.sub(r"(\d)\s*([A-Za-z_])", r"\1*\2", e)  # 2W -> 2*W
    e = re.sub(r"\)\s*([A-Za-z_(])", r")*\1", e)   # )( -> )*(
    e = re.sub(r"[,_{}]", "", e)                   # C_L,max -> CLmax
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
    rhs = re.sub(r"\s*\[.*?\]\s*", " ", rhs)      # drop [citation] tails
    rhs = re.sub(r"\s*\((?:small|large|with|where|assuming|per|note|i\.e\.)[^)]*\)", " ", rhs, flags=re.I)
    rhs = re.sub(r"\|([^|]+)\|", r"abs(\1)", rhs)   # |x| -> abs(x)
    rhs = re.sub(r"\b(\d+(?:\.\d+)?)\s*(m/s|m|s|kg|N|Pa|W)\b", r"\1", rhs)  # "1 m/s" literal
    rhs = rhs.split(",  ")[0]                       # drop a trailing second statement
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


def main(path):
    data = json.load(open(path))
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


if __name__ == "__main__":
    rows = main(sys.argv[1])
    tally: dict[str, int] = {}
    for v, *_ in rows:
        tally[v] = tally.get(v, 0) + 1
    print("dimensional check over", len(rows), "canonical formulas:", tally, "\n")
    for v, f, d, want, unknown, msg in rows:
        if v == "BALANCES":
            continue
        print(f"  {v:15s} {f['slug'][:44]:46s} {f.get('canonical_form','')[:70]}")
        if v == "MISMATCH":
            print(f"       rhs -> {d}   declared {want}  ({f.get('output_quantity')})")
        if msg:
            print(f"       {msg}")
        if unknown and v in ("UNKNOWN_SYMBOL",):
            print(f"       unknown symbols: {sorted(unknown)[:8]}")
