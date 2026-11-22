# Überarbeitung der Befunde — Logbuch

Dieses Blatt ist die einzige Quelle für den Stand der Überarbeitung. Es wird nach jedem abgeschlossenen
Teilschritt fortgeschrieben, eingecheckt und nach `github` geschoben (Zweig
`docs/canon-test-audit-2026-11-20`, PR #1433).

- **Basis:** `main` = 72c4b5c6 (unverändert seit dem Review)
- **Begonnen:** 2026-11-21
- **Umfang:** voll (alle 179 Befunde)

## Wiedereinstieg

1. Diese Datei lesen. Der erste Schritt, der nicht `fertig` ist, ist der Einstiegspunkt.
2. Das Review ist seit 2026-11-22 auf `main` (PR #1433). Das Buch zu Schritt 6 läuft auf dem Zweig
   `docs/canon-test-review-step6` in `.worktrees/canon-test-audit`.
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
| 6 | Abarbeiten der Arbeitspakete | läuft | Abschnitt „Schritt 6“ unten |

## Schritt 1 — Produktionsfehler

| Befund | Nachgestellt | Ticket |
|---|---|---|
| P8-F08 | ja | #1434 (gilt app-weit, nicht nur für `/canon/compute`) |
| P3-F04 | ja, nur mit Test-Stub | #1447 (latent, über die API nicht erreichbar; Vorbedingung `stall_speed_usable` wird ergänzt) |
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
| P5-F06 | keine Entscheidung nötig: Code fehlt nur in der Liste der Regel `positive-lengths`, Ticket #1445; der Befund bleibt offen und wird mit der Korrektur getestet |
| P8-F13 | **entschieden 2026-11-21:** einmal messen, dann löschen. Gemessen 2026-11-22: 2,8 % (Kommentar in #1142); App-Test entfernt mit PR #1446 (offen, nicht gemergt); der Kernel-seitige Schlusstest bleibt als Befund offen |
| P7b-F03 | keine Entscheidung nötig: Textfehler bei exklusiver Grenze, Ticket #1440; der Befund bleibt offen und wird mit der Korrektur getestet (erwartet „> 5“) |
| P7a-F05 | **entschieden 2026-11-21:** bleibt, wie es ist (`taxonomy.yaml` speist Tag-Prüfungen und Navigator, nicht die Rechnung); Befund gestrichen, kein Ticket |
| P3-F04 | **entschieden 2026-11-21:** Vorbedingung `stall_speed_usable` wird ergänzt: Ticket #1447 |

## Schritt 6 — Abarbeiten (Freigabe des Maintainers 2026-11-22: „ja umsetzen“)

Epic #1448. Je Paket ein Ticket, ein Worktree `.worktrees/gh-<N>`, ein Zweig `test/gh-<N>-<slug>`, ein Subagent
(Vorlage README Abschnitt 7). Nach dem Bericht: Diff lesen, **gelöschte `def test_`-Namen gegen den Brief prüfen**, schnelle Stufe selbst laufen lassen, PR öffnen, nach
grüner CI mergen. Stände: `offen` → `läuft` (Subagent gestartet) → `Bericht` (Zweig gepusht) → `PR #N` → `gemergt`.

| Welle | Paket | Ticket | Zweig | Stand |
|---:|---|---|---|---|
| 1 | WP-P4a | #1449 | test/gh-1449-p4a-cache-engine-rules | PR #1461 (9d58ac1d: 7 Tests, 7 von 7 Mutationen; nachgeprüft: Dateien grün, P4-F03 getötet) |
| 1 | WP-P7b | #1450 | test/gh-1450-p7b-evaluation | PR #1462 (8a36220e: 30 Testfälle, 9 von 9 Mutationen; nachgeprüft: Dateien grün, P7b-F01 getötet) |
| 1 | WP-P6a | #1451 | test/gh-1451-p6a-opti-fakes | PR #1466 (6f72a133: 23 Fälle, 11 von 11 Mutationen; nachgeprüft). Rest: Aero-Hälften von P6a-F09 und F10 |
| 1 | WP-P6b | #1452 | test/gh-1452-p6b-avl | PR #1465 (4fa7515a: 14 Fälle, 9 von 9 Mutationen; nachgeprüft). Rest: P6b-F12 |
| 1 | WP-P3 | #1453 | test/gh-1453-p3-powertrain-performance | PR #1463 (ac2f5bd5: 16 Tests, 12 von 12 Mutationen; nachgeprüft). Rest: P3-F16 (Aero), P1-F09 zum Teil (Frage an den Produktivcode) |
| 2 | WP-P1 | #1454 | test/gh-1454-p1-closed-form-preconditions | PR #1464 (588ae063: 12 Tests + 40 Fälle, 8 von 8 Mutationen; nachgeprüft). Rest: P1-F15 in test_tail_arms.py, P1-F13 Aero-Teil |
| 2 | WP-P2 | #1455 | test/gh-1455-p2-aero-stability | PR #1468 (36fcf1d5 + 3b810783: 19 Tests, 5 von 5 Mutationen; nach Rückgabe wiederhergestellt, Namen je Datei geprüft: nur die fünf vorgeschriebenen Umbenennungen fehlen) |
| 2 | WP-P5 | #1456 | test/gh-1456-p5-validation-geometry | PR #1470 (e68bdce6: 24 Tests, 5 von 5 Mutationen; nachgeprüft). Rest: P5-F06 mit #1445 |
| 2 | WP-P7a | #1457 | test/gh-1457-p7a-importer | PR #1467 (bb4e5411: 27 Fälle, 9 von 9 Mutationen; nachgeprüft). Rest: P7a-F17 in test_importer_abscissa.py |
| 3 | WP-P8a | #1458 | test/gh-1458-p8a-reference-fleet | PR #1472 (24e5ab66: 250 schnelle Tests, 1 von 1 Mutation; nachgeprüft). Rest: P8-F06, P8-F03 (Recorder), P8-F18 Teil 1 |
| 3 | WP-P8b | #1459 | test/gh-1459-p8b-app-layer | PR #1471 (070b0bf1: 3 neue + 3 verschärfte Tests, 4 von 4 Mutationen; nachgeprüft). Rest: P8-F13 (Aero) |
| 3 | WP-P4b | #1460 | test/gh-1460-p4b-test-isolation | PR #1469 (049468e4: 5 Tests robust, gemeinsamer Lauf 2 rot → grün, nachgeprüft). Rest: P4-F17 |

Ein Paket im Stand `läuft` ohne laufenden Subagent (nach einem Neustart): Zweig und Worktree prüfen
(`git -C .worktrees/gh-<N> log --oneline -3`, `status`); liegt kein Commit vor, Subagent neu starten.

Zusätze zu den Briefen, die im Dispatch stehen müssen: P7b-F03 nur die obere Bandgrenze prüfen (untere exklusive
Grenze gehört zu #1440); P5-F06 schlägt heute fehl und wird mit #1445 geschrieben; P8-F13 nur der Kernel-seitige
Schlusstest; Befunde mit Ticket (#1439 bis #1447) bekommen keinen Test im Paket.

**Restliste nach den Paketen (ein Nachlauf am Ende, Aero-Tests einzeln):** P3-F16 (Aero, Erwartungswerte neu herleiten);
P1-F13 Aero-Teil (`GeometryAdapter.fin_area` gegen 0,0339411 m²); P1-F15 in `test_tail_arms.py:154`;
P1-F09 Rest (`advance_ratio` bei zwei negativen Argumenten und bei NaN-Geschwindigkeit: Frage an den Maintainer);
P6a-F09/F10 Aero-Hälften (`test_solvers_opti_real.py`); P6b-F12 (aufgezeichnete Ausgaben des echten AVL je Leser: wo liegen die Dateien? Frage); P6b-F03: Rundungsregel der Streifenzahl am Seitenleitwerk steht nicht in ARCHITECTURE (Frage);
P7a-F17 in `test_importer_abscissa.py`; P8-F13 Kernel-seitiger Schlusstest (Aero);
P4-F17 (Zeit-Asserts in test_runtime*.py: Rendezvous-Mechanismus und Marge, Frage);
P8-F06 (Aero, Klammer gegen veröffentlichte Werte: gewollt? Frage); P8-F03 Golden-Recorder (Skript `scripts/canon_checks/reference_fleet/record_goldens.py`, JSON je Flugzeug + Differenzbericht: Entwurf im Bericht des Subagents, Frage wo die JSON liegen); AERONCA_CHAMP `not_converged` ohne Ticket im Fehlerregister (gleiche Art wie #1423? prüfen, dann Ticket); ULTRA_STICK_120 Masse 8,95 gegen 8,9448 kg aus 19,72 lbf (Frage);
P1-F08: ist der Aufruf `warn_flap_validity` in `maneuvering-speed` über die Engine erreichbar? (ADR 0021, Frage).

**#1437 (nächtlicher CI-Lauf):** Zweig `fix/gh-1437-nightly-ci`, Worktree `.worktrees/gh-1437`. Diagnose-Commit
teilt den Lauf in `rest` und acht Aero-Teile (nur 3.12); Lauf 45030193951 gestartet 2026-11-22. Ziel: Dauer je Teil
und Tracebacks der 20 Aero-Fehler. Danach: Ursache der Fehler klären, Aufteilung endgültig festlegen, PR.

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
- P5-F06: keine Entscheidung nötig, Ticket #1445
- P8-F13 entschieden: gemessen (2,8 %, #1142), App-Test entfernt mit PR #1446
- P3-F04 entschieden: Vorbedingung wird ergänzt, Ticket #1447. Alle Maintainer-Entscheidungen getroffen
- Dashboard-Daten auf Stand der Entscheidungen (datasets/findings Version 4, findings_v4.json)
- 2026-11-22 — PR #1433 und #1446 gemergt. Schritt 6 begonnen: Epic #1448, Tickets #1449–#1460, Welle 1 vergeben (5 Subagents). #1437: Diagnoselauf 45030193951
- Schritt 6 in der Tabelle auf läuft
- WP-P4a → PR #1461, WP-P7b → PR #1462; Welle 2 vergeben (4 Subagents)
- WP-P3 → PR #1463, WP-P1 → PR #1464; Restliste angelegt
- WP-P6b → PR #1465, WP-P6a → PR #1466 (Nummern nach Ausgabe prüfen)
- WP-P7a → PR #1467; WP-P2 zurückgegeben (neun Tests gelöscht); Welle 3 vergeben
- WP-P2 → PR #1468 (nach Wiederherstellung), WP-P4b → PR #1469
- WP-P5 → PR #1470, WP-P8b → PR #1471
- WP-P8a → PR #1472. Alle zwölf Pakete als PR offen oder gemergt
