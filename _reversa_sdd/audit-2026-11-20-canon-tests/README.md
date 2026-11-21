# Review der Kanon-Tests — Empfehlungsschreiben

**Stand:** Review vom 20. November 2026, Nachprüfung der Befunde vom 21. November 2026 · Commit `72c4b5c6` (main) · Verfasser: Testmanagement (Claude) im Auftrag des Maintainers

**Gegenstand:** die Tests des Rechenkanons: `aero_kernel/tests/` (219 Dateien), `app/tests/test_canon_*.py` (5), `scripts/tests/test_check_canon.py` und `test_build_canon_navigator.py`. Zusammen 225 Testdateien, 3305 Testfunktionen, 5754 Testfälle (5021 schnelle Stufe, 733 Aero-Stufe).

**Frage des Auftrags:** Erzeugen die Tests nur hohe Coverage, oder prüfen sie die fachlichen Anforderungen und die Randfälle?

<!-- rework:begin -->
## Nachtrag vom 21. November 2026: Nachprüfung der Befunde

Die 179 Befunde des Reviews wurden einen Tag später unabhängig nachgeprüft. Dieser Abschnitt ist der gültige Stand; die Abschnitte 1 bis 6 beschreiben das Review, wie es am 20. November abgegeben wurde. `findings.json` und die zwölf Briefe unter `wp/` sind neu erzeugt und enthalten das Ergebnis der Nachprüfung.

**Vorgehen.** Zwölf Prüfer, keiner davon der ursprüngliche Reviewer, je einer pro Arbeitspaket, auf einer eingefrorenen Kopie von `72c4b5c6`. Hohe und mittlere Befunde: Mutation erneut gesetzt oder neu geschrieben, gegen alle schnellen Testdateien, die die Stelle erreichen können, nicht nur gegen die Liste des Reviewers. Niedrige Befunde: gelesen und nach Zweck gefiltert. Die fünf Produktionsfehler wurden getrennt mit eigenen Skripten nachgestellt, die Handwerte der 21 hohen Befunde nachgerechnet, und 19 überlebende Mutationen liefen zusätzlich gegen gezielt gewählte Aero-Tests.

### Ergebnis

73 Befunde sind durch eine überlebende Mutation bestätigt, 97 durch Lesen, 4 sind widerlegt, 5 sind Produktionsfehler und keine Testlücken.

| Stand | Befunde | Bedeutung |
|---|---:|---|
| offen | 110 | bestätigt; wird im Arbeitspaket bearbeitet |
| gebündelt | 24 | bestätigt, aber klein; wird mit einem anderen Befund derselben Testdatei erledigt |
| wartet auf Entscheidung | 7 | sachlich bestätigt; der Test hängt an einer offenen Entscheidung |
| gestrichen | 29 | zutreffend, aber ohne Risiko für Flugfähigkeit, Reichweite oder Nutzlast |
| widerlegt | 4 | ein vorhandener Test fängt den Fehler bereits |
| Produktionsfehler | 5 | kein Testbefund; als Bug-Ticket oder Frage geführt |

Zu bearbeiten bleiben 134 Befunde:

| Schwere | im Review gemeldet | nach der Nachprüfung zu bearbeiten |
|---|---:|---:|
| hoch | 21 | 21 |
| mittel | 79 | 59 |
| niedrig | 79 | 54 |

Die Zahl der hohen Befunde ist zufällig gleich geblieben, die Menge nicht: neu hoch sind P2-F04, P3-F07, P3-F08, P5-F02, P7b-F06, P8-F09; nicht mehr hoch sind P1-F01, P3-F03, P6b-F01, P6b-F05, P7a-F01, P7b-F02. Regel für alle Pakete: Hoch ist ein Befund nur, wenn ein falscher Wert oder ein fehlender Fehler oder eine fehlende Warnung den Aufrufer des Kerns erreicht, die Mutation alle schnellen Tests überlebt und kein Aero-Test sie fängt.

### Gegenprobe in der Aero-Stufe

Für 19 überlebende Mutationen nannten die Prüfer Aero-Tests, die den Fehler fangen müssten. Jeder dieser Tests lief zuerst unverändert (alle grün), dann mit der Mutation. Ergebnis: 17 Mutationen werden von einem Aero-Test gefangen, 2 überleben auch dort (P6a-F09, P6b-F03). Für die übrigen 54 bestätigten Mutationen fand der Prüfer keinen Aero-Test, der die Stelle erreicht; das ist gelesen, nicht gemessen.

Die 17 gefangenen Lücken bestehen nur in der schnellen Stufe und sind deshalb höchstens mittel. Ohne den Aero-Test wären 10 davon hoch: P1-F01, P2-F02, P6a-F04, P6a-F05, P6a-F06, P6a-F10, P6b-F01, P6b-F05, P6b-F10, P8-F05. **Dieser Schutz wirkt heute nicht:** Die PR-CI schließt die Aero-Stufe aus, und der nächtliche Lauf ist seit mindestens dem 11. November jeden Tag rot und bricht nach 50 Minuten bei 22 % ab (Ticket #1437). Solange #1437 offen ist, sind diese Befunde wie hohe zu behandeln.

### Die 21 hohen Befunde nach der Nachprüfung

| ID | Paket | Stelle | Was unbemerkt falsch sein könnte |
|---|---|---|---|
| P1-F02 | WP-P1 | `aero_kernel/formulas/sink_rate.py:29` | lift_coefficient_positive can reject every lift coefficient and no test fails: sink-rate has no 'held' case for C_L and is never requested through the engine in any tier, so a sink rate that is never computed would go unnoticed. |
| P2-F01 | WP-P2 | `aero_kernel/formulas/butterfly_approach.py:152-157` | butterfly-approach can drop every caveat of its reference solves (Reynolds regime, drag messages of the landing stall and of the closing sample) and no test fails; ADR 0020 requires them declared. The early-return path (s_max = 0) forwards nothing testable either. |
| P2-F04 | WP-P2 | `aero_kernel/formulas/butterfly_approach.py:290-291` | The test cannot tell 'mix with the largest deflection' from 'always full crow': at s = 1 the raised aileron is carried as a flap at -40 deg, above the 30 deg limit, so the declaration appears either way and only its presence is asserted. |
| P3-F01 | WP-P3 | `aero_kernel/formulas/endurance_and_range_optimum.py:116` | The canon constraint r_T(V) <= 1 of the optimum can be dropped: max-endurance/max-range are then returned at a speed the drive train cannot hold, instead of no_level_flight_speed or a declared full_throttle bound. |
| P3-F02 | WP-P3 | `aero_kernel/formulas/motor_propeller_part_load.py:300` | A negative battery power (reachable with a table whose C_P is negative at the part-load point) would give a negative flight time and range instead of non_positive_battery_power. |
| P3-F07 | WP-P3 | `aero_kernel/formulas/best_rate_of_climb.py:62` | best-rate-of-climb can stop declaring that its optimum lies on the vertical bound or on the stall corner (powered_limit_declared) without any test failing; the test named 'is declared too' asserts no declaration. |
| P3-F08 | WP-P3 | `aero_kernel/formulas/static_thrust_to_weight.py:49` | static-thrust-to-weight can drop its route notice (which route ran, R_m is the winding only, nominal voltage; Q-PT-6 / ADR 0020) unnoticed. |
| P4-F01 | WP-P4a | `aero_kernel/engine.py:568` | The engine can drop the world assignment from the node cache key without any test failing. With a cache, all worlds of a node whose worlds share a tool then share one entry: the interval collapses to the first world's value (observed under the mutation: {'unc=alpha': 10.0, 'unc=beta': 10.0, 'unc=gamma': 10.0} instead of 10/20/30) and is served as such on later calls. |
| P4-F02 | WP-P4a | `aero_kernel/engine.py:588-595` | If the engine stops releasing a cache claim when a node run is cancelled or the time budget expires, every later call on the same CachedKernel that needs that key waits forever (observed under the mutation: the second call still hangs after 3 s, after a timed-out call and after a cancelled one). No test notices. |
| P4-F03 | WP-P4a | `aero_kernel/engine.py:193-197` | A polar that a node reads can be left out of that node's cache key (replaced by a constant) without any test failing: a reader of a changed polar would then be served the value computed from the old polar. |
| P5-F01 | WP-P5 | `aero_kernel/validate.py:886` | The conflicting_mass notice can disappear for every what-if at a mass above the geometry's total_mass_kg without a test failing: all tests pass a mass below the stored one. |
| P5-F02 | WP-P5 | `aero_kernel/validate.py:1110` | A NaN or infinite airplane.xyz_ref, which the ASB and AVL conversions read as the moment reference point, can stop being reported. |
| P6a-F01 | WP-P6a | `aero_kernel/solvers/opti.py:2299` | level_polar could check the regime at the slowest point only: a Mach or Re-above-band warning of the fastest point (up to the `error` mach_beyond_validity) would be dropped and no test fails. |
| P6a-F02 | WP-P6a | `aero_kernel/solvers/opti.py:2397` | sweep could accept a deflected flap (flaps_supported=True) and return the polar of the flapped airplane without any caveat, although ch. 8.8 says sweep refuses a flap because it returns no warnings. |
| P6a-F03 | WP-P6a | `aero_kernel/solvers/opti.py:2238` | best_glide could drop the flap caveats (hinge_line_averaged, control_surface_fit_range_unknown) of a flapped configuration: an undeclared model substitution (ADR 0020). The same declaration is untested for min_sink (opti.py:2442) and level_flight_point (opti.py:2367). |
| P6b-F03 | WP-P6b | `aero_kernel/solvers/avl_hinge.py:265` | On a horizontal tail or fin of the hinge-moment mesh the stations are unchecked: the device ends need not be stations (a part-span elevator or rudder then controls the wrong strips or, with one bounding section lacking the CONTROL, none: AVL drives a strip only if both sections declare it), the tail need not take the wing's stations, and slivers next to a break need not be dropped. |
| P7b-F01 | WP-P7b | `aero_kernel/evaluation/evaluator.py:199` | A quantity the kernel returned with status error or skipped can be reported as not_applicable ('The kernel found it not applicable: no reason given') instead of not_available, and no test fails. The consumer then reads a failed computation as 'the rule does not apply to this aircraft'. |
| P7b-F03 | WP-P7b | `aero_kernel/evaluation/evaluator.py:294` | The verdict text of a one-sided band can state the band in the wrong direction ('≥ 15' for the limit ≤ 15 deg, '≤ 5' for B > 5) and no test fails. Turn sideslip and all three spiral rules of the shipped table have one-sided bands, and the text is the LLM-facing contract. |
| P7b-F04 | WP-P7b | `aero_kernel/evaluation/rule_table.json` | Three decided properties of the shipped rule table can change without a failing fast test: the band of the two circling rules over spiral-parameter-mp (5 -> 4), the severity of spiral-stability-circling-aileron below the band (caution -> bad, maintainer decision 2026-10-26), and the level edges of turn-sideslip (5 -> 6 deg). |
| P7b-F06 | WP-P7b | `aero_kernel/evaluation/evaluator.py:257` | An interval whose ends lie in two different levels can be reported with the level of its lower end (and that level's meaning in the text) without a failing test; the rule 'one level only if both ends share it' is unpinned. |
| P8-F09 | WP-P8b | `app/services/canon_service.py:262` | Every fast endpoint and service test replaces the whole kernel, so the kernel's own input validation and per-quantity errors never pass through the endpoint outside the aero tier: Q8 (mass <= 0 -> invalid_input with input_path) and an unknown quantity are unpinned at the API. Invalid input also has two shapes (422 envelope with details.input_errors as dicts for a parse failure, 200 with body.input_errors as KernelError for inadmissible values) and no test states the split. |

### Widerlegte Befunde

| ID | Gefangen von |
|---|---|
| P4-F11 | `aero_kernel/tests/test_aileron_deflection_required_engine.py::test_a_target_above_the_aerobuildup_maximum_is_an_error_with_the_avl_value` |
| P6a-F11 | `aero_kernel/tests/test_geometry_properties.py` (Aero-Stufe, durch Lesen festgestellt) |
| P4-F12 | `aero_kernel/tests/test_induced_drag.py::test_an_override_outside_the_range_is_refused[0.0-non_positive_value]` |
| P4-F13 | `aero_kernel/tests/test_induced_drag.py::test_an_override_inside_the_range_is_accepted[1.0]` |

In drei Fällen lag der fangende Test in einer Datei, die der Reviewer nicht ausgeführt hatte; im vierten (P6a-F11) liegt er in der Aero-Stufe.

### Korrigierte Testempfehlungen

Bei 10 zu bearbeitenden Befunden ist die Testempfehlung des Reviews falsch oder unvollständig: P1-F08, P2-F03, P2-F04, P2-F06, P3-F10, P3-F12, P6b-F01, P6b-F03, P6b-F05, P7a-F12. Die Briefe tragen dort eine Zeile **Correction**, die den ursprünglichen Text ersetzt. Bei 17 weiteren hat der Prüfer die Empfehlung nicht bis zum Ende nachvollzogen (in den Briefen als `unclear` mit Grund vermerkt). Von den 21 Handwerten der hohen Befunde waren 13 richtig, einer falsch (P6b-F01: Referenzwerte des Seitenleitwerks-Tests), zwei unvollständig (P6b-F03, P6b-F05) und einer fraglich (P7b-F03, siehe Entscheidungen); vier Befunde enthalten keine Zahl.

### Produktionsfehler

Alle fünf ließen sich nachstellen (`rework/defects/`).

| Befund | Fehler | Stand |
|---|---|---|
| P8-F08 | Unerwartete Ausnahme verlässt die API als Klartext-500 statt in der Fehlerhülle; gilt app-weit, nicht nur für `/canon/compute` | Ticket #1434 |
| P1-F11 | `lift-coefficient` bei Fluggeschwindigkeit 0 endet als `internal` | Ticket #1435 |
| P7b-F08 | `@relation` für einen unbekannten Slug wird nicht gemeldet | Ticket #1436 |
| P3-F04 | `endurance-and-range-optimum` kehrt bei Überziehgeschwindigkeit exakt 0 nicht zurück | kein Ticket: über die API nicht erreichbar (`stall-speed` ist keine Eingabe, der Erzeuger liefert nie 0). Entscheidung unten |
| P7a-F05 | `taxonomy.yaml` wird vom Importer nicht auf `# ESCALATED:` und YAML-1.1-Wahrheitswerte geprüft | kein Ticket: keine geschriebene Anforderung nennt die Datei. Entscheidung unten |

Nebenbefund außerhalb des Kanons: Ticket #1437 (nächtlicher CI-Lauf rot, 20 Aero-Tests schlagen dort ohne Traceback fehl; zwei davon lokal auf demselben Stand grün).

### Entscheidungen des Maintainers

Die sieben Fragen aus Abschnitt 6 sind unverändert offen; die Befunde sind sachlich bestätigt. Aus der Nachprüfung kommt hinzu:

| Befund | Frage | Empfehlung |
|---|---|---|
| P5-F08 | Ergänzung zur bestehenden Frage: `aero_kernel/ARCHITECTURE.md:645` sagt bereits „a mixed set (flaps, ailerons and flaperons) needs no special rule (KISS, D10)“. Das widerspricht der Lesart „Flaperons XOR Querruder + Klappen“. | Architektur gilt: Mischung ist zulässig, ein Test hält das fest. |
| P7b-F03 | `_band_text` ignoriert, ob eine Grenze exklusiv ist: Für B > 5 lautet der Text „≥ 5“. Der empfohlene Test würde diesen Wortlaut festschreiben. | Wortlaut zuerst festlegen („> 5“ für exklusive Grenzen), dann testen. Einfache Alternative: Test nur mit inklusiver Grenze. |
| P3-F04 | Vorbedingung `stall_speed_usable` auch für `endurance-and-range-optimum`, wie bei den sechs Leistungsformeln? | Ja, eine Zeile im Kanon; kein eigener Mechanismus. Einfache Alternative: lassen, da nicht erreichbar. |
| P7a-F05 | Soll der Importer `taxonomy.yaml` wie die anderen Kanon-Dateien prüfen? | Ja, ein Aufruf von `_scan_front_matter`. Einfache Alternative: lassen und in §8.9 vermerken. |
| P8-F13 | Ergänzung: Der Test läuft derzeit nirgends, weil der nächtliche Lauf vorher abbricht (#1437). Ob er rot oder grün ist, ist unbekannt. | Nach #1437 einmal ausführen und das Ergebnis in gh-1142 festhalten. |

### Arbeitspakete nach der Nachprüfung

| Welle | Paket | Inhalt | zu bearbeiten (hoch / mittel / niedrig) | ausgeschieden | Brief |
|---:|---|---|---|---|---|
| 1 | WP-P4a | Cache-Schlüssel, Engine-Provenienz, Regelgrenzen | 7 (3 / 3 / 1) | 2 wartet auf Entscheidung, 3 gestrichen, 1 widerlegt | `wp/WP-P4a.md` |
| 1 | WP-P7b | Bewertung (Evaluator, Regeltabelle, Drela-Bänder) | 12 (4 / 5 / 3) | 6 gestrichen, 1 Produktionsfehler | `wp/WP-P7b.md` |
| 1 | WP-P6a | Opti-Adapter: Fakes, die Zielfunktion und Nebenbedingungen aufzeichnen | 16 (3 / 7 / 6) | 3 gestrichen, 1 widerlegt | `wp/WP-P6a.md` |
| 1 | WP-P6b | AVL: Referenzgrößen, Leitwerks-Stationen, Rumpfkörper | 14 (1 / 8 / 5) | 1 wartet auf Entscheidung, 1 gestrichen | `wp/WP-P6b.md` |
| 1 | WP-P3 | Antrieb, Leistung, Flugzeit, Holm | 14 (4 / 6 / 4) | 3 gestrichen, 1 Produktionsfehler | `wp/WP-P3.md` |
| 2 | WP-P1 | Geschlossene Formeln: Vorbedingungen beidseitig | 13 (1 / 7 / 5) | 2 gestrichen, 1 Produktionsfehler | `wp/WP-P1.md` |
| 2 | WP-P2 | Aerodynamik- und Stabilitätsformeln | 14 (2 / 2 / 10) | 3 gestrichen | `wp/WP-P2.md` |
| 2 | WP-P5 | Validierung, Geometrie, Geräte | 13 (2 / 6 / 5) | 2 wartet auf Entscheidung, 2 gestrichen, 2 widerlegt | `wp/WP-P5.md` |
| 2 | WP-P7a | Importer, check_canon, Navigator-Build | 13 (0 / 9 / 4) | 1 wartet auf Entscheidung, 3 gestrichen, 1 Produktionsfehler | `wp/WP-P7a.md` |
| 3 | WP-P8a | Referenzflotte: Relationen, schnelle Kette, Golden-Recorder | 8 (0 / 5 / 3) | 3 gestrichen | `wp/WP-P8a.md` |
| 3 | WP-P8b | App-Anbindung: Fehlerhülle und Eingabeprüfung über den Endpunkt | 5 (1 / 1 / 3) | 1 wartet auf Entscheidung, 1 Produktionsfehler | `wp/WP-P8b.md` |
| 3 | WP-P4b | Test-Isolation und zeitabhängige Tests | 5 (0 / 0 / 5) | — | `wp/WP-P4b.md` |

Die Wellen bleiben. Welle 1 enthält 15 der 21 hohen Befunde. Vor Welle 1 sollte #1437 behoben sein, weil die Abnahme der 17 nur in der schnellen Stufe offenen Lücken und der Schutz durch die Aero-Stufe daran hängen. WP-P4b ist weiterhin klein und früh sinnvoll: Die beiden Log-Tests sind in jedem gemeinsamen Lauf von App- und Kern-Tests rot; vier Prüfer sind unabhängig darauf gestoßen.

Jede Abnahme-Mutation liegt jetzt als Patch vor (`rework/patches/<WP>/<Befund>.patch`) und wird mit `git apply` in einer Wegwerf-Kopie eingespielt.

### Grenzen der Nachprüfung

- **97 Befunde sind nur durch Lesen bestätigt**, darunter alle niedrigen. Dort ist nichts gemessen.
- **Die Prüfer irren auch.** Ihre Urteile sind nicht ein drittes Mal geprüft. Widerlegungen sind belegt (fangender Test genannt), Bestätigungen durch den gespeicherten Patch nachvollziehbar.
- **Aero-Gegenprobe:** höchstens drei vom Prüfer gewählte Tests je Mutation. „Überlebt auch dort“ heißt: Diese Tests fangen sie nicht.
- **Duplikate:** Ein Abgleich nach Produktionsstelle fand keine doppelten Befunde über Paketgrenzen. Ähnliche Befunde derselben Datei sind als gebündelt geführt.
- **Gestrichene Befunde** sind nicht falsch, sondern nach Zweck aussortiert; sie stehen mit Grund am Ende jedes Briefs und in `findings.json` (`state: dropped`).
- **Drei herabgestufte Befunde** (P4-F14, P4-F15, P4-F16) habe ich gegen den Wortlaut der Regel auf niedrig gesetzt, wie vom Prüfer angeregt: Kein Wert, Fehler oder Warnhinweis ist betroffen.

Stand der Bearbeitung und Wiedereinstieg: `rework/STATE.md`.
<!-- rework:end -->

## 1. Urteil

**Die Suite ist keine Coverage-Suite.** Von 3305 Testfunktionen erfüllen 63 (1,9 %) die Definition „führt Code aus, würde aber auch bei falschem Ergebnis bestehen“. 118 von 225 Dateien haben die Note A, 100 die Note B, 7 die Note C, keine die Note D. Die Erwartungswerte sind überwiegend von Hand hergeleitet oder stammen aus einem unabhängig geschriebenen Vergleichsmodell, Fehlermeldungen werden als Inhalt verglichen, und Aufrufzähler beweisen, was nicht gelaufen ist.

**Trotzdem sagt die Coverage-Zahl hier nichts mehr.** Die schnelle Stufe erreicht 99.1 % Zeilen- und 97.5 % Zweigabdeckung. Bei diesem Stand überleben 119 von 221 gezielten Mutationen des Produktivcodes alle Tests. Die Lücken liegen also dort, wo Coverage sie nicht zeigen kann: an Grenzwerten, bei Warnungen, im Cache-Schlüssel und im Optimierungskern.

Von 923 geprüften Anforderungen sind 694 (75 %) durch einen Test abgesichert, 147 teilweise und 82 gar nicht. Daraus ergeben sich 179 Befunde: 21 hoch, 79 mittel, 79 niedrig. 102 davon sind durch eine überlebende Mutation belegt, die übrigen durch Lesen.

## 2. Zahlen je Paket

| Paket | Bereich | Dateien | Testfunktionen | Note A / B / C | Anforderungen (ja / teilweise / nein) | Befunde (hoch / mittel / niedrig) | Mutationen überlebt |
|---|---|---:|---:|---|---|---|---|
| P1 | Geschlossene Formeln | 21 | 175 | 10 / 11 / 0 | 70 / 10 / 18 | 2 / 8 / 8 | 14 von 18 |
| P2 | Aerodynamik & Stabilität | 22 | 250 | 13 / 7 / 2 | 54 / 19 / 4 | 1 / 5 / 10 | 12 von 26 |
| P3 | Antrieb, Leistung, Holm | 17 | 233 | 5 / 11 / 1 | 91 / 11 / 12 | 3 / 6 / 8 | 11 von 18 |
| P4 | Engine, Graph, Cache, API | 30 | 569 | 21 / 9 / 0 | 95 / 10 / 11 | 3 / 11 / 6 | 12 von 19 |
| P5 | Validierung, Schema, Geometrie | 27 | 623 | 18 / 8 / 1 | 90 / 32 / 5 | 1 / 7 / 9 | 8 von 23 |
| P8 | Flotte, Golden Values, App | 22 | 153 | 8 / 12 / 2 | 45 / 13 / 7 | 0 / 11 / 7 | 4 von 19 |
| P6a | Solver: ASB / Opti | 26 | 316 | 10 / 16 / 0 | 70 / 17 / 5 | 3 / 8 / 9 | 15 von 20 |
| P6b | Solver: AVL / Prozess | 20 | 286 | 10 / 10 / 0 | 73 / 9 / 7 | 3 / 7 / 6 | 12 von 20 |
| P7a | Importer & Kanon-Skripte | 16 | 363 | 8 / 7 / 1 | 59 / 12 / 8 | 1 / 11 / 7 | 11 von 26 |
| P7b | Kanon-Modell & Bewertung | 24 | 337 | 15 / 9 / 0 | 47 / 14 / 5 | 4 / 5 / 9 | 20 von 32 |

Lesehilfe: „Mutationen überlebt“ zählt nur gewertete Proben; 8 äquivalente Mutanten sind verworfen. Die Proben wurden gezielt dort gesetzt, wo die Reviewer eine Lücke vermuteten. Die Quote ist deshalb kein Mutations-Score der Suite, sondern eine Trefferquote des Verdachts.

## 3. Was gut ist und so bleiben soll

- **Formeln mit Handwert.** Jede geschlossene Formel hat einen schnellen Test gegen eine von Hand gerechnete Zahl. Vorzeichen und Einheiten (Stabilitätsmaß, Leitwerkshebelarm, Grad gegen Radiant) werden durch Mutation getötet.
- **Antrieb gegen ein unabhängiges Modell.** Antriebskette, Teillastpunkt, Flugzeit und die sechs Leistungsformeln werden gegen ein getrennt geschriebenes Python-Modell und dessen Brute-Force-Suche geprüft, nicht gegen die Suche des Kerns.
- **Validierung auf beiden Seiten der Grenze.** 24 von 27 Dateien prüfen Fehlercode, Eingabepfad und Detail exakt, bei 0 gegen 1e-6, einem gegen zwei Schnitten, genau 45 Grad.
- **Importer Regel für Regel.** Jede Konsistenzregel aus ARCHITECTURE §8.6 hat einen Kanon, der genau diese Regel verletzt, und der vollständige Befundtext wird verglichen.
- **Prozess- und Abbruchverhalten.** Timeout, Abbruch, Gruppen-Kill, Aufräumen des Temp-Verzeichnisses und `tool_unavailable` sind mit echten Prozessen abgesichert.
- **Aero-Stufe mit unabhängiger Begründung.** Scharniermoment gegen die Theorie dünner Profile, Rollrate gegen ein kernfreies AVL-Skript, Auftriebsbilanz auf 1e-6.

Der statische Scan („Test hat nur schwache Asserts“) hat sich als unbrauchbar erwiesen: Er hielt 468 Tests für schwach, die Reviewer bestätigten 63. Er liest Enum-Identität (`is QuantityStatus.OK`) und Hilfsfunktionen wie `close()` falsch. Als Qualitätsmaß sollte er nicht eingeführt werden.

## 4. Die acht Muster hinter den Befunden

1. **Die schnellen Fakes verwerfen, was sie prüfen müssten.** Die `FakeOpti`-Klassen ignorieren `subject_to`, für Überziehen und Rollen auch `minimize`. Zielfunktion, Auftriebsbedingung und beide Rollgleichgewichte lassen sich ändern, ohne dass ein schneller Test rot wird (P6a-F04, F05, F10). Dasselbe bei AVL: Kein schneller Test liest die Zeile `Sref Cref Bref` einer geschriebenen Datei (P6b-F01).
2. **Die PR-CI sieht die Aero-Stufe nicht.** PR-Läufe schließen `aero` aus. Alles, was nur dort abgesichert ist, wird erst in der Nacht nach dem Merge gefunden. Es gibt kein schnelles Gegenstück zur Kette auf echter Flottengeometrie (P8-F04).
3. **Warnungen nach ADR 0020 werden selten als Inhalt geprüft.** `butterfly-approach` kann alle Vorbehalte seiner Referenzlösungen fallen lassen (P2-F01), `best_glide` die Klappenvorbehalte (P6a-F03), `level_polar` die Regime-Prüfung am schnellsten Punkt (P6a-F01). Ein Assert wie `len(regime) <= 2` besteht auch bei null Warnungen.
4. **Vorbedingungen sind einseitig getestet.** Geprüft wird meist genau ein verletzender Wert (0), nicht der negative, nicht der unendliche, und oft kein Fall, in dem die Bedingung gilt. Eine Bedingung, die jede Eingabe ablehnt, bleibt dann unbemerkt (P1-F01, P1-F02, P3-F02, P5-F01).
5. **Der Cache-Schlüssel ist nur als Funktion getestet, nicht in der Engine.** Die Welt und eine gelesene Polare können aus dem Schlüssel fallen. Das Intervall schrumpft dann still auf den Wert einer Welt (P4-F01, P4-F03). Ein Cache-Anspruch wird nach Abbruch nicht nachweislich freigegeben, der nächste Aufruf hinge (P4-F02).
6. **Einige Tests prüfen den Stellvertreter statt der Produktion.** `test_surface_properties.py` läuft gegen `tests/planform_stand_in.py`, `test_v_tail_neutral_point.py` weitgehend gegen `asb_fakes.py` (P5-F07, P2-F03, P1-F13). Die Namen versprechen mehr, als die Tests halten.
7. **Die Flotte ist Regression ohne einen einzigen Messwert.** 812 Zellen der Plan-Flotte sind aus der eigenen Ausgabe kopiert, 13 davon sind Fehler der Kategorie `internal` und gelten als Golden Value (Bug #1373). Golden Values werden von Hand eingefügt, ohne Recorder und ohne Differenzbericht (P8-F01, F02, F03, F06). Das ist dokumentiert („regression, not validation“), aber die Folge ist: Kein Test vergleicht den Kern mit der Wirklichkeit.
8. **Zwei Tests hängen am globalen Logger.** `test_engine.py` hat zwei Log-Tests, die scheitern, sobald der Root-Logger auf DEBUG steht. `app/main.py` setzt das beim Import. In einem gemeinsamen Lauf von App- und Kern-Tests sind sie rot (reproduziert, P4-F09, F10). Dazu kommen Tests mit festen Schlafzeiten und harten Zeitgrenzen (P4-F17).

## 5. Die 21 Befunde der Stufe „hoch“ im Review

> Überholt: Die gültige Liste der hohen Befunde steht im Nachtrag oben. Sechs der folgenden sind nicht mehr hoch, sechs andere sind hinzugekommen.

Jeder ist durch eine überlebende Mutation belegt. P4-F01, P5-F01 und P6b-F01 habe ich nach dem Review selbst in einer eingefrorenen Kopie nachgestellt: Mutation eingebaut, alle betroffenen Tests grün.

| ID | Stelle | Was unbemerkt falsch sein könnte |
|---|---|---|
| P1-F01 | `aero_kernel/formulas/minimum_drag_speed_closed_form.py:24` | The precondition parabola_defined of minimum-drag-speed-closed-form can be violated for every input (the probe quantity would never be produced) and the fast tier stays green: there is no 'held' case and no fast engine run of minimum-drag-speed-probe. |
| P1-F02 | `aero_kernel/formulas/sink_rate.py:29` | lift_coefficient_positive can reject every lift coefficient and no test fails: sink-rate has no 'held' case for C_L and is never requested through the engine in any tier, so a sink rate that is never computed would go unnoticed. |
| P2-F01 | `aero_kernel/formulas/butterfly_approach.py:152-157` | butterfly-approach can drop every caveat of its reference solves (Reynolds regime, drag messages of the landing stall and of the closing sample) and no test fails; ADR 0020 requires them declared. The early-return path (s_max = 0) forwards nothing testable either. |
| P3-F01 | `aero_kernel/formulas/endurance_and_range_optimum.py:116` | The canon constraint r_T(V) <= 1 of the optimum can be dropped: max-endurance/max-range are then returned at a speed the drive train cannot hold, instead of no_level_flight_speed or a declared full_throttle bound. |
| P3-F02 | `aero_kernel/formulas/motor_propeller_part_load.py:300` | A negative battery power (reachable with a table whose C_P is negative at the part-load point) would give a negative flight time and range instead of non_positive_battery_power. |
| P3-F03 | `aero_kernel/spar_capacity.py:239-242` | The axis origin of a partial-extent spar (root rib of ITS segment; offset in normal mode, absolute in standard mode) is unproven: a spar in an outboard segment could be placed from y = 0 and reported present/absent at the wrong stations. (Module is unreachable until gh-1429, so no user value is wrong today.) |
| P4-F01 | `aero_kernel/engine.py:568` | The engine can drop the world assignment from the node cache key without any test failing. With a cache, all worlds of a node whose worlds share a tool then share one entry: the interval collapses to the first world's value (observed under the mutation: {'unc=alpha': 10.0, 'unc=beta': 10.0, 'unc=gamma': 10.0} instead of 10/20/30) and is served as such on later calls. |
| P4-F02 | `aero_kernel/engine.py:588-595` | If the engine stops releasing a cache claim when a node run is cancelled or the time budget expires, every later call on the same CachedKernel that needs that key waits forever (observed under the mutation: the second call still hangs after 3 s, after a timed-out call and after a cancelled one). No test notices. |
| P4-F03 | `aero_kernel/engine.py:193-197` | A polar that a node reads can be left out of that node's cache key (replaced by a constant) without any test failing: a reader of a changed polar would then be served the value computed from the old polar. |
| P5-F01 | `aero_kernel/validate.py:886` | The conflicting_mass notice can disappear for every what-if at a mass above the geometry's total_mass_kg without a test failing: all tests pass a mass below the stored one. |
| P6a-F01 | `aero_kernel/solvers/opti.py:2299` | level_polar could check the regime at the slowest point only: a Mach or Re-above-band warning of the fastest point (up to the `error` mach_beyond_validity) would be dropped and no test fails. |
| P6a-F02 | `aero_kernel/solvers/opti.py:2397` | sweep could accept a deflected flap (flaps_supported=True) and return the polar of the flapped airplane without any caveat, although ch. 8.8 says sweep refuses a flap because it returns no warnings. |
| P6a-F03 | `aero_kernel/solvers/opti.py:2238` | best_glide could drop the flap caveats (hinge_line_averaged, control_surface_fit_range_unknown) of a flapped configuration: an undeclared model substitution (ADR 0020). The same declaration is untested for min_sink (opti.py:2442) and level_flight_point (opti.py:2367). |
| P6b-F01 | `aero_kernel/solvers/avl.py:538` | The adapter can hand the wrong reference to the writer (Cref = span, or Bref = mean chord) and every fast test passes. The hinge moment is q*S_ref*c_ref*Chinge 'with the S_ref, c_ref the AVL file carries', and Clp / p'b/2V and the VM normalisation use the file's Bref, so the fast tier would ship moments wrong by b/c and roll rates wrong by c/b. |
| P6b-F03 | `aero_kernel/solvers/avl_hinge.py:265` | On a horizontal tail or fin of the hinge-moment mesh the stations are unchecked: the device ends need not be stations (a part-span elevator or rudder then controls the wrong strips or, with one bounding section lacking the CONTROL, none: AVL drives a strip only if both sections declare it), the tail need not take the wing's stations, and slivers next to a break need not be dropped. |
| P6b-F05 | `aero_kernel/solver_bodies.py:204` | The section of a body at an inserted station can ignore the taper (half-width taken from the lower neighbour instead of interpolated) without a failure: every parent and canopy of the tests has constant a, b, n and centre along x. A real fuselage tapers, so the merged body's width at every canopy station, its area for the AVL body radius and its wetted area would be wrong. |
| P7a-F01 | `aero_kernel/importer/pipeline.py:45` | The pipeline may ignore the formula entry's 'status:' completely (every formula reported as draft, no formula ever fully approved in IMPORT_REPORT.md) and no test fails. Stage 1 of the two-stage approval is never tested from the canon document to the report. |
| P7b-F01 | `aero_kernel/evaluation/evaluator.py:199` | A quantity the kernel returned with status error or skipped can be reported as not_applicable ('The kernel found it not applicable: no reason given') instead of not_available, and no test fails. The consumer then reads a failed computation as 'the rule does not apply to this aircraft'. |
| P7b-F02 | `aero_kernel/evaluation/rules.py:28` | The rule-table types can lose extra='forbid' and frozen without a failing test. A mistyped key in drela.yaml (e.g. `abov_severity: caution`, `min_inclusiv: false`) would then be dropped silently and the rule would judge with the default (bad, inclusive). |
| P7b-F03 | `aero_kernel/evaluation/evaluator.py:294` | The verdict text of a one-sided band can state the band in the wrong direction ('≥ 15' for the limit ≤ 15 deg, '≤ 5' for B > 5) and no test fails. Turn sideslip and all three spiral rules of the shipped table have one-sided bands, and the text is the LLM-facing contract. |
| P7b-F04 | `aero_kernel/evaluation/rule_table.json` | Three decided properties of the shipped rule table can change without a failing fast test: the band of the two circling rules over spiral-parameter-mp (5 -> 4), the severity of spiral-stability-circling-aileron below the band (caution -> bad, maintainer decision 2026-10-26), and the level edges of turn-sideslip (5 -> 6 deg). |

## 6. Was vor der Arbeit entschieden werden muss

> Die sieben Fragen gelten weiter. Ergänzungen und vier neue Fragen stehen im Nachtrag oben; dort steht auch der Stand der Produktionsfehler (Tickets #1434 bis #1436).

Diese Punkte sind keine Testaufgaben, solange die Entscheidung fehlt. Die Arbeitspakete lassen sie aus und melden sie als offen.

| Befund | Frage | Meine Empfehlung |
|---|---|---|
| P4-F07 | ARCHITECTURE §8.5 sagt, `has_vertical_tail` folgt aus `surface_type`. Der Code nutzt noch die vorläufige Grundrissregel, und rund 17 Tests halten sie fest. Ein als `vertical_tail` typisierter Mittelfin ergibt heute `False`. | Spezifikation gilt (Memory: Geometrie ist typisiert, nie abgeleitet). Bug-Ticket, Code und die betroffenen Tests anpassen. |
| P4-F08 | §8.5, §8.14 und Q33 verlangen eine INFO-Zeile „optional input absent“. Der Code schreibt sie nirgends, ein Test hält ihr Fehlen fest. | Spezifikation gilt, Zeile bauen. Alternative: Satz aus drei Stellen der Architektur streichen. |
| P5-F08 | „Flaperons XOR Querruder + Klappen“ ist entschieden (D9/D10), hat aber weder Regel noch Test. Ein Flügel mit allen dreien validiert ohne Meldung. | Regel in `rules.yaml` aufnehmen, dann Test. Einfache Alternative: Mischung als zulässig erklären und das mit einem Test festhalten. |
| P7a-F04 | §8.9 Stufe 4 (Differenz zum eingecheckten Modell, Markierung brechender Änderungen) ist nicht gebaut. | Aus §8.9 streichen und auf den Traceability-Test Q11 verweisen, solange kein Bedarf besteht (ADR 0021). |
| P6b-F11 | Eine abgeschnittene AVL-Tabelle kommt als kürzere Kurve zurück statt als Fehler. Woran wird die Vollständigkeit gemessen: an `# Spanwise = N` oder an `N_SPAN`? | Gegen `# Spanwise = N` der Ausgabe zählen, Abweichung ist ein Fehler. |
| P5-F06 | `non_positive_exponent` wird von `validate.py` gemeldet, steht aber in keiner Kanon-Regel. | In die Regel `positive-lengths` aufnehmen oder eigene Regel (Memory: jede Eingabeprüfung steht im Kanon). |
| P8-F13 | `test_canon_stall_speed_integration.py` ist laut Docstring „expected to fail“ (gh-1142), hat kein `xfail` und läuft nur nachts gegen die Alt-Rechnung der App. | Einmal ausführen und das Ergebnis in gh-1142 festhalten. Nicht löschen, nicht abschwächen. |

### Produktionsfehler, die das Review nebenbei gefunden hat

Für diese würde ein neuer Test heute rot. Nach Iron Law 5 braucht jeder ein Bug-Ticket vor der Korrektur. Stand vom 21. November: alle nachgestellt, drei Tickets angelegt, zwei als Frage an den Maintainer (Nachtrag oben).

| Befund | Fehler | Beleg |
|---|---|---|
| P8-F08 | Eine unerwartete Ausnahme aus dem Kern verlässt `POST /canon/compute` als Klartext-500 statt in der einen Fehlerhülle (ADR 0019). | in der Kopie gemessen |
| P3-F04 | `endurance-and-range-optimum` kehrt bei Überziehgeschwindigkeit 0 nicht zurück (`v *= ratio` bleibt 0). Der Eintrag hat keine Vorbedingung `stall_speed_usable`. | nach 15 s abgebrochen |
| P1-F11 | Fluggeschwindigkeit 0 ist zulässige Eingabe und endet bei `lift-coefficient` als `internal` (ZeroDivisionError) statt als erklärter Fehler. | `evaluate()` in der Kopie |
| P7a-F05 | `taxonomy.yaml` wird als einzige Kanon-Datei nicht auf `# ESCALATED:` und YAML-1.1-Wahrheitswerte geprüft. | unveränderter Code |
| P7b-F08 | Eine `@relation` für einen unbekannten Slug meldet `check_traceability` nicht. | `check_traceability` ausgeführt |
| P4-F09 / F10 | Zwei Log-Tests in `test_engine.py` sind vom Root-Logger abhängig (Testfehler, kein Produktfehler). | `--log-level=DEBUG`: 2 failed |

## 7. Arbeitspakete für Subagents

Zwölf Pakete. Jedes hat einen eigenen Brief unter `wp/`, der ohne dieses Schreiben und ohne das Review verständlich ist: Befund, Stelle, Beleg, Ergebnis der Nachprüfung, der zu schreibende Test mit Eingaben, Erwartungswert und Herleitung, eine Korrektur, wo die Nachprüfung die Empfehlung berichtigt hat, und die Abnahme-Mutation als Patch. Die Tabelle zeigt den Stand nach der Nachprüfung.

| Welle | Paket | Inhalt | zu bearbeiten (hoch / mittel / niedrig) | ausgeschieden | Brief |
|---:|---|---|---|---|---|
| 1 | WP-P4a | Cache-Schlüssel, Engine-Provenienz, Regelgrenzen | 7 (3 / 3 / 1) | 2 wartet auf Entscheidung, 3 gestrichen, 1 widerlegt | `wp/WP-P4a.md` |
| 1 | WP-P7b | Bewertung (Evaluator, Regeltabelle, Drela-Bänder) | 12 (4 / 5 / 3) | 6 gestrichen, 1 Produktionsfehler | `wp/WP-P7b.md` |
| 1 | WP-P6a | Opti-Adapter: Fakes, die Zielfunktion und Nebenbedingungen aufzeichnen | 16 (3 / 7 / 6) | 3 gestrichen, 1 widerlegt | `wp/WP-P6a.md` |
| 1 | WP-P6b | AVL: Referenzgrößen, Leitwerks-Stationen, Rumpfkörper | 14 (1 / 8 / 5) | 1 wartet auf Entscheidung, 1 gestrichen | `wp/WP-P6b.md` |
| 1 | WP-P3 | Antrieb, Leistung, Flugzeit, Holm | 14 (4 / 6 / 4) | 3 gestrichen, 1 Produktionsfehler | `wp/WP-P3.md` |
| 2 | WP-P1 | Geschlossene Formeln: Vorbedingungen beidseitig | 13 (1 / 7 / 5) | 2 gestrichen, 1 Produktionsfehler | `wp/WP-P1.md` |
| 2 | WP-P2 | Aerodynamik- und Stabilitätsformeln | 14 (2 / 2 / 10) | 3 gestrichen | `wp/WP-P2.md` |
| 2 | WP-P5 | Validierung, Geometrie, Geräte | 13 (2 / 6 / 5) | 2 wartet auf Entscheidung, 2 gestrichen, 2 widerlegt | `wp/WP-P5.md` |
| 2 | WP-P7a | Importer, check_canon, Navigator-Build | 13 (0 / 9 / 4) | 1 wartet auf Entscheidung, 3 gestrichen, 1 Produktionsfehler | `wp/WP-P7a.md` |
| 3 | WP-P8a | Referenzflotte: Relationen, schnelle Kette, Golden-Recorder | 8 (0 / 5 / 3) | 3 gestrichen | `wp/WP-P8a.md` |
| 3 | WP-P8b | App-Anbindung: Fehlerhülle und Eingabeprüfung über den Endpunkt | 5 (1 / 1 / 3) | 1 wartet auf Entscheidung, 1 Produktionsfehler | `wp/WP-P8b.md` |
| 3 | WP-P4b | Test-Isolation und zeitabhängige Tests | 5 (0 / 0 / 5) | — | `wp/WP-P4b.md` |

**Schnitt.** Jeder Befund gehört dem Paket, dem seine Testdatei gehört. Die Pakete ändern deshalb keine gemeinsamen Testdateien und können parallel in eigenen Worktrees laufen. Zwei Stellen überschneiden sich im Produktivcode, falls ein Test einen Fehler aufdeckt: `solver_bodies.py` (WP-P5 und WP-P6b) und `validate.py` / `rules.py` (WP-P5 und WP-P4a). Diese Paare nacheinander mergen.

**Reihenfolge.** Welle 1 enthält 15 der 21 hohen Befunde und die Stellen, an denen ein falscher Wert den Anwender erreicht (Cache, Bewertung, Optimierung, AVL-Referenzen, Flugzeit). Welle 2 schließt Vorbedingungen und Warnungen. Welle 3 ist Infrastruktur: Flotte, App-Hülle, Test-Isolation. WP-P4b ist klein und sollte trotzdem früh laufen, weil es einen roten gemeinsamen Lauf beseitigt.

**Aufwand.** Die Pakete enthalten 5 bis 16 zu bearbeitende Befunde. Die meisten Tests sind kurz, weil Fixtures und Builder vorhanden sind. WP-P6a und WP-P8a sind größer: Dort entsteht zuerst ein Werkzeug (aufzeichnender Fake, Golden-Recorder), dann die Tests.

### Regeln für alle Arbeitspakete

Diese Regeln gehören in jeden Dispatch-Prompt.

1. **Arbeitsort.** Eigener Worktree, Branch `test/gh-<N>-<slug>`. Nie im Haupt-Checkout arbeiten, nie `cd` mit git verketten (`git -C <pfad>` verwenden). Vor dem Start: `mkdir -p <worktree>/tmp`.
2. **Nur Tests.** Geändert werden Testdateien und Test-Helfer. Produktivcode wird nicht angefasst.
3. **Ein neuer Test, der auf dem heutigen Code rot ist, hat einen Fehler gefunden.** Dann: Test nicht abschwächen, nicht mit `skip` oder `xfail` versehen, nicht löschen. Den Test aus dem Commit herausnehmen, im Bericht mit Befund-ID, Eingabe und beobachtetem Verhalten melden. Der Maintainer legt das Bug-Ticket an.
4. **Abnahme durch Mutation.** Zu jedem Befund mit Abnahme-Mutation: den genannten Patch in einer Wegwerf-Kopie (`git worktree add` oder `git archive` des eigenen Commits im Scratchpad) mit `git apply <Audit-Ordner>/rework/patches/<WP>/<Befund>.patch` einspielen, die betroffenen schnellen Testdateien laufen lassen, mindestens ein schneller Test muss rot werden. Lässt sich der Patch nicht mehr einspielen, weil sich der Produktivcode geändert hat, die im Brief beschriebene Änderung von Hand nachbauen. Kopie danach verwerfen. Nie im Arbeits-Worktree mutieren.
5. **Herleitung im Test.** Jeder neue Erwartungswert steht mit seiner Rechnung oder Quelle im Test (Kommentar oder Docstring). Kein Wert wird aus der Ausgabe kopiert. Kein Erwartungswert wird mit demselben Ausdruck berechnet wie im Produktivcode.
6. **Grenzwerte beidseitig.** Zu jeder Bedingung: ein Fall, in dem sie gilt, der genaue Grenzwert, ein Fall jenseits davon. Bei „positiv“: 0, negativ, unendlich.
7. **Warnungen als Inhalt.** Code, Schweregrad und betroffene Größe einer Warnung werden verglichen, nie nur die Anzahl.
8. **Stufe.** Neue Tests gehören in die schnelle Stufe (ohne Marker, Solver über die vorhandenen Fakes), außer der Brief nennt ausdrücklich `aero`. Aero-Tests einzeln und nacheinander ausführen, nie parallel.
9. **Sonar und Stil.** Ein auslösender Aufruf je `pytest.raises`, Funktionen mit kognitiver Komplexität ≤ 15, Typannotationen auch in Test-Helfern, Englisch (ADR 0029). Neue Test-Helfer müssen von der schnellen Stufe ausgeführt werden (80-%-Gate auf neuem Code).
10. **Definition of Done, ohne Ausnahme im Vordergrund ausgeführt:**
    `poetry run ruff check aero_kernel && poetry run ruff format --check aero_kernel && poetry run pyright aero_kernel`,
    `poetry run pytest aero_kernel/tests -m "not aero and not slow" -p no:cacheprovider` (für WP-P8b und WP-P7a zusätzlich die betroffenen Dateien unter `app/tests` bzw. `scripts/tests`),
    dann Commit `test(gh-<N>): …` und `git push github <branch>`.
11. **Bericht.** Zeile 1: Ergebnis mit Beweis (Commit-SHA, Zahl neuer Tests, Zahl getöteter Abnahme-Mutationen von wie vielen). Dann: rote Tests nach Regel 3, verweigerte Befehle. Letzte Zeile: nächster Schritt.

### Vorlage für den Dispatch

```text
You implement work package <WP-ID> of the canon test review (frozen at 72c4b5c6).

Read, whole and in this order:
1. _reversa_sdd/audit-2026-11-20-canon-tests/README.md, section "Regeln für alle Arbeitspakete" (binding)
2. _reversa_sdd/audit-2026-11-20-canon-tests/wp/<WP-ID>.md (your findings, one section each)
3. aero_kernel/CLAUDE.md

GitHub issue: #<N>. Worktree: <path>, branch test/gh-<N>-<slug>.
Work through the findings that have their own section, in the order of the brief (high first). Where a finding has a Correction line, it overrides the text under Test to write. The table at the end of the brief lists findings that are not yours.
Tests only. A new test that is red on today's code is a discovered bug: follow rule 3.
Finish with the full definition of done (rule 10) in the foreground and report as rule 11 says.
```

Modell: Sonnet für die Umsetzung (Memory „Implementer subagents on Sonnet“). Für WP-P6a und WP-P8a das stärkere Modell, weil dort ein Werkzeug entworfen wird. Klassische Subagents ohne Namen, damit der Abschlussbericht sicher ankommt.

## 8. Empfehlungen jenseits der einzelnen Tests

1. **Aufzeichnende Fakes als Standard.** `FakeOpti` soll Zielfunktion und Nebenbedingungen aufzeichnen, der AVL-Fake die geschriebene Datei. Die Tests vergleichen dann, was an den Solver ging. Das schließt Muster 1 strukturell und ist der Kern von WP-P6a und WP-P6b.
2. **Schnelles Gegenstück zur Kette.** Fünf Flugzeuge (konventionell, nur Seitenruder, V-Leitwerk, Klappen, Nurflügel) laufen mit Fakes durch die ganze Kette und prüfen Status, Welten und Anwendungen. Damit sieht die PR-CI eine gebrochene Bindung (WP-P8a).
3. **Register für Fehler als Golden Value.** Jeder Fehlerstatus in den Golden Values braucht eine Ticketnummer. Ein neuer `internal` kann dann nicht mehr still aufgezeichnet werden (WP-P8a, P8-F02).
4. **Golden-Recorder mit Differenzbericht.** Ein Skript rechnet die Flotte, schreibt die Werte als JSON und einen Bericht alt/neu je Flugzeug und Größe. Das Review einer Neuaufzeichnung liest dann den Bericht statt 800 Zahlen im Diff.
5. **Mutationstest als nächtliches Signal, nicht als Gate.** Für `aero_kernel/formulas/`, `evaluation/`, `cache.py` und `rules.py` lohnt ein Mutationslauf (z. B. `mutmut`) auf einer eingefrorenen Kopie. Die Zahl überlebender Mutanten je Modul ist das Maß, das die Coverage-Zahl hier ersetzen kann. Als Gate ist es zu langsam und zu laut.
6. **Messwerte in die Flotte.** `reference/avistar_elite/MEASUREMENTS.md` liegt vor und wird von keinem Test benutzt. Schon zwei oder drei veröffentlichte Werte mit ehrlicher Toleranz wären die erste Validierung statt Regression. Das ist eine Entscheidung über Aufwand und gehört in ein eigenes Ticket.
7. **Root-Logger in den Kern-Tests festlegen.** Ein `conftest`-Fixture, das den Logger `aero_kernel` isoliert, oder Log-Tests, die nur Datensätze mit `call_id` auswerten. Das behebt P4-F09 und F10 an der Ursache.

## 9. Grenzen dieses Reviews

- **Die Aero-Stufe wurde nicht ausgeführt.** Ein Lauf der 733 Aero-Fälle wurde nach rund 50 Minuten bei 15 bestandenen Tests abgebrochen. Aero-Dateien sind deshalb nur gelesen, ihre Befunde tragen den Status `READ_ONLY`. Ergebnis und Dauer der Aero-Stufe fehlen im Dashboard.
- **Schnelle Stufe:** 5019 bestanden, 2 rot (die beiden Log-Tests aus Muster 8, nur im gemeinsamen Lauf mit den App-Tests).
- **Die Mutationsproben sind gezielt, nicht flächendeckend.** 229 Proben auf rund 10 700 Anweisungen. Wo keine Probe gesetzt wurde, ist nichts bewiesen, weder Lücke noch Dichtheit.
- **Nachtrag 21. November:** Die Befunde sind inzwischen unabhängig nachgeprüft, und 19 Mutationen liefen gegen gezielte Aero-Tests; siehe Nachtrag oben. Die folgenden Punkte beschreiben den Stand des Reviews.
- **Die Reviewer irren auch.** Ich habe drei von 21 hohen Befunden und die Log-Abhängigkeit selbst nachgestellt, alle vier bestätigt. Die übrigen Befunde sind nicht von mir nachgeprüft. Regel 4 fängt das auf: Eine Abnahme-Mutation, die heute doch getötet wird, entlarvt einen falschen Befund sofort.
- **17 der 44 Kanon-Regeln** gehören zu Solver-Adaptern und wurden nur über ihr Code-Literal gefunden, ihre Asserts nicht einzeln bewertet.
- **Frontend-Tests** des Kanon-Navigators (`frontend/__tests__/canonNavigator*.ts`) waren nicht Teil des Reviews.

## 10. Dateien dieses Audits

| Datei | Inhalt |
|---|---|
| `README.md` | dieses Schreiben |
| `wp/WP-*.md` | zwölf Arbeitspaket-Briefe für Subagents |
| `findings.json` | alle 179 Befunde mit Beleg, empfohlenem Test und dem Ergebnis der Nachprüfung (`state`, `severity`, `verdict`, `tier_gap`, Korrekturen) |
| `rework/STATE.md` | Logbuch der Nachprüfung mit Wiedereinstieg |
| `rework/verify/`, `rework/patches/` | Urteile der zwölf Prüfer je Paket und die Abnahme-Mutationen als Patch |
| `rework/defects/` | Skripte und Ausgaben zu den fünf Produktionsfehlern |
| `rework/handvalues.json`, `rework/aero/` | nachgerechnete Handwerte der hohen Befunde; Liste und Ergebnisse der Aero-Gegenprobe |
| `rework/build.py`, `rework/addendum.py` | erzeugen `findings.json`, die Briefe und den Nachtrag aus den Prüfergebnissen |
| `mutation_probes.json` | alle 229 Mutationsproben mit Ergebnis |
| `requirements_open.json` | die 229 Anforderungen, die teilweise oder nicht abgesichert sind |

Dashboard mit Drilldown (Paket → Datei → Test, Befunde, Anforderungen, Mutationen, Coverage): https://claude.ai/artifact/M7Q9tmDTkgPCQyG3ub1BM9
