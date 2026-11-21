"""Rewrite the step-2 table of STATE.md from verify/*.json and append a history line.

Usage: python ledger.py "<history line>"   (run from anywhere; paths are relative to this file)
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
ORDER = ["WP-P1", "WP-P2", "WP-P3", "WP-P4a", "WP-P4b", "WP-P5", "WP-P6a", "WP-P6b", "WP-P7a", "WP-P7b", "WP-P8a", "WP-P8b"]
COLS = ["CONFIRMED", "CONFIRMED_BY_READING", "REFUTED", "EQUIVALENT_MUTANT", "NOT_VERIFIED", "SEPARATE_DEFECT_TRACK"]

rows = [
    "| Paket | Befunde | Stand | bestätigt | gelesen bestätigt | widerlegt | äquivalent | nicht geprüft | Fehlerspur |",
    "|---|---|---|---|---|---|---|---|---|",
]
for wp in ORDER:
    want = [x["id"] for x in json.loads((HERE / "input" / f"{wp}.json").read_text())]
    out = HERE / "verify" / f"{wp}.json"
    got = {r["id"]: r for r in json.loads(out.read_text())["results"]} if out.exists() else {}
    have = sum(1 for i in want if i in got)
    state = "fertig" if have == len(want) else (f"läuft ({have}/{len(want)})" if have else "vergeben")
    count = collections.Counter(got[i]["verdict"] for i in want if i in got)
    rows.append(f"| {wp} | {len(want)} | {state} | " + " | ".join(str(count.get(c, 0)) if have else "" for c in COLS) + " |")

state_file = HERE / "STATE.md"
text = state_file.read_text()
text = re.sub(r"(## Schritt 2 — Prüfung je Paket\n\n)(\|.*\n)+", lambda m: m.group(1) + "\n".join(rows) + "\n", text)
if len(sys.argv) > 1:
    text = text.rstrip("\n") + f"\n- {sys.argv[1]}\n"
state_file.write_text(text)
print("\n".join(rows))
