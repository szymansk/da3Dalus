"""Build the walkable calculation graph from the Markdown canon.

The navigator is **derived, never maintained**: it is regenerated from
`canon/quantities/` and `canon/formulas/` whenever the catalogue changes. Editing the
generated HTML instead would recreate exactly the duplicate problem requirement A1 warns
about.

Run:  poetry run python scripts/build_canon_navigator.py \
          _reversa_sdd/calculations/canon _reversa_sdd/calculations/canon/navigator.html
"""

from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

#: Edges the layering breaks, with the reason. A naming collapse, not a fixed point: one
#: name covering a swept measurement and a modelled value. (The second one, a generic
#: speed bucket, was resolved in the canon on 2026-10-01 by making V a pure input.)
# Edges cut by hand. Empty since 2026-10-02: the last false cycle (C_D -> C_D0 -> C_D) was a
# naming collision, removed in the canon itself. Keep it empty; fix cycles in the canon.
BROKEN_EDGES: set = set()

GREEK = {
    "rho": r"\rho",
    "alpha": r"\alpha",
    "gamma": r"\gamma",
    "eta": r"\eta",
    "mu": r"\mu",
    "pi": r"\pi",
    "sigma": r"\sigma",
    "lambda": r"\lambda",
    "phi": r"\phi",
}

#: A canonical form containing any of these is a procedure, not an expression, and is
#: shown verbatim rather than typeset.
NOT_TYPESETTABLE = (
    "argmax",
    "argmin",
    "interp",
    "first i",
    "max over",
    "min over",
    "sum_i",
    "crossing",
    ":=",
    "optionally",
    "[",
)


def _front(text: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.+)$", text.split("---", 2)[1], re.M)
    return m.group(1).strip() if m else ""


def to_tex(form: str) -> str | None:
    """Best-effort TeX for a canonical form; None when it is a procedure."""
    if not form or any(w in form for w in NOT_TYPESETTABLE):
        return None
    s = re.split(r"\s{2,}", form.strip())[0].rstrip(",").replace("sqrt(", r"\sqrt(")
    for word, cmd in GREEK.items():
        s = re.sub(rf"(?<![A-Za-z\\]){word}(?![A-Za-z])", (lambda m, c=cmd: c), s)
    s = re.sub(r"([A-Za-z])_([A-Za-z0-9,]+)", lambda m: "%s_{%s}" % m.groups(), s)
    s = re.sub(r"\^([0-9.]+)", lambda m: "^{%s}" % m.group(1), s)
    s = s.replace("*", r"\,")
    s = re.sub(r"\bmax\b", r"\\max ", s)
    while r"\sqrt(" in s:  # also nested
        i = s.index(r"\sqrt(")
        j = i + 6
        depth = 1
        while j < len(s) and depth:
            depth += (s[j] == "(") - (s[j] == ")")
            j += 1
        s = s[:i] + r"\sqrt{" + s[i + 6 : j - 1] + "}" + s[j:]
    return re.sub(r"\s+", " ", s).strip()


def read_canon(root: pathlib.Path) -> tuple[dict, dict]:
    quantities = {}
    for f in sorted((root / "quantities").glob("*.md")):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"^# .+?\n+(.+?)(?:\n\n|\Z)", t.split("---", 2)[2], re.S | re.M)
        quantities[f.stem] = {
            "symbol": _front(t, "symbol"),
            "unit": _front(t, "unit"),
            "role": _front(t, "role"),
            "unc": _front(t, "uncertainty"),
            "desc": " ".join(m.group(1).split()) if m else "",
        }
    formulas = {}
    for f in sorted((root / "formulas").glob("*.md")):
        t = f.read_text(encoding="utf-8")
        cf = re.search(r"\*\*Canonical form\*\*\s*\n+```[a-z]*\n(.*?)\n```", t, re.S)
        form = cf.group(1).strip() if cf else ""
        produces = re.search(r"\*\*Produces\*\*.*?\*\*from\*\*(.*)", t)
        source = re.search(r"\*\*Source\.\*\*.*?\n\n> (.+?)(?:\n\n|\Z)", t, re.S)
        ins = re.findall(r"\[\[([a-z0-9-]+)\]\]", produces.group(1)) if produces else []
        formulas[f.stem] = {
            "out": [o.strip() for o in _front(t, "output").split(",") if o.strip()],
            "ins": [i for i in ins if i in quantities],
            "form": form,
            "tex": _front(t, "tex") or to_tex(form),
            "kind": _front(t, "kind"),
            "tool": _front(t, "tool") or "APP",
            "status": _front(t, "status"),
            "src": " ".join(source.group(1).split())[:420] if source else "",
        }
    return quantities, formulas


def layout(quantities: dict, formulas: dict) -> dict:
    edges = []
    for slug, f in formulas.items():
        for out in f["out"]:
            for i in dict.fromkeys(f["ins"]):
                if i == out:
                    raise SystemExit(f"self-edge: {slug} lists its own output {out!r} as an input")
                if (i, out) not in BROKEN_EDGES:
                    edges.append((i, out, slug))

    produced = {o for f in formulas.values() for o in f["out"]}
    consumed = {a for a, _, _ in edges}
    layer = {q: 0 for q in quantities if q not in produced}
    for _ in range(80):  # longest chain is ~12
        changed = False
        for f in formulas.values():
            for out in f["out"]:
                ins = [i for i in f["ins"] if i != out and (i, out) not in BROKEN_EDGES]
                if all(i in layer for i in ins):
                    lvl = 1 + max([layer[i] for i in ins], default=0)
                    if layer.get(out, -1) < lvl:
                        layer[out] = lvl
                        changed = True
        if not changed:
            break
    for q in quantities:
        layer.setdefault(q, 0)

    rows = collections.defaultdict(list)
    for q, lay in layer.items():
        rows[lay].append(q)
    for lay in rows:
        rows[lay].sort()
    pos = {q: i for lay in rows for i, q in enumerate(rows[lay])}
    pred, succ = collections.defaultdict(list), collections.defaultdict(list)
    for a, b, _ in edges:
        pred[b].append(a)
        succ[a].append(b)
    for sweep in range(14):  # barycentre, both ways
        ref = pred if sweep % 2 == 0 else succ
        for lay in sorted(rows, reverse=sweep % 2):
            rows[lay].sort(
                key=lambda q: (sum(pos[x] for x in ref[q]) / len(ref[q])) if ref[q] else pos[q]
            )
            for i, q in enumerate(rows[lay]):
                pos[q] = i

    return {
        "Q": quantities,
        "F": formulas,
        "edges": edges,
        "layer": layer,
        "order": {str(lay): rows[lay] for lay in sorted(rows)},
        "inputs": sorted(q for q in quantities if q not in produced),
        "outputs": sorted(q for q in produced if q not in consumed),
    }


def to_ascii(html: str) -> str:
    """Escape per region: \\uXXXX in script, CSS escapes in style, refs elsewhere.

    The page is served under whatever charset the host decides, so anything non-ASCII
    in the source is a gamble on that decision. Escaping removes the gamble.
    """

    def convert(chunk: str, kind: str) -> str:
        if kind == "script":
            return "".join(c if ord(c) < 128 else "\\u%04x" % ord(c) for c in chunk)
        if kind == "style":
            return "".join(c if ord(c) < 128 else "\\%04x " % ord(c) for c in chunk)
        return "".join(c if ord(c) < 128 else "&#%d;" % ord(c) for c in chunk)

    out, i = [], 0
    for m in re.finditer(r"<(script|style)\b[^>]*>(.*?)</\1>", html, re.S | re.I):
        if m.start() > i:
            out.append(convert(html[i : m.start()], "html"))
        gt = html.index(">", m.start())
        out.append(html[m.start() : gt + 1])
        out.append(convert(m.group(2), m.group(1).lower()))
        out.append(html[m.end(2) : m.end()])
        i = m.end()
    out.append(convert(html[i:], "html"))
    return "".join(out)


def main(canon_dir: str, out_path: str) -> None:
    root = pathlib.Path(canon_dir)
    quantities, formulas = read_canon(root)
    data = layout(quantities, formulas)
    template = pathlib.Path(__file__).with_name("canon_navigator_template.html")
    payload = json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    html = to_ascii(template.read_text(encoding="utf-8").replace("__CANON_DATA__", payload))
    assert all(ord(c) < 128 for c in html), "page is not pure ASCII"
    pathlib.Path(out_path).write_text(html, encoding="ascii")

    layers = len(data["order"])
    print(
        f"{len(quantities)} quantities, {len(formulas)} formulas, "
        f"{len(data['edges'])} edges, {layers} layers"
    )
    print(f"{len(data['inputs'])} inputs, {len(data['outputs'])} final results")
    print(f"-> {out_path}  ({len(html) / 1024:.0f} KB)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
