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
3. Eingefrorene Kopien liegen im Scratchpad der ursprünglichen Sitzung (siehe „Orte“). Sind sie weg:
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
| 2 | Unabhängige Prüfung je Paket (12 Prüfer) | läuft | siehe Tabelle unten |
| 2b | Handwerte der 21 hohen Befunde nachrechnen | fertig | 13 richtig, 1 falsch (P6b-F01), 2 unvollständig (P6b-F03, P6b-F05), 1 Formel fraglich (P7b-F03), 4 ohne Zahl; `handvalues.json` |
| 3 | Aero-Gegenprobe der überlebenden Mutationen | offen | wartet auf Schritt 2 |
| 4 | Zusammenführen: Duplikate, Schweregrade, niedrige Befunde filtern | offen | wartet auf 1–3 |
| 5 | Ablage erneuern: `findings.json`, Briefe, Schreiben, Dashboard | offen | wartet auf 4 |
| 6 | Abarbeiten der Arbeitspakete | nicht Teil dieses Laufs | braucht Freigabe |

## Schritt 1 — Produktionsfehler

| Befund | Nachgestellt | Ticket |
|---|---|---|
| P8-F08 | ja | #1434 (gilt app-weit, nicht nur für `/canon/compute`) |
| P3-F04 | ja, nur mit Test-Stub | kein Ticket: latent, über die API nicht erreichbar (`stall-speed` ist keine Eingabe, der Erzeuger liefert nie 0). Entscheidung Maintainer: Vorbedingung `stall_speed_usable` ergänzen oder lassen |
| P1-F11 | ja | #1435 |
| P7a-F05 | ja | kein Ticket: keine geschriebene Anforderung nennt `taxonomy.yaml`; Entwurfsfrage an den Maintainer |
| P7b-F08 | ja | #1436 |

Skripte und Ausgaben: `defects/<Befund>.py`, `defects/<Befund>.txt`, Zusammenfassung `defects/result.json`.

**Nebenbefund, Ticket #1437 (priority:critical, Iron Law 6):** Der nächtliche CI-Lauf `test` ist seit mindestens 2026-11-11 jeden Tag rot. Auf 72c4b5c6 (Lauf 44721669112) endet er nach 3000 s bei 22 % mit Exit 124; davor 20 fehlgeschlagene Aero-Tests ohne Traceback. Zwei davon lokal auf derselben Basis gegengeprüft: beide grün (255 s). Ursache der CI-Fehler ungeklärt. Folge für Schritt 3: die Aero-Stufe ist in CI nicht grün belegt; die Gegenprobe misst deshalb je Test zuerst die unveränderte Basis.

## Schritt 2 — Prüfung je Paket

| Paket | Befunde | Stand | bestätigt | gelesen bestätigt | widerlegt | äquivalent | nicht geprüft | Fehlerspur |
|---|---|---|---|---|---|---|---|---|
| WP-P1 | 16 | fertig | 7 | 8 | 0 | 0 | 0 | 1 |
| WP-P2 | 17 | fertig | 4 | 13 | 0 | 0 | 0 | 0 |
| WP-P3 | 18 | vergeben |  |  |  |  |  |  |
| WP-P4a | 13 | fertig | 6 | 6 | 1 | 0 | 0 | 0 |
| WP-P4b | 5 | fertig | 0 | 5 | 0 | 0 | 0 | 0 |
| WP-P5 | 19 | fertig | 5 | 12 | 2 | 0 | 0 | 0 |
| WP-P6a | 20 | vergeben |  |  |  |  |  |  |
| WP-P6b | 16 | fertig | 8 | 8 | 0 | 0 | 0 | 0 |
| WP-P7a | 18 | fertig | 9 | 8 | 0 | 0 | 0 | 1 |
| WP-P7b | 19 | fertig | 9 | 9 | 0 | 0 | 0 | 1 |
| WP-P8a | 11 | fertig | 1 | 10 | 0 | 0 | 0 | 0 |
| WP-P8b | 7 | fertig | 2 | 4 | 0 | 0 | 0 | 1 |

## Offene Entscheidungen des Maintainers

Unverändert sieben (README Abschnitt 6): P4-F07, P4-F08, P5-F08, P7a-F04, P6b-F11, P5-F06, P8-F13. Die
Befunde werden sachlich geprüft und bleiben danach als „wartet auf Entscheidung“ markiert.

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
