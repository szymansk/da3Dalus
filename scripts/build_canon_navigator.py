"""Build the walkable calculation graph from the Markdown canon.

The navigator is **derived, never maintained**: it is regenerated from
`canon/quantities/` and `canon/formulas/` whenever the catalogue changes. Editing the
generated HTML instead would recreate exactly the duplicate problem requirement A1 warns
about.

The imported canon model (`aero_kernel/canon/canon_model.json`) is the source of everything
structural: the quantities and formulas with their roles, tools, worlds and validated tags, the
bindings the edges come from (exact per application, so a formula with several applications links
each output only to the inputs of its own application) and the taxonomy (`taxonomy.yaml`: names,
order, explanations and properties of every tag family). The template holds drawing logic and UI
text only. What the model does not carry stays in the Markdown entries: the prose a reader sees
(description, canonical form, source paragraph, status) and the issues an entry declares itself.
The page also marks the implementation status in `aero_kernel` (an `@formula("<slug>")` in
`aero_kernel/formulas/`) and the MVP (the upstream closure of `MVP_RESULTS`).

Run:   poetry run python scripts/build_canon_navigator.py
Check: poetry run python scripts/build_canon_navigator.py --check   (CI: fails if stale)
"""

from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))  # the script runs from scripts/, the package sits at the root

from aero_kernel.canon.model import DATA_KIND_PARENT, CanonModel  # noqa: E402
from aero_kernel.importer.approval import derive_approval  # noqa: E402
from aero_kernel.importer.normalise import QUANTITY_TAG_FAMILIES  # noqa: E402

#: Edges the layering breaks, with the reason. A naming collapse, not a fixed point: one
#: name covering a swept measurement and a modelled value. (The second one, a generic
#: speed bucket, was resolved in the canon on 2026-10-01 by making V a pure input.)
# Edges cut by hand. Empty since 2026-10-02: the last false cycle (C_D -> C_D0 -> C_D) was a
# naming collision, removed in the canon itself. Keep it empty; fix cycles in the canon.
BROKEN_EDGES: set = set()

GREEK = {
    "alpha": r"\alpha",
    "beta": r"\beta",
    "gamma": r"\gamma",
    "Delta": r"\Delta",
    "delta": r"\delta",
    "eta": r"\eta",
    "lambda": r"\lambda",
    "mu": r"\mu",
    "nu": r"\nu",
    "omega": r"\omega",
    "phi": r"\phi",
    "pi": r"\pi",
    "rho": r"\rho",
    "sigma": r"\sigma",
    "tau": r"\tau",
    "theta": r"\theta",
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


def _by_file(item: tuple[str, dict]) -> str:
    """Sort key: the order of the entry files (``a-b.md`` before ``a.md``), which the layout follows."""
    return item[0] + ".md"


def read_canon(root: pathlib.Path, model: dict) -> tuple[dict, dict]:
    """Quantities and formulas: structure from the canon model, prose from the Markdown entries."""
    calc = model["namespaces"]["calc"]
    quantities = {}
    for slug, mq in sorted(calc["quantities"].items(), key=_by_file):
        t = (root / "quantities" / f"{slug}.md").read_text(encoding="utf-8")
        m = re.search(r"^# .+?\n+(.+?)(?:\n\n|\Z)", t.split("---", 2)[2], re.S | re.M)
        quantities[slug] = {
            "symbol": mq["symbol"],
            "unit": _front(t, "unit"),  # as written: the model folds the em dash into 1
            "role": mq["role"],
            "unc": mq["uncertainty"] or "",
            "desc": " ".join(m.group(1).split()) if m else "",
            "type": mq["type"],
            **{family: mq[family] or "" for family in QUANTITY_TAG_FAMILIES},
            "checks": mq["checks"] or "",
        }
    formulas = {}
    for slug, mf in sorted(calc["formulas"].items(), key=_by_file):
        t = (root / "formulas" / f"{slug}.md").read_text(encoding="utf-8")
        cf = re.search(r"\*\*Canonical form\*\*\s*\n+```[a-z]*\n(.*?)\n```", t, re.S)
        form = cf.group(1).strip() if cf else ""
        source = re.search(r"\*\*Source\.\*\*.*?\n\n> (.+?)(?:\n\n|\Z)", t, re.S)
        formulas[slug] = {
            "out": [o.strip() for o in _front(t, "output").split(",") if o.strip()],
            "ins": [],
            "form": form,
            "tex": _front(t, "tex") or to_tex(form),
            "kind": mf["kind"],
            "tool": mf["tool"],
            "status": _front(t, "status"),
            "src": " ".join(source.group(1).split())[:420] if source else "",
            "worlds": mf["worlds"],
            "issues": entry_issues(t),
            "direction": mf["direction"],
        }
    return quantities, formulas


#: The MVP results (maintainer 2026-10-22): BRYAN and JAGUAR through the kernel to the stall
#: speed, neutral point and static margin, and the roll rate. The MVP is their upstream closure.
MVP_RESULTS = (
    "stall-speed",
    "neutral-point",
    "static-margin-measured",
    "centre-of-gravity-design",
    "roll-rate-approach",
    "roll-rate-nondimensional-approach",
)

#: Open MVP formulas and their ticket; an entry is removed when the formula is implemented.
OPEN_TICKETS: dict[str, str] = {}

CANON_DIR = REPO / "_reversa_sdd/calculations/canon"
OUT_PATH = CANON_DIR / "navigator.html"
MODEL_PATH = REPO / "aero_kernel/canon/canon_model.json"
KERNEL_FORMULAS = REPO / "aero_kernel/formulas"


def _clip(text: str, limit: int = 700) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\u2026"


def entry_issues(text: str) -> list:
    """The open issues an entry declares itself, read from its markers (never typed in by hand).

    - a broken assumption in the code: the "> 🔴 **...**" callout and its blockquote;
    - a conflict: the "flag/conflict" tag and its "## ⚠️ Conflict" section;
    - a missing or partial source: source_status NO_SOURCE_FOUND / PARTIAL and the Source paragraph;
    - an approximation standing where a law belongs: shape approximation;
    - a dimensional check that cannot be run: dimensional_check UNPARSEABLE.
    """
    front, body = text.split("---", 2)[1], text.split("---", 2)[2]
    issues = []
    for m in re.finditer(r"^> 🔴 \*\*(.+?)\*\*\s*\n((?:>.*\n?)+)", body, re.M):
        quote = "\n".join(line[1:].strip() for line in m.group(2).splitlines())
        issues.append({"kind": "broken", "title": m.group(1).strip(), "text": _clip(quote)})
    if "flag/conflict" in front:
        m = re.search(r"^## ⚠️ Conflict\s*\n(.*?)(?=^## |\Z)", body, re.S | re.M)
        issues.append(
            {
                "kind": "conflict",
                "title": "Two producers disagree (flag/conflict).",
                "text": _clip(m.group(1)) if m else "",
            }
        )
    status = _front(text, "source_status")
    # An approved entry has passed the gates: a missing source adopted on the maintainer's authority,
    # or an approximation approved as a declared rating, is a legitimate outcome (canon README).
    if status in ("NO_SOURCE_FOUND", "PARTIAL") and _front(text, "status") != "approved":
        m = re.search(r"^\*\*Source\.\*\*(.*?)(?=\n\n\*\*|\n## |\Z)", body, re.S | re.M)
        title = (
            "No published source found." if status == "NO_SOURCE_FOUND" else "Only partly sourced."
        )
        issues.append({"kind": "source", "title": title, "text": _clip(m.group(1)) if m else ""})
    if _front(text, "shape") == "approximation" and _front(text, "status") != "approved":
        issues.append(
            {
                "kind": "approximation",
                "title": "An approximation stands where a law belongs.",
                "text": "A rule of thumb in place of a law: it may be right to show, but it is never approved as the law for this quantity.",
            }
        )
    if _front(text, "dimensional_check") == "UNPARSEABLE":
        issues.append(
            {
                "kind": "dimensions",
                "title": "The dimensional check cannot be run.",
                "text": "The canonical form is not machine-checkable as written, so its units are unverified.",
            }
        )
    return issues


def application_edges(formulas: dict, quantities: dict, model: dict) -> list:
    """Edges (input, output, formula) per application, from the canon model's bindings."""
    mf = model["namespaces"]["calc"]["formulas"]
    if set(mf) != set(formulas):
        raise SystemExit("canon model and canon documents differ; re-run the importer first")
    constants = binding_constants(mf)
    edges = []
    for slug, f in formulas.items():
        apps, ins_all, outs_all = [], {}, {}
        for ap in mf[slug]["applications"]:
            ins = [v.split(":", 1)[1] for v in ap["bind"].values() if isinstance(v, str)]
            ins += [g.split(":", 1)[1] for g in ap.get("given") or []]
            ins = list(dict.fromkeys(ins))
            outs = [o.split(":", 1)[1] for o in (ap["produce"] or {}).values() if o]
            apps.append(
                {
                    "id": ap["id"],
                    "when": ap.get("when") or "",
                    "ins": ins,
                    "out": outs,
                    "consts": constants[slug][ap["id"]],
                }
            )
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


def closure(start: set, pred: dict) -> set:
    """The quantities in ``start`` and everything upstream of them."""
    seen: set = set()
    stack = list(start)
    while stack:
        q = stack.pop()
        if q not in seen:
            seen.add(q)
            stack.extend(pred[q])
    return seen


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
    mvp = closure(set(MVP_RESULTS), pred)

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
    design_out = {o for f in formulas.values() if f["direction"] == "design" for o in f["out"]}
    data["design"] = sorted(closure(design_out, pred))
    data["analysis"] = sorted(closure(set(quantities) - design_out - set(data["inputs"]), pred))
    data["mvp"] = sorted(mvp)
    data["mvp_results"] = list(MVP_RESULTS)


def plausibility(data: dict) -> list:
    """Module tags that contradict what a reference derives from; a hint, never a refusal.

    A reference (a quantity of a stage the taxonomy marks as ``reference``) belongs to the module
    its inputs come from. If all inputs upstream of it stand in one module and the reference is
    tagged with another, the tag or the dependency is probably wrong.
    """
    quantities = data["Q"]
    reference_stages = {s["id"] for s in data["tax"]["stages"] if s.get("reference")}
    pred = {q: set() for q in quantities}
    for a, b, _ in data["edges"]:
        pred[b].add(a)
    notes = []
    for q, d in sorted(quantities.items()):
        if d["stage"] not in reference_stages:
            continue
        sources = {quantities[x]["module"] for x in closure({q}, pred) if x in data["inputs"]}
        if len(sources) == 1 and d["module"] not in sources:
            notes.append(
                f"{q} is tagged module/{d['module']} but derives only from module/{next(iter(sources))}"
            )
    return notes


def default_marks(data: dict, model: dict) -> None:
    """Show every default of the canon model with its source and what rests on it.

    The defaults are read from the canon model (``defaults.yaml``), never typed in here. A default
    that maps to no quantity of the navigator is an error, whatever its basis. ``defaults`` holds
    per default its value, unit, basis, source, regime and the quantities and formulas downstream
    of it; ``conventions`` and ``conv`` are the ``convention`` subset: the defined values and, per
    quantity that rests on at least one of them, their slugs. ``starts`` and ``start`` are the same
    for the ``start`` basis (#1258): starting values the designer is expected to set.
    """
    defaults = dict(sorted(model["namespaces"]["calc"]["defaults"].items()))
    unknown = sorted(set(defaults) - set(data["Q"]))
    if unknown:
        raise SystemExit(f"defaults for quantities the canon lacks: {unknown}")
    succ: dict = {q: [] for q in data["Q"]}
    for a, b, f in data["edges"]:
        succ[a].append((b, f))
    shown: dict = {}
    for slug, d in defaults.items():
        seen: set = set()
        used: set = set()
        stack = [slug]
        while stack:
            q = stack.pop()
            if q not in seen:
                seen.add(q)
                for b, f in succ[q]:
                    used.add(f)
                    stack.append(b)
        shown[slug] = {
            "value": d["value"],
            "unit": d["unit"],
            "basis": d["basis"],
            "source": d["source"],
            "regime": d["regime"],
            "quantities": sorted(seen - {slug}),
            "formulas": sorted(used),
        }
    data["defaults"] = shown
    for basis, listed, rests_on in (
        ("convention", "conventions", "conv"),
        ("start", "starts", "start"),
    ):
        marked: dict = {}
        for slug, d in shown.items():
            if d["basis"] == basis:
                for q in [slug, *d["quantities"]]:
                    marked.setdefault(q, []).append(slug)
        data[listed] = {
            s: {"value": d["value"], "unit": d["unit"], "source": d["source"]}
            for s, d in shown.items()
            if d["basis"] == basis
        }
        data[rests_on] = {q: sorted(v) for q, v in sorted(marked.items())}


#: The five kinds of data source (canon README, "Two-stage approval"): id, label, explanation.
SOURCE_KINDS = (
    (
        "geometry",
        "Geometry format",
        "A field of the airplane geometry document (docs/geometry-format).",
    ),
    ("component", "Component catalogue", "A field of a component type in the parts catalogue."),
    ("default", "Defaults", "An entry of defaults.yaml: a value the canon states with its source."),
    (
        "start",
        "Starting values",
        "An entry of defaults.yaml with basis start: a starting value the designer is expected to set.",
    ),
    ("app", "Designer input in the app", "A named field the designer enters in the app."),
    (
        "evaluation",
        "Evaluation result",
        "The result of the evaluation or of the selection graph (Urmodell).",
    ),
)


def approval_marks(data: dict, model: dict) -> None:
    """Two-stage approval (#1251): per formula stage 1 and inputs k of n, per quantity its derived status.

    Stage 1 is the formula's own status in its entry; stage 2 and the quantity statuses are derived
    from the canon model by the same function the importer reports with.
    """
    stage1 = {slug: f["status"] or "draft" for slug, f in data["F"].items()}
    approval = derive_approval(CanonModel.model_validate(model), stage1)
    data["appr"] = {
        row.formula: {
            "s1": row.stage1,
            "k": row.mapped,
            "n": row.total,
            "missing": [{"q": state.quantity, "why": state.basis} for state in row.missing]
            + [{"q": "", "why": f"embedded: {blocker}"} for blocker in row.embed_blockers],
        }
        for row in approval.formulas
    }
    data["qstat"] = approval.quantity_status
    quantities = model["namespaces"]["calc"]["quantities"]
    data["qdata"] = {q: v["data"] for q, v in sorted(quantities.items()) if v.get("data")}
    data["srckinds"] = [
        {"id": k, "label": label, "explanation": text} for k, label, text in SOURCE_KINDS
    ]
    fed: dict = {}
    for quantity, sources in data["qdata"].items():
        for source in sources:
            fed.setdefault(source, []).append(quantity)
    order = {k: i for i, (k, _, _) in enumerate(SOURCE_KINDS)}
    defaults = model["namespaces"]["calc"]["defaults"]

    def parent_of(source: str, fed: list) -> str:
        """The input a source refines; a source that feeds that input itself is its root, not its child."""
        parent = DATA_KIND_PARENT.get(source.split(":", 1)[0], "")
        return "" if parent in fed else parent

    def kind_of(source: str) -> str:
        kind, loc = source.split(":", 1)
        return "start" if kind == "default" and defaults[loc]["basis"] == "start" else kind

    data["src"] = [
        {
            "id": source,
            "kind": kind_of(source),
            "loc": source.split(":", 1)[1],
            "qs": qs,
            "parent": parent_of(source, qs),
        }
        for source, qs in sorted(fed.items(), key=lambda item: (order[kind_of(item[0])], item[0]))
    ]
    data["miss"] = sorted(q for q, status in data["qstat"].items() if status == "unmapped")


def binding_constants(model_formulas: dict) -> dict:
    """Constants bound in applications (``{const, source}``): per formula, per application id.

    They are fixed by definition of the application, not overridable and not defaults.
    """
    found: dict = {}
    for slug, f in model_formulas.items():
        for ap in f["applications"]:
            consts = [
                {"param": p, "value": v["const"], "source": v["source"]}
                for p, v in ap["bind"].items()
                if isinstance(v, dict)
            ]
            found.setdefault(slug, {})[ap["id"]] = consts
    return found


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
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    quantities, formulas = read_canon(CANON_DIR, model)
    edges = application_edges(formulas, quantities, model)
    data = layout(quantities, formulas, edges)
    kernel_status(data, KERNEL_FORMULAS)
    default_marks(data, model)
    approval_marks(data, model)
    data["tax"] = model["namespaces"]["calc"]["taxonomy"]
    data["stand"] = model["content_hash"][:12]
    template = pathlib.Path(__file__).with_name("canon_navigator_template.html")
    payload = json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    html = to_ascii(template.read_text(encoding="utf-8").replace("__CANON_DATA__", payload))
    assert all(ord(c) < 128 for c in html), "page is not pure ASCII"
    return html, data


def main(argv: list) -> None:
    html, data = build()
    for note in plausibility(data):
        print(f"plausibility: {note}", file=sys.stderr)
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
