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
| 1 | WP-P4a | #1449 | test/gh-1449-p4a-cache-engine-rules | **gemergt** PR #1461 (9d58ac1d: 7 Tests, 7 von 7 Mutationen; nachgeprüft: Dateien grün, P4-F03 getötet) |
| 1 | WP-P7b | #1450 | test/gh-1450-p7b-evaluation | **gemergt** PR #1462 (8a36220e: 30 Testfälle, 9 von 9 Mutationen; nachgeprüft: Dateien grün, P7b-F01 getötet) |
| 1 | WP-P6a | #1451 | test/gh-1451-p6a-opti-fakes | **gemergt** PR #1466 (6f72a133: 23 Fälle, 11 von 11 Mutationen; nachgeprüft). Rest: Aero-Hälften von P6a-F09 und F10 |
| 1 | WP-P6b | #1452 | test/gh-1452-p6b-avl | **gemergt** PR #1465 (4fa7515a: 14 Fälle, 9 von 9 Mutationen; nachgeprüft). Rest: P6b-F12 |
| 1 | WP-P3 | #1453 | test/gh-1453-p3-powertrain-performance | **gemergt** PR #1463 (ac2f5bd5: 16 Tests, 12 von 12 Mutationen; nachgeprüft). Rest: P3-F16 (Aero), P1-F09 zum Teil (Frage an den Produktivcode) |
| 2 | WP-P1 | #1454 | test/gh-1454-p1-closed-form-preconditions | **gemergt** PR #1464 (588ae063: 12 Tests + 40 Fälle, 8 von 8 Mutationen; nachgeprüft). Rest: P1-F15 in test_tail_arms.py, P1-F13 Aero-Teil |
| 2 | WP-P2 | #1455 | test/gh-1455-p2-aero-stability | **gemergt** PR #1468 (36fcf1d5 + 3b810783: 19 Tests, 5 von 5 Mutationen; nach Rückgabe wiederhergestellt, Namen je Datei geprüft: nur die fünf vorgeschriebenen Umbenennungen fehlen) |
| 2 | WP-P5 | #1456 | test/gh-1456-p5-validation-geometry | **gemergt** PR #1470 (e68bdce6: 24 Tests, 5 von 5 Mutationen; nachgeprüft). Rest: P5-F06 mit #1445 |
| 2 | WP-P7a | #1457 | test/gh-1457-p7a-importer | **gemergt** PR #1467 (bb4e5411: 27 Fälle, 9 von 9 Mutationen; nachgeprüft). Rest: P7a-F17 in test_importer_abscissa.py |
| 3 | WP-P8a | #1458 | test/gh-1458-p8a-reference-fleet | **gemergt** PR #1472 (24e5ab66: 250 schnelle Tests, 1 von 1 Mutation; nachgeprüft). Rest: P8-F06, P8-F03 (Recorder), P8-F18 Teil 1 |
| 3 | WP-P8b | #1459 | test/gh-1459-p8b-app-layer | **gemergt** PR #1471 (070b0bf1: 3 neue + 3 verschärfte Tests, 4 von 4 Mutationen; nachgeprüft). Rest: P8-F13 (Aero) |
| 3 | WP-P4b | #1460 | test/gh-1460-p4b-test-isolation | **gemergt** PR #1469 (049468e4: 5 Tests robust, gemeinsamer Lauf 2 rot → grün, nachgeprüft). Rest: P4-F17 |

Ein Paket im Stand `läuft` ohne laufenden Subagent (nach einem Neustart): Zweig und Worktree prüfen
(`git -C .worktrees/gh-<N> log --oneline -3`, `status`); liegt kein Commit vor, Subagent neu starten.

Zusätze zu den Briefen, die im Dispatch stehen müssen: P7b-F03 nur die obere Bandgrenze prüfen (untere exklusive
Grenze gehört zu #1440); P5-F06 schlägt heute fehl und wird mit #1445 geschrieben; P8-F13 nur der Kernel-seitige
Schlusstest; Befunde mit Ticket (#1439 bis #1447) bekommen keinen Test im Paket.

**Stand 2026-11-22:** alle zwölf Pakete gemergt (PR #1461–#1472). Schnelle Stufe auf dem zusammengeführten `main`
(47187715), Kern + `scripts/tests` + drei App-Canon-Dateien gemeinsam: 5565 bestanden. Abnahmelauf auf `main`:
alle 82 Patches einzeln eingespielt, schnelle Stufe je Patch: **82 von 82 getötet** (Ergebnis in `rework/accept-main-47187715.tsv`).
81 direkt; P3-F07 stand als `patch_failed`, weil der Patch gegen einen älteren Stand der Datei geschrieben war (der Patch passte
schon auf c08ac601 nicht). Von Hand nachgestellt: `test_the_best_rate_of_climb_vertical_is_declared_too` wird rot; der Patch ist neu erzeugt.
Tickets: #1449, #1450, #1455 durch den PR geschlossen; die übrigen neun bleiben offen bis die Restliste erledigt ist.

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

**Restliste, Stand nach PR #1473 (Zweig `test/gh-1448-review-leftovers`, Worktree `.worktrees/gh-1448-leftovers`):**
erledigt im PR: P1-F15, P7a-F17, P3-F16, P1-F13 (Aero, eigene Handgeometrie statt 0,0339411 m², die zu keiner Fixture passt),
P6a-F09/F10 (F09 wird nur in der schnellen Stufe getötet, der Aero-Test überlebt die Mutation wie vom Prüfer vorhergesagt),
P8-F13 Kernel-Schlusstest, P8-F18 Teil 1 (vier Flugzeuge). GEE_BEE_R3: Landeklappe 30° ergibt V_S 11,345 über sauber 11,119 m/s;
der Kern deklariert dort `flap_confidence_low` (Regel `flap-model-validity`, #1314 zuständig) — kein neuer Fehler, Test prüft die Warnung.
AERONCA_CHAMP: Massenband 0,332–0,39 kg `not_converged`, 0,273 und ab 0,41 kg rechnet; gleiche Meldung wie #1423, als Kommentar an #1423
gehängt; Register-Eintrag bleibt bei `ROOT_ERRORS_AWAITING_AN_ISSUE`, bis der Maintainer #1423 als Eigentümer bestätigt.
Offen danach: P8-F18 Teile 2 und 3, P5-F06 (mit #1445), P7b-F03 (mit #1440) und die Fragen an den Maintainer
(P4-F17, P6b-F12, P8-F03, P1-F09 Rest, P6b-F03, P1-F08, P8-F06, ULTRA_STICK_120-Masse, #1423 als Eigentümer für AERONCA_CHAMP).
PR #1473 **gemergt** (86beb0b8, CI + Sonar grün), Worktree entfernt. Fragen an den Maintainer laufen einzeln; erste gestellt: P1-F08.

**#1437, Stand nach der Diagnose (Kommentar im Ticket, issuecomment-7083369713):** Ursache 1: dem AVL-Binary fehlt auf dem
Runner `liblapack.so.3` (Exit 127); mit `apt-get install liblapack3` wird aero-2 grün (Lauf 45052390415), Korrektur ist im Zweig.
Ursache 2: der Teil `rest` beendet seine Tests nach 73 min und der Prozess endet dann nicht (Grund offen; Lauf 45053284171 schickt
nach 100 min SIGABRT, faulthandler gibt die Threads aus). Ursache 3: ein sequentieller Job über zwei Python-Versionen ist zu lang.
Offen: 27 Fehler + 2 Errors im Teil `rest`, die nicht alle von AVL kommen (Liste im Ticket), und ein Timeout in
`test_mass_envelope_aero.py`. Nächster Schritt: Lauf 45053284171 auswerten (alle neun Teile mit liblapack3), dann endgültige
Aufteilung des Jobs (Coverage-Upload und 3.11/3.12-Matrix wiederherstellen), PR; für die verbleibenden App-Testfehler ein eigenes Ticket.

**#1437 geschlossen (PR #1476, b1174db7):** nächtlicher Job in neun Teilen (`rest`, `aero-0…7`) für 3.11 und 3.12, `liblapack3`
in `nightly` und `full`, Prüfschritt „AVL startet“, SIGABRT am Zeitlimit. Lauf 45053284171 (alle Teile, 3.12, mit liblapack3):
Kern 5847 bestanden, 18 fehlgeschlagen → Bug **#1474** (9 Wertabweichungen Linux gegen macOS-Goldens, 7 Zeitlimits);
Teil `rest` 13 fehlgeschlagen + 2 Errors und der Prozess endet nicht (Thread-Dump: `_python_exit` wartet auf einen Pool-Worker,
vermutlich die CAD-Aufgabe von `test_ehawk_designer_workflow_stepwise`) → Bug **#1475** (priority:critical).
Der nächtliche Lauf bleibt rot, bis #1474 und #1475 behoben sind; beide Tickets sind nicht begonnen.
Verifikationslauf der Endfassung auf main 45071176949: 18 Jobs, längster 3 h 20 min, kein Job am Limit; dieselben 16 Kern-Tests rot auf 3.11 und 3.12 (#1474), `rest` 3.12 wie #1475; ein Job scheiterte an `poetry install` (Connection reset, kalter Cache, zum zweiten Mal — Retry um den Installationsschritt wäre die Abhilfe, nicht gemacht). Worktree `.worktrees/gh-1437` ist entfernt.

**Stand 2026-11-27.** P1-F08 entschieden (Maintainer: V_A nur saubere Konfiguration, Code folgt): Task #1477, PR #1478 gemergt
(1b7049d2) — Aufruf `warn_flap_validity` aus `maneuvering-speed` entfernt, der WP-P1-Test des entfernten Verhaltens durch zwei Tests
des beschlossenen Verhaltens ersetzt. Entscheidungsvorlage: https://claude.ai/artifact/JaNxNynRYAYYuAq5bxz9A4.
Auftrag „CI wieder grün“: **#1475** → PR #1482 (Zweig `fix/gh-1475-nightly-app-tests`, Worktree `.worktrees/gh-1475`): 11 veraltete
Tests angepasst, `cad_service.shutdown_executor` beendet noch rechnende Worker (Test vorher rot); vier Tests bleiben rot wegen
Produktionsfehlern → Bugs #1479 (Holm-Einbau ohne surface_type), #1480 (GeneralJSONDecoder list→str, cad_designer gesperrt, braucht
Freigabe), #1481 (Holm-Roundtrip/Vase-Rippenschnitt, endlose Designer-Aufgabe, Linux-only test_shape_tolerant).
**#1474**: Hypothese — Linux-Wheel von AVL ist einfache Genauigkeit + LAPACK (`avl-binary/Dockerfile.avl-amd64`), macOS-Binary
ruft nur double-Mathefunktionen (Indiz für doppelte Genauigkeit); alle Abweichungen liegen in AVL-Größen. Gegenlauf 45991083115
(Zweig `fix/gh-1474-kernel-aero-linux`, Worktree `.worktrees/gh-1474`, Teile `single`/`double`: AVL auf dem Runner in DP gebaut)
auswerten. Bestätigt es sich: neues Linux-Wheel in DP (Release = Rückfrage beim Maintainer), sonst weiter suchen.
Noch offen aus der Restliste: Fragen P4-F17, P6b-F12, P8-F03, P1-F09 Rest, P6b-F03, P8-F06, ULTRA_STICK_120-Masse, #1423 für AERONCA_CHAMP.

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
- Alle zwölf Pakete gemergt (PR #1461–#1472); main in der schnellen Stufe grün (5565); Abnahmelauf über alle Patches gestartet
- Abnahmelauf auf main: 82 von 82 Mutationen getötet (P3-F07 von Hand nachgestellt, Patch erneuert)
- Restliste: PR #1473 offen, GEE_BEE_R3 und AERONCA_CHAMP geklärt
- PR #1473 gemergt; erste Maintainer-Frage P1-F08 gestellt
- #1437: Ursache liblapack3 belegt, zweiter Diagnoselauf 45053284171 läuft
- #1437 geschlossen (PR #1476); Folgetickets #1474, #1475
- #1437: Verifikationslauf der Endfassung ausgewertet
- P1-F08 erledigt (PR #1478); #1475 PR #1482, Folgetickets #1479–#1481; #1474 Gegenlauf läuft
