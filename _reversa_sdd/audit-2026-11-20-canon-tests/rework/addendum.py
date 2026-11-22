"""Write the rework addendum into ../README.md between the rework markers (idempotent).

Usage: python addendum.py     (after build.py)
"""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
AUDIT = HERE.parent
F = json.loads((AUDIT / "findings.json").read_text())
VERIFIED = {r["id"]: r for p in sorted((HERE / "verify").glob("WP-*.json")) for r in json.loads(p.read_text())["results"]}
ACTIVE = [f for f in F if f["state"] in ("open", "bundled")]
SEV = {"high": "hoch", "medium": "mittel", "low": "niedrig"}
STATE = [
    ("open", "offen", "bestätigt; wird im Arbeitspaket bearbeitet"),
    ("bundled", "gebündelt", "bestätigt, aber klein; wird mit einem anderen Befund derselben Testdatei erledigt"),
    ("waiting_for_decision", "wartet auf Entscheidung", "sachlich bestätigt; der Test hängt an einer offenen Entscheidung"),
    ("dropped", "gestrichen", "zutreffend, aber ohne Risiko für Flugfähigkeit, Reichweite oder Nutzlast"),
    ("refuted", "widerlegt", "ein vorhandener Test fängt den Fehler bereits"),
    ("production_defect", "Produktionsfehler", "kein Testbefund; als Bug-Ticket oder Frage geführt"),
]
WAVE = {"WP-P4a": 1, "WP-P7b": 1, "WP-P6a": 1, "WP-P6b": 1, "WP-P3": 1, "WP-P1": 2, "WP-P2": 2, "WP-P5": 2, "WP-P7a": 2, "WP-P8a": 3, "WP-P8b": 3, "WP-P4b": 3}
TITLE = {
    "WP-P4a": "Cache-Schlüssel, Engine-Provenienz, Regelgrenzen",
    "WP-P7b": "Bewertung (Evaluator, Regeltabelle, Drela-Bänder)",
    "WP-P6a": "Opti-Adapter: Fakes, die Zielfunktion und Nebenbedingungen aufzeichnen",
    "WP-P6b": "AVL: Referenzgrößen, Leitwerks-Stationen, Rumpfkörper",
    "WP-P3": "Antrieb, Leistung, Flugzeit, Holm",
    "WP-P1": "Geschlossene Formeln: Vorbedingungen beidseitig",
    "WP-P2": "Aerodynamik- und Stabilitätsformeln",
    "WP-P5": "Validierung, Geometrie, Geräte",
    "WP-P7a": "Importer, check_canon, Navigator-Build",
    "WP-P8a": "Referenzflotte: Relationen, schnelle Kette, Golden-Recorder",
    "WP-P8b": "App-Anbindung: Fehlerhülle und Eingabeprüfung über den Endpunkt",
    "WP-P4b": "Test-Isolation und zeitabhängige Tests",
}


def n(rows: list[dict], **want: str) -> int:
    return sum(all(r[k] == v for k, v in want.items()) for r in rows)


def wp_table() -> list[str]:
    rows = ["| Welle | Paket | Inhalt | zu bearbeiten (hoch / mittel / niedrig) | ausgeschieden | Brief |", "|---:|---|---|---|---|---|"]
    for wp, wave in WAVE.items():
        mine = [f for f in F if f["wp"] == wp]
        act = [f for f in mine if f in ACTIVE]
        gone = ", ".join(f"{n(mine, state=s)} {label}" for s, label, _ in STATE[2:] if n(mine, state=s)) or "—"
        rows.append(f"| {wave} | {wp} | {TITLE[wp]} | {len(act)} ({n(act, severity='high')} / {n(act, severity='medium')} / {n(act, severity='low')}) | {gone} | `wp/{wp}.md` |")
    return rows


def addendum() -> str:
    c = collections.Counter(f["verdict"] for f in F)
    aero = [f for f in F if f["aero_outcome"]]
    killed = [f for f in aero if f["aero_outcome"] == "killed"]
    would_be_high = sorted(f["id"] for f in killed if VERIFIED[f["id"]]["severity_proposed"] == "high")
    high = sorted((f for f in ACTIVE if f["severity"] == "high"), key=lambda f: f["id"])
    fixes = sorted(f["id"] for f in ACTIVE if f["recommended_test_ok"] == "no" or f["hand_value_correction"])
    unclear = sorted(f["id"] for f in ACTIVE if f["recommended_test_ok"] == "unclear" and not f["hand_value_correction"])
    up = sorted(f["id"] for f in ACTIVE if f["severity"] == "high" and f["severity_review"] != "high")
    down = sorted(f["id"] for f in ACTIVE if f["severity_review"] == "high" and f["severity"] != "high")
    wave1 = sum(1 for f in high if WAVE[f["wp"]] == 1)
    out = [
        "## Nachtrag vom 21. November 2026: Nachprüfung der Befunde",
        "",
        "Die 179 Befunde des Reviews wurden einen Tag später unabhängig nachgeprüft. Dieser Abschnitt ist der gültige Stand; "
        "die Abschnitte 1 bis 6 beschreiben das Review, wie es am 20. November abgegeben wurde. `findings.json` und die zwölf Briefe "
        "unter `wp/` sind neu erzeugt und enthalten das Ergebnis der Nachprüfung.",
        "",
        "**Vorgehen.** Zwölf Prüfer, keiner davon der ursprüngliche Reviewer, je einer pro Arbeitspaket, auf einer eingefrorenen Kopie von "
        "`72c4b5c6`. Hohe und mittlere Befunde: Mutation erneut gesetzt oder neu geschrieben, gegen alle schnellen Testdateien, die die Stelle "
        "erreichen können, nicht nur gegen die Liste des Reviewers. Niedrige Befunde: gelesen und nach Zweck gefiltert. Die fünf Produktionsfehler "
        "wurden getrennt mit eigenen Skripten nachgestellt, die Handwerte der 21 hohen Befunde nachgerechnet, und 19 überlebende Mutationen "
        "liefen zusätzlich gegen gezielt gewählte Aero-Tests.",
        "",
        "### Ergebnis",
        "",
        f"{c['CONFIRMED']} Befunde sind durch eine überlebende Mutation bestätigt, {c['CONFIRMED_BY_READING']} durch Lesen, "
        f"{c['REFUTED']} sind widerlegt, {c['SEPARATE_DEFECT_TRACK']} sind Produktionsfehler und keine Testlücken.",
        "",
        "| Stand | Befunde | Bedeutung |",
        "|---|---:|---|",
        *[f"| {label} | {n(F, state=s)} | {text} |" for s, label, text in STATE],
        "",
        f"Zu bearbeiten bleiben {len(ACTIVE)} Befunde:",
        "",
        "| Schwere | im Review gemeldet | nach der Nachprüfung zu bearbeiten |",
        "|---|---:|---:|",
        *[f"| {SEV[s]} | {n(F, severity_review=s)} | {n(ACTIVE, severity=s)} |" for s in SEV],
        "",
        "Die Zahl der hohen Befunde ist zufällig gleich geblieben, die Menge nicht: "
        f"neu hoch sind {', '.join(up)}; nicht mehr hoch sind {', '.join(down)}. "
        "Regel für alle Pakete: Hoch ist ein Befund nur, wenn ein falscher Wert oder ein fehlender Fehler oder eine fehlende Warnung den "
        "Aufrufer des Kerns erreicht, die Mutation alle schnellen Tests überlebt und kein Aero-Test sie fängt.",
        "",
        "### Gegenprobe in der Aero-Stufe",
        "",
        f"Für {len(aero)} überlebende Mutationen nannten die Prüfer Aero-Tests, die den Fehler fangen müssten. Jeder dieser Tests lief zuerst "
        f"unverändert (alle grün), dann mit der Mutation. Ergebnis: {len(killed)} Mutationen werden von einem Aero-Test gefangen, "
        f"{len(aero) - len(killed)} überleben auch dort ({', '.join(sorted(f['id'] for f in aero if f['aero_outcome'] != 'killed'))}). "
        f"Für die übrigen {c['CONFIRMED'] - len(aero)} bestätigten Mutationen fand der Prüfer keinen Aero-Test, der die Stelle erreicht; das ist gelesen, nicht gemessen.",
        "",
        f"Die {len(killed)} gefangenen Lücken bestehen nur in der schnellen Stufe und sind deshalb höchstens mittel. Ohne den Aero-Test wären "
        f"{len(would_be_high)} davon hoch: {', '.join(would_be_high)}. **Dieser Schutz wirkt heute nicht:** Die PR-CI schließt die Aero-Stufe aus, "
        "und der nächtliche Lauf ist seit mindestens dem 11. November jeden Tag rot und bricht nach 50 Minuten bei 22 % ab (Ticket #1437). "
        "Solange #1437 offen ist, sind diese Befunde wie hohe zu behandeln.",
        "",
        f"### Die {len(high)} hohen Befunde nach der Nachprüfung",
        "",
        "| ID | Paket | Stelle | Was unbemerkt falsch sein könnte |",
        "|---|---|---|---|",
        *[f"| {f['id']} | {f['wp']} | `{f['production_ref']}` | {f['claim'].replace('|', '/')} |" for f in high],
        "",
        "### Widerlegte Befunde",
        "",
        "| ID | Gefangen von |",
        "|---|---|",
        *[f"| {f['id']} | " + (f"`{f['killed_by']}`" if f["killed_by"] else "`aero_kernel/tests/test_geometry_properties.py` (Aero-Stufe, durch Lesen festgestellt)") + " |" for f in F if f["state"] == "refuted"],
        "",
        "In drei Fällen lag der fangende Test in einer Datei, die der Reviewer nicht ausgeführt hatte; im vierten (P6a-F11) liegt er in der Aero-Stufe.",
        "",
        "### Korrigierte Testempfehlungen",
        "",
        f"Bei {len(fixes)} zu bearbeitenden Befunden ist die Testempfehlung des Reviews falsch oder unvollständig: {', '.join(fixes)}. "
        "Die Briefe tragen dort eine Zeile **Correction**, die den ursprünglichen Text ersetzt. "
        f"Bei {len(unclear)} weiteren hat der Prüfer die Empfehlung nicht bis zum Ende nachvollzogen (in den Briefen als `unclear` mit Grund vermerkt). "
        "Von den 21 Handwerten der hohen Befunde waren 13 richtig, einer falsch (P6b-F01: Referenzwerte des Seitenleitwerks-Tests), zwei unvollständig "
        "(P6b-F03, P6b-F05) und einer fraglich (P7b-F03, siehe Entscheidungen); vier Befunde enthalten keine Zahl.",
        "",
        "### Produktionsfehler",
        "",
        "Die fünf aus dem Review ließen sich alle nachstellen (`rework/defects/`). P5-F08 kam am 21. November durch Entscheidung des Maintainers hinzu.",
        "",
        "| Befund | Fehler | Stand |",
        "|---|---|---|",
        "| P8-F08 | Unerwartete Ausnahme verlässt die API als Klartext-500 statt in der Fehlerhülle; gilt app-weit, nicht nur für `/canon/compute` | Ticket #1434 |",
        "| P1-F11 | `lift-coefficient` bei Fluggeschwindigkeit 0 endet als `internal` | Ticket #1435 |",
        "| P7b-F08 | `@relation` für einen unbekannten Slug wird nicht gemeldet | Ticket #1436 |",
        "| P5-F08 | Die Validierung nimmt Flaperons zusammen mit getrennten Klappen und Querrudern an. Entschieden: Flaperons sind selbst die Mischung aus Klappe und Querruder, die Kombination ist sinnlos (Flaperons XOR Querruder + Klappen) | Ticket #1439; `ARCHITECTURE.md:645` wird mit der Korrektur umformuliert |",
        "| P4-F07 | `has_vertical_tail` nutzt noch die vorläufige Grundrissregel. Die Architektur (§8.5) hält die Entscheidung D9 vom 17. Oktober bereits fest: Es gilt `surface_type`. Keine neue Entscheidung nötig | Ticket #1441; rund 17 Tests in `test_graph_conditions.py` werden mit der Korrektur auf die entschiedene Regel umgestellt |",
        "| P4-F08 | Fehlt eine optionale Eingabe, schreibt der Kernel die in §8.5/§8.14/Q33 verlangte `INFO`-Zeile nicht; ein Test hält ihr Fehlen fest. Entschieden am 21. November: Die Spezifikation gilt, die Zeile wird gebaut | Ticket #1442; `test_an_absent_optional_input_adds_no_info_line` wird mit der Korrektur zum Test der Zeile |",
        "| P7a-F04 | Stufe 4 des Importers (§8.9, Diff gegen das eingecheckte Modell) ist nicht gebaut. Entschieden am 21. November: nur die kleine Fassung, der Bericht nennt geänderte Eingaben, Ausgaben und Einheiten je Eintrag; keine Zuordnung zu Implementierungen und Golden-Tests | Ticket #1443 (Task); §8.9 wird mit dem Ticket auf diesen Umfang umgeschrieben |",
        "| P6b-F11 | Eine AVL-Tabelle mit unlesbarer Zeile kommt als kürzere Lastkurve zurück, ohne Fehler (ADR 0020). Entschieden am 21. November: Zeilenzahl gegen die Kopfzeile `# Spanwise = N` der AVL-Ausgabe prüfen, sonst der vorhandene Fehler „did not complete“ | Ticket #1444; die Testvorlagen werden dabei vollständige Tabellen |",
        "| P3-F04 | `endurance-and-range-optimum` kehrt bei Überziehgeschwindigkeit exakt 0 nicht zurück | kein Ticket: über die API nicht erreichbar (`stall-speed` ist keine Eingabe, der Erzeuger liefert nie 0). Entscheidung unten |",
        "| P7a-F05 | `taxonomy.yaml` wird vom Importer nicht auf `# ESCALATED:` und YAML-1.1-Wahrheitswerte geprüft | gestrichen (Maintainer, 21. November): Die Datei speist die Tag-Prüfungen und den Navigator, nicht die Rechnung; keine geschriebene Anforderung nennt sie. Kein Ticket |",
        "",
        "Nebenbefund außerhalb des Kanons: Ticket #1437 (nächtlicher CI-Lauf rot, 20 Aero-Tests schlagen dort ohne Traceback fehl; zwei davon lokal auf demselben Stand grün).",
        "",
        "### Entscheidungen des Maintainers",
        "",
        "Von den sieben Fragen aus Abschnitt 6 ist P5-F08 entschieden (21. November: die Mischung ist sinnlos, Regel wird gebaut, Ticket #1439), P4-F07 war bereits entschieden (D9, Ticket #1441), und P4-F08 ist entschieden (21. November: die Logzeile wird gebaut, Ticket #1442). P7a-F04 ist entschieden (21. November: kleine Fassung, Ticket #1443). P6b-F11 ist entschieden (21. November: gegen die Kopfzeile zählen, Ticket #1444). P5-F06 brauchte keine Entscheidung (Ticket #1445). P8-F13 ist entschieden (messen und löschen, PR #1446). Aus Abschnitt 6 ist damit nichts mehr offen; die Befunde sind sachlich bestätigt. Aus der Nachprüfung kommt hinzu:",
        "",
        "| Befund | Frage | Empfehlung |",
        "|---|---|---|",
        "| P7b-F03 | Keine Entscheidung nötig, sondern ein Textfehler: Die Regel nach Drela ist B > 5 (B = 5 ist neutral), und die Einstufung rechnet richtig. Nur der Satz der Bewertung schreibt „≥ 5“, bei B = 5 also „5 liegt unter dem Band ≥ 5“. | Ticket #1440. Der Test zu P7b-F03 wird mit dieser Korrektur geschrieben und erwartet „> 5“. |",
        "| P5-F06 | Keine Entscheidung nötig: Die Kanon-Regel `positive-lengths` beschreibt den Exponenten bereits im Kriterium, nur ihre Code-Liste nennt `non_positive_exponent` nicht. Nach der Vorgabe vom 25. Oktober (jede Eingabeprüfung hat ihre Kanon-Regel) ist das eine Lücke im Kanon. | Ticket #1445 (ein Wort in `rules.yaml`). Der Befund bleibt offen; sein Test (Rückrichtung Code → Regel) wird mit der Korrektur geschrieben. |",
        "| P3-F04 | Vorbedingung `stall_speed_usable` auch für `endurance-and-range-optimum`, wie bei den sechs Leistungsformeln? | Ja, eine Zeile im Kanon; kein eigener Mechanismus. Einfache Alternative: lassen, da nicht erreichbar. |",
        "| P7a-F05 | Entschieden am 21. November: bleibt, wie es ist. `taxonomy.yaml` hat keinen Einfluss auf die Rechnung. | Befund gestrichen, kein Ticket. |",
        "| P8-F13 | Entschieden am 21. November: einmal messen, dann löschen. Gemessen am 22. November: Abweichung 2,8 % (V_S 8,264 gegen 8,495 m/s), festgehalten in #1142. | Der App-Test wird mit PR #1446 entfernt. Offen bleibt nur der Kernel-seitige Schlusstest (`stall-speed` gegen `max-lift-coefficient`) in WP-P8b. |",
        "",
        "### Arbeitspakete nach der Nachprüfung",
        "",
        *wp_table(),
        "",
        f"Die Wellen bleiben. Welle 1 enthält {wave1} der {len(high)} hohen Befunde. Vor Welle 1 sollte #1437 behoben sein, weil die Abnahme der "
        "17 nur in der schnellen Stufe offenen Lücken und der Schutz durch die Aero-Stufe daran hängen. WP-P4b ist weiterhin klein und früh sinnvoll: "
        "Die beiden Log-Tests sind in jedem gemeinsamen Lauf von App- und Kern-Tests rot; vier Prüfer sind unabhängig darauf gestoßen.",
        "",
        "Jede Abnahme-Mutation liegt jetzt als Patch vor (`rework/patches/<WP>/<Befund>.patch`) und wird mit `git apply` in einer Wegwerf-Kopie eingespielt.",
        "",
        "### Grenzen der Nachprüfung",
        "",
        f"- **{c['CONFIRMED_BY_READING']} Befunde sind nur durch Lesen bestätigt**, darunter alle niedrigen. Dort ist nichts gemessen.",
        "- **Die Prüfer irren auch.** Ihre Urteile sind nicht ein drittes Mal geprüft. Widerlegungen sind belegt (fangender Test genannt), Bestätigungen durch den gespeicherten Patch nachvollziehbar.",
        "- **Aero-Gegenprobe:** höchstens drei vom Prüfer gewählte Tests je Mutation. „Überlebt auch dort“ heißt: Diese Tests fangen sie nicht.",
        "- **Duplikate:** Ein Abgleich nach Produktionsstelle fand keine doppelten Befunde über Paketgrenzen. Ähnliche Befunde derselben Datei sind als gebündelt geführt.",
        "- **Gestrichene Befunde** sind nicht falsch, sondern nach Zweck aussortiert; sie stehen mit Grund am Ende jedes Briefs und in `findings.json` (`state: dropped`).",
        "- **Drei herabgestufte Befunde** (P4-F14, P4-F15, P4-F16) habe ich gegen den Wortlaut der Regel auf niedrig gesetzt, wie vom Prüfer angeregt: Kein Wert, Fehler oder Warnhinweis ist betroffen.",
        "",
        "Stand der Bearbeitung und Wiedereinstieg: `rework/STATE.md`.",
    ]
    return "\n".join(out)


def main() -> None:
    readme = AUDIT / "README.md"
    text = readme.read_text()
    block = "<!-- rework:begin -->\n" + addendum() + "\n<!-- rework:end -->\n\n"
    if "<!-- rework:begin -->" in text:
        text = re.sub(r"<!-- rework:begin -->.*?<!-- rework:end -->\n\n", lambda _m: block, text, flags=re.S)
    else:
        text = text.replace("## 1. Urteil", block + "## 1. Urteil", 1)
    head, tail = text.split("## 7. Arbeitspakete", 1)
    tail = re.sub(r"\| Welle [^\n]*\n(\|[^\n]*\n)+", lambda _m: "\n".join(wp_table()) + "\n", tail, count=1)
    text = head + "## 7. Arbeitspakete" + tail
    readme.write_text(text)
    print(addendum()[:1500])


if __name__ == "__main__":
    main()
