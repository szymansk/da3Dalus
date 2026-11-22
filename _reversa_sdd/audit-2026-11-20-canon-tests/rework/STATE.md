# Überarbeitung der Befunde — Logbuch

Dieses Blatt ist die einzige Quelle für den Stand der Überarbeitung. Es wird nach jedem abgeschlossenen
Teilschritt fortgeschrieben, eingecheckt und nach `github` geschoben (Zweig
`docs/canon-test-audit-2026-11-20`, PR #1433).

- **Basis:** `main` = 72c4b5c6 (unverändert seit dem Review)
- **Begonnen:** 2026-11-21
- **Umfang:** voll (alle 179 Befunde)

## Wiedereinstieg

1. Diese Datei lesen. Der erste Schritt, der nicht `fertig` ist, ist der Einstiegspunkt.
2. Arbeitskopie des Zweigs: `.worktrees/canon-test-audit` (fehlt sie:
   `git worktree add .worktrees/canon-test-audit docs/canon-test-audit-2026-11-20`).
3. Die eingefrorenen Kopien sind nach Abschluss gelöscht. Werden sie wieder gebraucht:
   je Einheit `git archive 72c4b5c6 | tar -x -C <Ordner>`, dann `git init`, `git add -A`, ein Commit.
4. Schritt 2 ist je Arbeitspaket wiederaufnehmbar: der Prüfer schreibt `verify/<WP>.json` nach jedem
   Befund. Ein Paket ist fertig, wenn jede ID aus `input/<WP>.json` in `verify/<WP>.json` steht. Für ein
   unfertiges Paket denselben Auftrag erneut vergeben (`VERIFY_BRIEF.md`); der Prüfer setzt fort.
5. Schritt 3 ist je Mutation wiederaufnehmbar: `aero/queue.json` ist die Liste, `aero/results.jsonl`
   bekommt eine Zeile je erledigtem Eintrag; das Skript überspringt Erledigtes.

## Orte

| Was | Wo |
|---|---|
| Auftrag der Prüfer | `rework/VERIFY_BRIEF.md` |
| Eingabe je Paket | `rework/input/<WP>.json` |
| Ergebnis je Paket | `rework/verify/<WP>.json` |
| Mutationen als Patch | `rework/patches/<WP>/<Befund>.patch` |
| Produktionsfehler | `rework/defects/` |
| Handwerte der hohen Befunde | `rework/handvalues.json` |
| Aero-Gegenprobe | `rework/aero/` |
| Eingefrorene Kopien | `/private/tmp/claude-501/-Users-szymanski-Projects-da3Dalus-cad-modelling-service/f61e5dfe-bbac-4dc3-a375-00d069aa35d6/scratchpad/rework/copies/<Einheit>` |

## Schritte

| # | Schritt | Stand | Ergebnis |
|---|---|---|---|
| 0 | Vorbereitung: Arbeitskopie, 14 Kopien, Eingaben, Auftrag | fertig | 2026-11-21 |
| 1 | Fünf Produktionsfehler nachstellen, Bug-Tickets | fertig | alle 5 nachgestellt; 3 Tickets, 2 an den Maintainer (siehe unten) |
| 2 | Unabhängige Prüfung je Paket (12 Prüfer) | fertig | 179 geprüft: 73 bestätigt (Mutation), 97 gelesen bestätigt, 4 widerlegt, 5 Fehlerspur |
| 2b | Handwerte der 21 hohen Befunde nachrechnen | fertig | 13 richtig, 1 falsch (P6b-F01), 2 unvollständig (P6b-F03, P6b-F05), 1 Formel fraglich (P7b-F03), 4 ohne Zahl; `handvalues.json` |
| 3 | Aero-Gegenprobe der überlebenden Mutationen | fertig | 19 Mutationen gegen 32 Aero-Tests (alle unverändert grün): 17 gefangen, 2 überleben (P6a-F09, P6b-F03); `aero/results.jsonl`, `aero/baseline.jsonl` |
| 4 | Zusammenführen: Duplikate, Schweregrade, niedrige Befunde filtern | fertig | `python3 rework/build.py`: 134 zu bearbeiten (21 hoch, 59 mittel, 54 niedrig), 29 gestrichen, 4 widerlegt, 7 warten, 5 Produktionsfehler; keine Duplikate über Paketgrenzen; `rework/summary.json` |
| 5 | Ablage erneuern: `findings.json`, Briefe, Schreiben, Dashboard | fertig | `findings.json`, `wp/*.md`, README-Nachtrag; Dashboard https://claude.ai/artifact/M7Q9tmDTkgPCQyG3ub1BM9 aktualisiert (Datenquelle `findings` auf Version 2, Seite mit Reiter „Nachprüfung“). Die Seite ist nur per Skript gegen die Daten geprüft, nicht im Browser gesehen |
| 6 | Abarbeiten der Arbeitspakete | nicht Teil dieses Laufs | braucht Freigabe |

## Schritt 1 — Produktionsfehler

| Befund | Nachgestellt | Ticket |
|---|---|---|
| P8-F08 | ja | #1434 (gilt app-weit, nicht nur für `/canon/compute`) |
| P3-F04 | ja, nur mit Test-Stub | kein Ticket: latent, über die API nicht erreichbar (`stall-speed` ist keine Eingabe, der Erzeuger liefert nie 0). Entscheidung Maintainer: Vorbedingung `stall_speed_usable` ergänzen oder lassen |
| P1-F11 | ja | #1435 |
| P7a-F05 | ja | kein Ticket: keine geschriebene Anforderung nennt `taxonomy.yaml`; vom Maintainer am 2026-11-21 gestrichen |
| P7b-F08 | ja | #1436 |

Skripte und Ausgaben: `defects/<Befund>.py`, `defects/<Befund>.txt`, Zusammenfassung `defects/result.json`.

**Nebenbefund, Ticket #1437 (priority:critical, Iron Law 6):** Der nächtliche CI-Lauf `test` ist seit mindestens 2026-11-11 jeden Tag rot. Auf 72c4b5c6 (Lauf 44721669112) endet er nach 3000 s bei 22 % mit Exit 124; davor 20 fehlgeschlagene Aero-Tests ohne Traceback. Zwei davon lokal auf derselben Basis gegengeprüft: beide grün (255 s). Ursache der CI-Fehler ungeklärt. Folge für Schritt 3: die Aero-Stufe ist in CI nicht grün belegt; die Gegenprobe misst deshalb je Test zuerst die unveränderte Basis.

## Schritt 2 — Prüfung je Paket

| Paket | Befunde | Stand | bestätigt | gelesen bestätigt | widerlegt | äquivalent | nicht geprüft | Fehlerspur |
|---|---|---|---|---|---|---|---|---|
| WP-P1 | 16 | fertig | 7 | 8 | 0 | 0 | 0 | 1 |
| WP-P2 | 17 | fertig | 4 | 13 | 0 | 0 | 0 | 0 |
| WP-P3 | 18 | fertig | 12 | 5 | 0 | 0 | 0 | 1 |
| WP-P4a | 13 | fertig | 6 | 6 | 1 | 0 | 0 | 0 |
| WP-P4b | 5 | fertig | 0 | 5 | 0 | 0 | 0 | 0 |
| WP-P5 | 19 | fertig | 5 | 12 | 2 | 0 | 0 | 0 |
| WP-P6a | 20 | fertig | 10 | 9 | 1 | 0 | 0 | 0 |
| WP-P6b | 16 | fertig | 8 | 8 | 0 | 0 | 0 | 0 |
| WP-P7a | 18 | fertig | 9 | 8 | 0 | 0 | 0 | 1 |
| WP-P7b | 19 | fertig | 9 | 9 | 0 | 0 | 0 | 1 |
| WP-P8a | 11 | fertig | 1 | 10 | 0 | 0 | 0 | 0 |
| WP-P8b | 7 | fertig | 2 | 4 | 0 | 0 | 0 | 1 |

## Entscheidungen des Maintainers

| Befund | Stand |
|---|---|
| P5-F08 | **entschieden 2026-11-21:** Flaperons sind die Mischung aus Klappe und Querruder; Flaperons zusammen mit Klappen und Querrudern sind sinnlos. Regel wird gebaut: Ticket #1439 |
| P4-F07 | war bereits entschieden (D9 vom 2026-10-17, ARCHITECTURE §8.5): Ticket #1441 |
| P4-F08 | **entschieden 2026-11-21:** die Spezifikation gilt, die `INFO`-Zeile „optional input absent“ wird gebaut: Ticket #1442 |
| P7a-F04 | **entschieden 2026-11-21:** nur die kleine Fassung von Stufe 4 (Bericht nennt geänderte Eingaben, Ausgaben, Einheiten): Task-Ticket #1443 |
| P6b-F11 | **entschieden 2026-11-21:** Zeilenzahl gegen die Kopfzeile der AVL-Ausgabe prüfen, sonst Fehler „did not complete“: Ticket #1444 |
| P5-F06, P8-F13 | offen (README Abschnitt 6) |
| P7b-F03 | keine Entscheidung nötig: Textfehler bei exklusiver Grenze, Ticket #1440; der Befund bleibt offen und wird mit der Korrektur getestet (erwartet „> 5“) |
| P7a-F05 | **entschieden 2026-11-21:** bleibt, wie es ist (`taxonomy.yaml` speist Tag-Prüfungen und Navigator, nicht die Rechnung); Befund gestrichen, kein Ticket |
| P3-F04 | offen (README Nachtrag) |

## Verlauf

- 2026-11-21 — Schritt 0 fertig. Schritte 1, 2, 2b vergeben (14 Subagents).
- 2026-11-21 — WP-P4b geprüft: 5 gelesen bestätigt; P4-F09, P4-F10, P4-F17 von mittel auf niedrig.
- 2026-11-21 — WP-P8a geprüft: 1 bestätigt, 10 gelesen bestätigt; P8-F05 mittel→hoch (nur schnelle Stufe, Aero-Kandidat offen), P8-F03/F04 mittel→niedrig.
- 2026-11-21 — WP-P7a geprüft: 9 bestätigt, 8 gelesen bestätigt, 1 Fehlerspur; P7a-F01 hoch→mittel; keine Aero-Kandidaten.
- 2026-11-21 — Schritt 2b fertig: Handwerte der hohen Befunde nachgerechnet; P6b-F01 falsch, P6b-F03/F05 unvollständig, P7b-F03 Wortlaut der exklusiven Grenze fraglich.
- 2026-11-21 — Schritt 1 fertig: Tickets #1434, #1435, #1436; P3-F04 und P7a-F05 ohne Ticket an den Maintainer. WP-P8b geprüft: P8-F09 mittel→hoch, P8-F13 mittel→niedrig. Nebenbefund: nächtlicher CI-Lauf seit ≥10 Tagen rot.
- 2026-11-21 — WP-P7b geprüft: 9 bestätigt, 9 gelesen bestätigt, 1 Fehlerspur; P7b-F02 hoch→mittel, P7b-F06 mittel→hoch; keine Aero-Kandidaten.
- 2026-11-21 — WP-P5 geprüft: 5 bestätigt, 12 gelesen bestätigt, 2 widerlegt (P4-F12, P4-F13 durch test_induced_drag.py); P5-F02 mittel→hoch; P5-F08: ARCHITECTURE.md:645 nennt die Mischung bereits zulässig.
- 2026-11-21 — WP-P4a geprüft: 6 bestätigt, 6 gelesen bestätigt, 1 widerlegt (P4-F11); P4-F01/F02/F03 bleiben hoch; ein Aero-Kandidat für P4-F04/F05.
- 2026-11-21 — WP-P6b geprüft: 8 bestätigt, 8 gelesen bestätigt; P6b-F10 mittel→hoch (Bref/Sref-Tausch, empfohlener Momenten-Assert fängt ihn nicht); P6b-F08-Patch wird heute getötet (nur Snapshot-Tests).
- 2026-11-21 — WP-P2 geprüft: 4 bestätigt, 13 gelesen bestätigt; P2-F02, P2-F04 mittel→hoch, P2-F03, P2-F06 mittel→niedrig. Ticket #1437 für den roten nächtlichen CI-Lauf.
- 2026-11-21 — WP-P1 geprüft: 7 bestätigt, 8 gelesen bestätigt, 1 Fehlerspur; P1-F13 mittel→niedrig; P1-F08 nur an der Formel bestätigt, empfohlener Engine-Test nicht umsetzbar.
- 2026-11-21 — WP-P3 geprüft: 12 bestätigt, 5 gelesen bestätigt, 1 Fehlerspur; P3-F07, P3-F08 mittel→hoch; P3-F03 hoch→mittel (Code laut gh-1429 noch nicht erreichbar); Testempfehlungen P3-F10, F12, F15 korrigiert.
- 2026-11-21 — WP-P6a geprüft: 10 bestätigt, 9 gelesen bestätigt, 1 widerlegt (P6a-F11); P6a-F04/F05/F06/F10 mittel→hoch vorbehaltlich Aero. Schritt 2 vollständig. Aero-Liste aero/queue.json geschrieben.
- 2026-11-21 — Schritt 3 gestartet (Hintergrundlauf, wiederaufnehmbar).
- 2026-11-21 — Schritt 4 begonnen: build.py führt Prüfung, Handwerte und Fehlerspur zusammen; Zwischenstand (Aero offen): 110 offen, 24 gebündelt, 29 gestrichen, 4 widerlegt, 7 warten, 5 Fehlerspur.
- 2026-11-21 — Schritte 3 und 4 fertig; findings.json, Briefe und README-Nachtrag neu erzeugt. Offen: Dashboard.
- 2026-11-21 — Schritt 5 fertig. Überarbeitung abgeschlossen; Schritt 6 (Abarbeiten) braucht Freigabe und die Entscheidungen. Eingefrorene Kopien gelöscht.
- 2026-11-21 — Entscheidung P5-F08 (Flaperons XOR Querruder + Klappen): Ticket #1439, Befund aus der Warteliste in die Fehlerspur; Schreiben und Brief WP-P5 neu erzeugt.
- 2026-11-21 — P7b-F03: keine Entscheidung, sondern Textfehler; Ticket #1440.
- 2026-11-21 — P4-F07: bereits entschieden (D9), Ticket #1441.
- P7a-F05 vom Maintainer gestrichen (taxonomy.yaml ohne Einfluss auf die Rechnung)
- P4-F08 entschieden: Logzeile wird gebaut, Ticket #1442
- P7a-F04 entschieden: kleine Fassung, Ticket #1443
- P6b-F11 entschieden: gegen die Kopfzeile zählen, Ticket #1444
