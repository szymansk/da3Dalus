"""Build the walkable calculation graph from the Markdown canon.

The navigator is **derived, never maintained**: it is regenerated from
`canon/quantities/` and `canon/formulas/` whenever the catalogue changes. Editing the
generated HTML instead would recreate exactly the duplicate problem requirement A1 warns
about.

Edges are exact per application: they come from the bindings of the imported canon model
(`aero_kernel/canon/canon_model.json`), so a formula with several applications links each
output only to the inputs of its own application. The page also marks the implementation
status in `aero_kernel` (an `@formula("<slug>")` in `aero_kernel/formulas/`) and the MVP
(the upstream closure of `MVP_RESULTS`).

Run:   poetry run python scripts/build_canon_navigator.py
Check: poetry run python scripts/build_canon_navigator.py --check   (CI: fails if stale)
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
    return m.group(1).strip().strip('"') if m else ""


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


#: The MVP results (maintainer 2026-10-22): BRYAN and JAGUAR through the kernel to the stall
#: speed, neutral point and static margin, and the roll rate. The MVP is their upstream closure.
MVP_RESULTS = (
    "stall-speed",
    "neutral-point",
    "static-margin",
    "roll-rate-approach",
    "roll-rate-nondimensional-approach",
)

#: Open MVP formulas and their ticket; an entry is removed when the formula is implemented.
OPEN_TICKETS = {"roll-rate": "#1211", "speed-from-stall-margin": "#1211"}

REPO = pathlib.Path(__file__).resolve().parent.parent
CANON_DIR = REPO / "_reversa_sdd/calculations/canon"
OUT_PATH = CANON_DIR / "navigator.html"
MODEL_PATH = REPO / "aero_kernel/canon/canon_model.json"
KERNEL_FORMULAS = REPO / "aero_kernel/formulas"


def add_front_fields(root: pathlib.Path, quantities: dict, formulas: dict) -> None:
    """Quantity type and formula worlds, which the navigator shows."""
    for slug, q in quantities.items():
        t = (root / "quantities" / f"{slug}.md").read_text(encoding="utf-8")
        q["type"] = _front(t, "type") or "scalar"
    for slug, f in formulas.items():
        t = (root / "formulas" / f"{slug}.md").read_text(encoding="utf-8")
        f["worlds"] = [w.strip() for w in _front(t, "worlds").strip("[]").split(",") if w.strip()]


def application_edges(formulas: dict, quantities: dict, model: dict) -> list:
    """Edges (input, output, formula) per application, from the canon model's bindings."""
    mf = model["namespaces"]["calc"]["formulas"]
    if set(mf) != set(formulas):
        raise SystemExit("canon model and canon documents differ; re-run the importer first")
    edges = []
    for slug, f in formulas.items():
        apps, ins_all, outs_all = [], {}, {}
        for ap in mf[slug]["applications"]:
            ins = [v.split(":", 1)[1] for v in ap["bind"].values() if isinstance(v, str)]
            ins += [g.split(":", 1)[1] for g in ap.get("given") or []]
            ins = list(dict.fromkeys(ins))
            outs = [o.split(":", 1)[1] for o in (ap["produce"] or {}).values() if o]
            apps.append({"id": ap["id"], "when": ap.get("when") or "", "ins": ins, "out": outs})
            for o in outs:
                outs_all[o] = None
                for i in ins:
                    if i == o:
                        raise SystemExit(
                            f"self-edge: {slug} lists its own output {o!r} as an input"
                        )
                    ins_all[i] = None
                    if (i, o, slug) not in edges and (i, o) not in BROKEN_EDGES:
                        edges.append((i, o, slug))
        f["apps"] = apps
        f["ins"] = [i for i in ins_all if i in quantities]
        f["out"] = list(outs_all) or f["out"]
    return edges


def layout(quantities: dict, formulas: dict, edges: list) -> dict:
    """Longest-path layers, then barycentre ordering within each layer, both ways."""
    produced = {o for f in formulas.values() for o in f["out"]}
    consumed = {a for a, _, _ in edges}
    pred = {q: [] for q in quantities}
    succ = {q: [] for q in quantities}
    for a, b, _ in edges:
        pred[b].append(a)
        succ[a].append(b)

    layer: dict = {}

    def depth(q: str, path: tuple = ()) -> int:
        if q in layer:
            return layer[q]
        if q in path:
            raise SystemExit(f"cycle through {q}; fix it in the canon")
        layer[q] = 1 + max((depth(x, path + (q,)) for x in pred[q]), default=-1)
        return layer[q]

    for q in quantities:
        depth(q)

    rows = collections.defaultdict(list)
    for q, lay in layer.items():
        rows[lay].append(q)
    for lay in rows:
        rows[lay].sort()
    pos = {q: i for lay in rows for i, q in enumerate(rows[lay])}
    for sweep in range(14):  # barycentre, both ways
        ref = pred if sweep % 2 == 0 else succ
        for lay in sorted(rows, reverse=bool(sweep % 2)):
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


def kernel_status(data: dict, kernel_dir: pathlib.Path) -> None:
    """Mark per formula its aero_kernel implementation, per quantity its status and the MVP."""
    quantities, formulas = data["Q"], data["F"]
    implemented = {}
    for path in sorted(kernel_dir.glob("*.py")):
        for slug in re.findall(r'@formula\("([a-z0-9-]+)"\)', path.read_text(encoding="utf-8")):
            implemented[slug] = f"aero_kernel/formulas/{path.name}"
    unknown = set(implemented) - set(formulas)
    if unknown:
        raise SystemExit(f"aero_kernel implements formulas the canon lacks: {sorted(unknown)}")
    stale = {slug for slug in OPEN_TICKETS if slug in implemented}
    if stale:
        raise SystemExit(f"OPEN_TICKETS lists implemented formulas, remove them: {sorted(stale)}")
    for slug, f in formulas.items():
        f["impl"] = implemented.get(slug, "")
        f["ticket"] = OPEN_TICKETS.get(slug, "")

    pred = {q: set() for q in quantities}
    for a, b, _ in data["edges"]:
        pred[b].add(a)
    mvp: set = set()
    stack = list(MVP_RESULTS)
    while stack:
        q = stack.pop()
        if q not in mvp:
            mvp.add(q)
            stack.extend(pred[q])

    produced_by: dict = {}
    for slug, f in formulas.items():
        for o in f["out"]:
            produced_by.setdefault(o, []).append(slug)
    status = {}
    for q, d in quantities.items():
        fs = produced_by.get(q, [])
        if not fs:
            status[q] = "input"
        elif any(formulas[f]["impl"] for f in fs):
            status[q] = "done" if d["type"] in ("scalar", "airplane") else "nonscalar"
        else:
            status[q] = "open"
    data["status"] = status
    data["mvp"] = sorted(mvp)
    data["mvp_results"] = list(MVP_RESULTS)


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


def build() -> tuple[str, dict]:
    """The navigator page and its data, from the canon, the canon model and the kernel."""
    quantities, formulas = read_canon(CANON_DIR)
    add_front_fields(CANON_DIR, quantities, formulas)
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    edges = application_edges(formulas, quantities, model)
    data = layout(quantities, formulas, edges)
    kernel_status(data, KERNEL_FORMULAS)
    data["stand"] = model["content_hash"][:12]
    template = pathlib.Path(__file__).with_name("canon_navigator_template.html")
    payload = json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    html = to_ascii(template.read_text(encoding="utf-8").replace("__CANON_DATA__", payload))
    assert all(ord(c) < 128 for c in html), "page is not pure ASCII"
    return html, data


def main(argv: list) -> None:
    html, data = build()
    if "--check" in argv:
        current = OUT_PATH.read_text(encoding="ascii") if OUT_PATH.exists() else ""
        if current != html:
            raise SystemExit(
                f"{OUT_PATH.relative_to(REPO)} is stale: run "
                "`poetry run python scripts/build_canon_navigator.py` and commit the result"
            )
        print("navigator is current")
        return
    OUT_PATH.write_text(html, encoding="ascii")
    done = sorted(f for f, v in data["F"].items() if v["impl"])
    print(
        f"{len(data['Q'])} quantities, {len(data['F'])} formulas, "
        f"{len(data['edges'])} edges, {len(data['order'])} layers"
    )
    print(f"{len(data['inputs'])} inputs, {len(data['outputs'])} final results")
    print(f"aero_kernel: {len(done)} formulas implemented; MVP quantities {len(data['mvp'])}")
    print(f"-> {OUT_PATH.relative_to(REPO)}  ({len(html) / 1024:.0f} KB)")


if __name__ == "__main__":
    main(sys.argv[1:])
