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
| 1 | Fünf Produktionsfehler nachstellen, Bug-Tickets | läuft | — |
| 2 | Unabhängige Prüfung je Paket (12 Prüfer) | läuft | siehe Tabelle unten |
| 2b | Handwerte der 21 hohen Befunde nachrechnen | läuft | — |
| 3 | Aero-Gegenprobe der überlebenden Mutationen | offen | wartet auf Schritt 2 |
| 4 | Zusammenführen: Duplikate, Schweregrade, niedrige Befunde filtern | offen | wartet auf 1–3 |
| 5 | Ablage erneuern: `findings.json`, Briefe, Schreiben, Dashboard | offen | wartet auf 4 |
| 6 | Abarbeiten der Arbeitspakete | nicht Teil dieses Laufs | braucht Freigabe |

## Schritt 1 — Produktionsfehler

| Befund | Nachgestellt | Ticket |
|---|---|---|
| P8-F08 | — | — |
| P3-F04 | — | — |
| P1-F11 | — | — |
| P7a-F05 | — | — |
| P7b-F08 | — | — |

## Schritt 2 — Prüfung je Paket

| Paket | Befunde | Stand | bestätigt | gelesen bestätigt | widerlegt | äquivalent | nicht geprüft | Fehlerspur |
|---|---|---|---|---|---|---|---|---|
| WP-P1 | 16 | vergeben |  |  |  |  |  |  |
| WP-P2 | 17 | vergeben |  |  |  |  |  |  |
| WP-P3 | 18 | vergeben |  |  |  |  |  |  |
| WP-P4a | 13 | vergeben |  |  |  |  |  |  |
| WP-P4b | 5 | fertig | 0 | 5 | 0 | 0 | 0 | 0 |
| WP-P5 | 19 | läuft (2/19) | 0 | 0 | 2 | 0 | 0 | 0 |
| WP-P6a | 20 | vergeben |  |  |  |  |  |  |
| WP-P6b | 16 | vergeben |  |  |  |  |  |  |
| WP-P7a | 18 | vergeben |  |  |  |  |  |  |
| WP-P7b | 19 | vergeben |  |  |  |  |  |  |
| WP-P8a | 11 | vergeben |  |  |  |  |  |  |
| WP-P8b | 7 | vergeben |  |  |  |  |  |  |

## Offene Entscheidungen des Maintainers

Unverändert sieben (README Abschnitt 6): P4-F07, P4-F08, P5-F08, P7a-F04, P6b-F11, P5-F06, P8-F13. Die
Befunde werden sachlich geprüft und bleiben danach als „wartet auf Entscheidung“ markiert.

## Verlauf

- 2026-11-21 — Schritt 0 fertig. Schritte 1, 2, 2b vergeben (14 Subagents).
- 2026-11-21 — WP-P4b geprüft: 5 gelesen bestätigt; P4-F09, P4-F10, P4-F17 von mittel auf niedrig.
