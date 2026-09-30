"""Build the JSON that check_canon.py reads, from the Markdown canon.

The canon used to be generated from an extraction JSON; the Markdown entries are the
source of truth now, so the dimensional checker had nothing left to read. This adapter
restores that: it lifts the frontmatter and the canonical form out of every entry.

Run:  poetry run python scripts/canon_to_json.py _reversa_sdd/calculations/canon out.json
"""

from __future__ import annotations

import json
import pathlib
import re
import sys


def _front(text: str, key: str) -> str | None:
    head = text.split("---", 2)[1]
    m = re.search(rf"^{key}:\s*(.+)$", head, re.M)
    return m.group(1).strip() if m else None


def _canonical_form(text: str) -> str:
    """The first fenced block after the '**Canonical form**' heading."""
    m = re.search(r"\*\*Canonical form\*\*\s*\n+```[a-z]*\n(.*?)\n```", text, re.S)
    return m.group(1).strip() if m else ""


def build(canon_dir: pathlib.Path) -> dict:
    quantities = []
    for f in sorted((canon_dir / "quantities").glob("*.md")):
        t = f.read_text(encoding="utf-8")
        quantities.append(
            {"slug": _front(t, "canon") or f.stem,
             "symbol": _front(t, "symbol"),
             "unit": _front(t, "unit")}
        )
    formulas = []
    for f in sorted((canon_dir / "formulas").glob("*.md")):
        t = f.read_text(encoding="utf-8")
        formulas.append(
            {"slug": _front(t, "canon") or f.stem,
             "output_quantity": _front(t, "output"),
             "canonical_form": _canonical_form(t),
             "kind": _front(t, "kind")}
        )
    return {"proposal": {"quantities": quantities, "formulas": formulas}}


if __name__ == "__main__":
    src = pathlib.Path(sys.argv[1])
    data = build(src)
    out = sys.argv[2] if len(sys.argv) > 2 else "-"
    text = json.dumps(data, indent=1, ensure_ascii=False)
    if out == "-":
        print(text)
    else:
        pathlib.Path(out).write_text(text, encoding="utf-8")
        p = data["proposal"]
        print(f"{len(p['quantities'])} quantities, {len(p['formulas'])} formulas -> {out}")
