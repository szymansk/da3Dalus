# GH-Issue-Audit gegen die Spezifikation — 2026-08-16

Alle **82 offenen Issues** gegen `_reversa_sdd/` geprüft, aufgefächert auf acht Agenten,
je Ticket ein Verdikt mit Spec-Zitat und Konfidenzmarker. Nichts ausgelassen.

**Dies ist eine Entscheidungsvorlage, keine Entscheidung.** Kein Issue wurde geändert,
kommentiert, gelabelt oder geschlossen.

| Verdikt | Anzahl | Bedeutung |
|---|---|---|
| **BESTÄTIGT** | 29 | Spec deckt das Gebiet, Ticket ist konsistent |
| **KOLLISION** | 28 | widerspricht einer Spec-Regel und könnte trotzdem recht haben → Maintainer |
| **NICHT-SPEZIFIZIERT** | 13 | keine Einheit deckt das ab — gültiges Ergebnis |
| **ÜBERHOLT** | 12 | eine protokollierte Entscheidung nimmt dem Ticket den Zweck |

---

## 1. Überholt — Kandidaten zum Schließen (12)

| # | Grund | Beleg |
|---|---|---|
| **775, 776, 779, 780** | gebaut in PR #782, im Code verifiziert | `avl-integration/control-surface-naming/requirements.md` BR-9/BR-11/BR-CSN1 🟢 |
| **1081** | gebaut (`carbon_tube_import.py`), inkl. nachgeschärfter AC | `powertrain/cots-powertrain-components/` 🟢 |
| **151** | Versionierung ist gebaut (Snapshot, Fork, Branch, Lineage) | ADR 0006 🟢 |
| **901** | Epic geliefert; Sub-Issues #903/904/905/907 geschlossen | ADR 0006 🟢 |
| **202** | Q-CG-4 löscht das ganze Tessellations-Subsystem | `questions.md#Q-CG-4` 🟢 |
| **660** | Phasen A–C via gh-674 erledigt, Phase D als „Not chosen" verworfen | ADR 0003 🟢 |
| **792** | Prämisse durch gh-855/857 entfallen (`spanwise_resolution=1` + Remesh) | `aero-analysis/requirements.md#BR-AA3` 🟢 |
| **152** | Mehrbenutzer-Server ist per ADR ausdrücklich out of scope | ADR 0024 🟢 |
| **38** | Scraping-Methode namentlich verworfen | ADR 0014 §Rejected 🟢 |
| **198** | Analyse ist erledigt; was fehlt, ist die Umsetzung | `expert-consensus-powertrain.md` 🟢 |

**#202 besser umschreiben statt schließen:** Q-CG-4 enthält eine vollständige, protokollierte,
aber ungebaute Löschliste — und dafür existiert kein Ticket. Siehe Abschnitt 3.

> **Zwei Präzisierungen zu #202, unabhängig von zwei Agenten bestätigt.**
>
> **① Die Löschung ist eine Produktentscheidung, keine technische Kapitulation.** Der
> Code-Lookup ergab das Gegenteil der TODO-Begründung: *„Both blockers named in the TODO
> are already solved in the same repo … the wiring is roughly six lines plus one
> decision"*. Belegt wurde die Löschung mit **null Consumern** für `useTessellation.ts`
> (205 Z.), `usePreviewState.ts` (207 Z.) und `ViewerPanel.tsx`. Wer beim Schließen
> „zu aufwendig" notiert, protokolliert den falschen Grund.
>
> **② Beim Löschticket muss der Nicht-lösch-Teil mitreisen, sonst reißt der Live-3D-Pfad
> mit.** Ausdrücklich **nicht** gelöscht: `construction_plan_service._tessellate_shapes`
> und die `ocp_tessellate`-Nutzung, die `ExecutionResultDialog` speist (der lebende Pfad),
> sowie der CAD-**Export** (`cad_service`) samt Zip-Download — ein anderes Subsystem.
>
> Miterledigt („rendered moot"): `Q-CG-5`, `Q-FW-5`, `Q-CG-3`, der
> `"manual"`-geometry-hash-Platzhalter und der Cache-Race.

**#38 und #198 ersetzen, nicht ersatzlos schließen:** bei #38 bleibt die Datenlücke Servo /
Receiver / Flight-Controller; bei #198 bleiben Q-PT-1/2/3 als Umsetzungstickets.

### Der Grund, warum sechs davon offen hingen

GitHub wertet in `Closes #a, #b, #c` nur die **erste** Referenz aus — jede Nummer braucht
ihr eigenes Schlüsselwort.

| PR | im Text | verlinkt | hing offen |
|---|---|---|---|
| #782 | `Closes #773, #775, #776, #779, #780` | nur #773 | #775, #776, #779, #780 |
| #1086 | `Closes #1075, #1080, #1081` | nur #1075 | #1080, #1081 |

Prozessfehler, kein Backlog-Problem — und er erklärt einen Teil der 66 seit über
60 Tagen unberührten Issues.

---

## 2. Kollisionen — Maintainer-Entscheidung nötig (28)

Nach Muster gruppiert. In jeder Gruppe kann das **Ticket** recht haben; die Spec ist
nicht automatisch im Recht.

### 2.1 Zweiter Produzent einer nutzersichtbaren Größe — ADR 0022 (7)

Das häufigste Muster. Jedes Mal soll etwas neu berechnet werden, das bereits genau
einen Besitzer hat.

| # | rechnet neu, was schon existiert |
|---|---|
| 61, 62 | Static Margin / Stabilitätstests im Frontend-ViewModel — `stability_service.get_stability_summary` ist alleinige Autorität; BR-FE36 🟢 „the frontend never computes a displayed number" |
| ~~781~~ | **✅ erledigt 2026-08-16 — und das Audit lag hier falsch.** Siehe unten. |
| 616 | eigener `P_required` + eigene V-n-Kurve — BR-PT30 🟢 „one drag polar in the codebase" |
| 675 | Triangle-Check meldet Divergenz statt einen Produzenten zu bestimmen — genau die von ADR 0022 §Rejected verworfene Option |
| 676 | zweite V_H-Bandtabelle — `/tail-sizing` klassifiziert bereits klassenabhängig |
| 1077 | zweiter Vollzustandsblock statt des per Q-CO-14 entschiedenen Änderungsdatensatzes |

### 2.2 Eingefrorene Schicht `cad_designer/` — ADR 0002 (4)

| # | Konflikt |
|---|---|
| 762 | neues Feld auf `WingConfiguration` + Helfer in `Airfoil.py` — eingefroren. **Aber:** ADR 0002 begründet den Freeze mit „silent wrongness", und ein bei 60° Dihedral 50 % zu dünnes Profil ist genau das → Präzedenzfall gh-934 |
| 941 | Fix in `VaseModeWingCreator.py`; ADR 0002 friert wörtlich nur `aircraft_topology/` ein, drei Unit-Dokumente führen die Datei aber als read-only — **die Freeze-Grenze widerspricht sich selbst** |
| 57 | benutzergeschriebener CadQuery-Code als zweiter Erweiterungspfad neben „neuer Creator" |
| 283 | Klausel „Bugs found → separate bug ticket" gegen „Defekte werden dokumentiert, nicht behoben" |

### 2.3 Bezug auf stillgelegte Subsysteme (3)

| # | verweist auf |
|---|---|
| 696 | skaliert `WeightItem`-Positionen und -Massen — per Q-MB-1 stillgelegt |
| 746 | E2E-Fixture „weight items exist with total CG at 0.30m" (`operating-points.feature:32`) |
| 278 | drei Coverage-Ziele sind Code, den die Spec löscht (`tessellation_service`, `design_version_service`, `weight_items_service`) — Tests darauf sind verlorene Arbeit |

### 2.4 Falsche Prämisse — das Ticket beschreibt den Code nicht (6)

Die gefährlichste Klasse: äußerlich plausibel, sachlich gegen eine erfundene Codebasis
geschrieben.

| # | Behauptung | gemessen |
|---|---|---|
| **654** | „Existierender ComponentImporterCreator hat schon Pattern" | `is_editable` und `frozen_components`: **0 Fundstellen**; keines der vier benannten Argumente existiert |
| **791** | Importer verursacht `ΔC_L0 ≈ 0.43`, VSPAERO als Wahrheit | Q-VI-8: echter Anteil 0.10–0.17, ~2.5× überschätzt; VSPAERO überschießt stärker |
| **1080** | Holmplan nutzt beliebige OD/ID | Stock-Snapping läuft auf 100 % der Produktionspfade (Q-CP-5 🟢) |
| **1089** | Katalog hat kein kleines Rohr mehr | 11 spar-fähige Rohre ab 3,0 mm im Snapshot; es fehlt die **Test-Seed** |
| **586** | löscht `_pick_deflections` | Spec begründet den Empty-Dict-No-op ausdrücklich: „precisely so it cannot silently erase a fresh trim" |
| **673** | AeroBuildup liefert 30 Felder über 5 Achsen | `Cnr`/`Clr` nur im AVL-Pfad → liefe unbemerkt gegen ADR 0003 |

### 2.5 Spec muss zuerst nachgezogen werden (8)

#199 (ADR 0014/0013), #561 (feste Achsenzahl RF-12 + ADR 0006), #669 (dritte Warnform
neben ADR 0020), #745 (deutsche Seed-Labels vs. Q-CC-5), #797 (Wartung per CLI, nicht
REST — Q-AF-6/ADR 0024), #814 (Prämisse vom Maintainer korrigiert: Konsument ist der
Creator, nicht der Download), #902 (Epic-Körper ist Stand 2026-06-07), #1079
(`n_max ≥ 6` gegen das Spec-Band 1,5–2 — geht über #1080 direkt in die Holmwandstärke).

---

## 3. Entschieden, nicht gebaut — jetzt getickt ✅

Die Gegenrichtung — der Rückstand, den das Interview erzeugt hat. Jede Zeile gegen den
Code geprüft. **Am 2026-08-16 in 27 Tickets überführt (#1096–#1122)**, und jede
zugehörige Entscheidung in `questions.md` trägt jetzt ihre `**Soll → #N**`-Marke. Damit
ist die Verriegelung aus [`MARKERS.md`](MARKERS.md) zum ersten Mal geschlossen.

### Ticketzuordnung

| Ticket | Entscheidung | |
|---|---|---|
| **#1096** | `Q-WD-8` ② Hinge-Clearance-Guard | 🐞 **sicherheitsrelevant** |
| **#1097** | `Q-MC-1` MCP-Transaktionsgrenze | 🐞 ~40 Write-Tools schreiben nichts |
| **#1098** | `Q-VS-1` Immutability-Guard | 🐞 **ADR 0007 ruht darauf** |
| **#1099** | `Q-AA-1` zweiter `cd0`-Produzent | 🐞 |
| #1100 | `Q-CG-4` Tessellations-Subsystem löschen | groß |
| #1101 | `Q-MB-1` Component-Tree als alleinige Massenautorität | groß |
| #1102 | `Q-CC-3` eine Fehler-Hülle | groß |
| #1103 | `Q-CC-10` typisierter Computation-Context | groß |
| #1104 | `Q-MB-7` `total_mass_kg` als abgeleitete Sicht | |
| #1105 | `Q-CC-4` eine `Settings`-Klasse, eine Version | Vorbedingung für #1095 |
| #1106 | `Q-WD-8` ① rechteckige/gekappte Holme rechnen | |
| #1107 | `Q-PT-13` ①–④ COTS-Lebenszyklus | |
| #1108 | `Q-PT-3` Kv/Propeller aus der Polardatenbank | |
| #1109 | `Q-PT-1` ESC auf Peak-Strom bei Sag-Spannung | |
| #1110 | `Q-PT-2` Propellermasse in `total_mass` | |
| #1111 | `Q-FW-1`/`R2-10` CORS-Allowlist | |
| #1112 | `Q-AV-3`/`Q-AV-4` AVL-Replay-Artefakt löschen | Spec sagt „gelöscht", Code existiert |
| #1113 | `Q-VS-3` fünf tote `design-versions`-Routen | |
| #1114 | `Q-VI-2` `validate_geometry` verdrahten | |
| #1115 | `Q-CO-1` Copilot-Audit-Trail | |
| #1116 | `Q-MS-2`/`Q-MS-13` ④ ein Landedistanz-Produzent | |
| #1117 | `Q-PT-12` Prop-Polar-Spalten + Skip-Report | |
| #1118 | `Q-CC-5` deutsche UI-Strings übersetzen | **blockiert #745** |
| #1119 | `Q-CT-5` Guard für unimplementierte Hinge-Typen | |
| #1120 | `Q-CC-16` zwei importlose Dateien löschen | trivial |
| #1121 | `Q-FW-8`/`R2-13` `react-plotly.js` entfernen | trivial |
| #1122 | Servo-/Receiver-/FC-Katalog | aus der Schließung von #38; **keine `Q-id`** |

**#1122 trägt bewusst keine Soll-Marke.** Es ist eine Datenlücke, keine protokollierte
Entscheidung — die Regel gilt für Entscheidungen, nicht für alles.

### Die ursprüngliche Aufstellung

Nach Umfang, größtes zuerst.

| Entscheidung | Was der Code heute tut | Umfang |
|---|---|---|
| `Q-CG-4` Tessellations-Subsystem löschen | alle 3 Services, Tabelle+Migration, 2 Endpunkte, ~10 Call-Sites, 3 FE-Dateien vorhanden | groß |
| `Q-MB-1` Component-Tree als alleinige Massenautorität | 5 Consumer-Services lesen weiter `WeightItemModel` | groß |
| `Q-CC-3` eine Fehler-Hülle | `_raise_http` in ≥20 Endpoint-Modulen | groß |
| `Q-CC-10` typisierter Computation-Context | kein `context_version`; RC-Fallbacks live in 4 Services | groß |
| `Q-MC-1` MCP-Transaktionsgrenze | `mcp_server.py:96-107` ohne `commit()` — **~40 Write-Tools schreiben nichts** | groß |
| `Q-MB-7` `total_mass_kg` als abgeleitete Sicht | Spalte + 2 Routen + MCP-Tool schreiben sie direkt | mittel |
| `Q-CC-4` eine `Settings`-Klasse, eine Version | 2 Klassen, **3 Versionen** (1.0.0 / 0.1.0 / 2.0.0) — Voraussetzung für #1095 | mittel |
| `Q-FW-1`/`R2-10` CORS-Allowlist | `main.py:235` `allow_origins=["*"]` + `allow_credentials=True` | klein |
| **`Q-WD-8` ② Hinge-Clearance-Guard** | `build_stations_from_geometry` wird ohne `control_surface_hinge_x_c` gerufen → **Guard läuft in Produktion nie**; Floor nach der Klemme | klein, **sicherheitsrelevant** |
| `Q-WD-8` ① rechteckige/gekappte Holme rechnen | `width`/`height`/`cap_width` nirgends zugewiesen; publiziert immer `None` | mittel |
| `Q-AA-1` zweiten `cd0`-Produzenten entfernen | `stability_service.py:257/360` schreibt Gesamt-CD in die `cd0`-Assumption | klein |
| `Q-AV-3`/`Q-AV-4` AVL-Replay-Artefakt löschen | **Spec führt beide bereits als gelöscht — der Code existiert** | klein |
| `Q-VS-3` fünf tote `design-versions`-Routen | Router registriert, Service wirft nur `NotFoundError` | klein |
| `Q-PT-13` ①–④ COTS-Lebenszyklus | `PUT /component-types/{id}` verwirft Änderungen still mit 200 | mittel |
| `Q-VI-2` `validate_geometry` verdrahten | nur vom Test referenziert | klein |
| `Q-CO-1` Copilot-Audit-Trail | jeder Proposal-Branch heißt gleich | klein |
| `Q-MS-2`/`Q-MS-13` ④ ein Landedistanz-Produzent | `ga_runway`-Defaults in Cessna-172-Klasse, außerhalb 0,5–15 kg | klein |
| `Q-PT-12` Prop-Polar-Spalten + Skip-Report | `Torque_Nm` weiterhin vorhanden | klein |
| `Q-CC-5` deutsche UI-Strings übersetzen | Seed-Labels weiterhin deutsch — blockiert #745 | klein |
| `Q-CT-5` Guard für runde Hinge-Typen | blanker Dict-Lookup → opakes 500 | klein |
| `Q-CC-16` zwei importlose Dateien löschen | beide vorhanden | trivial |
| `Q-FW-8`/`R2-13` `react-plotly.js` entfernen | in `package.json`, kein Import | trivial |
| `Q-PT-1/2/3` Powertrain-Umsetzung | `_PHASE1_PROP_DIAMETER_M = 0.30 m` „up to 2× wrong at 6–8 in" | mittel |

---

## 4. Spec-Drift, die das Audit nebenbei fand

1. **`Q-VS-2` trug die Antwort von `Q-PT-11`** — eine Entscheidung, die nie getroffen
   wurde, stand in der selbstsichersten Form da. #906 wäre dagegen gebaut worden.
   Korrigiert 2026-08-16 (Commit `ff6709ad`); Zählung jetzt 205/206.
2. **Spec und Code widersprechen sich bei `avl_artefact_service`** —
   `avl-integration/requirements.md:701` führt es als gelöscht, die Datei existiert.
3. **Holm-Pipeline: die Unit-Requirements kennen den Stock-Snapper nicht.** Er steht nur
   in `questions.md`, `wave2-lookups.md` und `wave3-lookups.md`. Wer nur die Unit liest,
   liefert den ~15 % unterdimensionierten Zwischenstand aus.
4. **`app/services/spanwise_loads.py` hat keine Use-Case-Einheit** — nur modulgranular
   zugeordnet (betrifft #1041).
5. **`_reversa_sdd/addenda/` enthält nur die README** — für keinen seit der Extraktion
   gemergten PR existiert ein Adendum, obwohl Naht ③ das vorsieht.
6. **#955 ist in der Spec breiter als im Ticket:** ADR 0008 nennt drei divergierende
   Konsumenten, das Ticket adressiert einen.

---

## Bearbeitung der Kollisionen

### #781 — aufgeteilt · 2026-08-16 · **das Audit hatte unrecht**

Das Audit schrieb: *„Backend erzeugt sie bereits (BR-AA24 🟢)"* — also sei die vom Ticket
geforderte Sättigungswarnung ein Duplikat. **Nachgemessen stimmt das nicht.**

```python
# app/services/trim_enrichment_service.py:412-420
usage = abs(deflection_deg) / limit     # je STEUERVARIABLE
```

Seit gh-772 hat eine gemischte Fläche **zwei** Steuervariablen. Physisch schlägt sie um
`δ_sym + δ_anti` aus. Beide Achsen können unter 80 % liegen, während die Fläche bei 120 %
steht. Der kombinierte Wert wird sogar berechnet (`:323-324`) und kommt in der ganzen
Datei **sonst nicht mehr vor**.

**Das Ticket hatte die Lücke korrekt gefunden und nur in der falschen Schicht repariert.**

| | |
|---|---|
| #781 bleibt | Anzeige von L/R-Ausschlag, Differential, Solver-Badge, vorhandenen Warnungen |
| **#1124** neu | kombinierte Reserve je *physischer* Fläche statt je Steuervariable |

**Die Messung lieferte statt Dringlichkeit eine Reihenfolge.** Von 85 Operating Points mit
`deflection_reserves` hat **keiner** eine gemischte Fläche mit zwei Achsen: es gibt 39×
`[ruddervator]pitch_v-tail_0` und **0×** `…yaw_…`, daneben 39× den rohen TED-Namen. Das ist
**#955**. Der Defekt ist real, aber heute nicht auslösbar — und **#955 schaltet ihn scharf**.
Landet #955 allein, überschreiten gemischte Flächen ab dem ersten Trim still ihr Limit.
Vermerkt in beiden Tickets.

**Was daraus für die restlichen Kollisionen folgt:** die Audit-Einordnung ist eine
Hypothese, keine Feststellung. Wo sie *„das gibt es schon"* sagt, gehört nachgemessen, ob
das Vorhandene denselben Fall abdeckt — bei #781 tat es das nicht, und der Unterschied war
sicherheitsrelevant.

### #676 — umgeschrieben · 2026-08-16 · **Ticket und Audit lagen beide daneben**

| Behauptung | Befund |
|---|---|
| Ticket: *„die Schwellen sind statisch"* | **falsch** — `AIRCRAFT_CLASS_TARGETS` führt 7 Klassen mit eigenen V_H/V_V-Bändern |
| Audit: *„klassifiziert bereits klassenabhängig"* | **formal richtig, praktisch falsch** |
| Wirklichkeit | Die Tabelle wird **nie mit etwas anderem als dem Default erreicht** |

`aircraft_class` kommt aus dem `is_default` Loading Scenario. **`loading_scenarios` hat null
Zeilen.** Gemessen: 9 von 15 Flugzeugen mit Mission sind `sailplane` und werden gegen das
Trainer-Band 0.55–0.70 bewertet statt 0.40–0.55 — ein Segler mit V_H = 0.45 erscheint als
`below_range`, obwohl er im Soll liegt. `flying_wing` hat im Klassenvokabular gar keine
Entsprechung.

Ursache ist eine **Vokabeltrennung**: die Mission steht in `mission_objectives.mission_type`
(`trainer`/`sailplane`/`flying_wing`), das Band hängt an `loading_scenarios.aircraft_class`
(`rc_trainer`/`glider`/…). Zweiter, bislang unbemerkter Konsument derselben Zeile:
`loading_template_service.get_templates_for_class`.

→ **#1125** (Ursache: Klasse wird nie gesetzt), **#676** umgeschrieben auf das, was wirklich
fehlt — die richtungsabhängige Begründung über den `DesignWarning`-Kanal statt einer zweiten
Bandtabelle.

---

### #616 — umgeschrieben · 2026-08-16 · **das Vorhandene ist da und defekt**

Audit-Einordnung *„eigener `P_required` + eigene V-n-Kurve — es gibt beides schon"*:

| | |
|---|---|
| `P_required` | **stimmt** — `endurance_service._power_required` (:77), `powertrain_sizing_service:92` delegiert bereits dorthin (BR-PT30 🟢) |
| V-n-Hüllkurve | **existiert und ist defekt** |
| Blocker #615 | **geschlossen** — die Blocker-Zeile im Ticket ist veraltet |

`flight_envelope_service.py:604-606` setzt `n = 1.0` für **jeden** Betriebspunkt, mit der
Begründung *„Without stored CL, we cannot derive actual load factor"*. Der Wert ist
gespeichert — im `description`-Freitext derselben Zeile: `turn_60` trägt `target_n=2.00`,
dazu `q=0.43083`, `r=0.24874`. Das höchstbelastete Manöver des Standardsatzes erscheint im
V-n-Diagramm auf der Horizontalfluglinie. → **#1126**

Ursache dahinter: ein numerischer Auslegungswert lebt in Prosa statt in einer Spalte. Der
Generator schreibt ihn, der Konsument kann ihn nicht sehen, und der Kommentar erklärt die
Blindheit zur Naturgesetzlichkeit.

**#616 konsumiert danach**, statt B.3 selbst zu bauen — sonst zeigte der neue Reiter
dieselbe falsche Aussage, nur prominenter.


### #675 — geschlossen · 2026-08-16 · **die Prämisse hält der Messung nicht stand**

Das Ticket nimmt an, `V_stall` sei ein gespeicherter Wert, der gegenüber `mass`, `S` und
`CL_max` veralten kann. **Gemessen: `v_stall` wird nirgends persistiert** — keine Spalte,
kein `design_assumptions`-Eintrag. Jeder Konsument leitet es zur Anfragezeit her
(`flight_envelope_service.py:314`). Es gibt keinen Cache, der veralten könnte.

Der reale Fund ist ein anderer: **drei Implementierungen derselben Formel**, eine davon mit
stiller Klemmung `cl_max_safe = max(cl_max, 0.5)` (`assumption_compute_service:1758`).
Bei `cl_max < 0.5` liefert sie eine niedrigere — optimistischere — Stallgeschwindigkeit
als die beiden anderen. Heute nicht auslösbar (0 von 27 Flugzeugen unter 0.5, Minimum
1.011), scharf in genau dem Fall, für den die Klemmung gebaut wurde. → **#1127**

### Epic #669 — Kontext geklärt · 2026-08-16

Drei der sechs Sub-Issues sind geliefert (#670, #672, #674). Die drei offenen hängen alle
an derselben überholten Annahme: *„R-W4 etabliert das `RuleResult`-Schema"*, begründet
„analog zum etablierten `PolarRejection`".

**ADR 0020 nennt `PolarRejection` namentlich als eine der zwei Formen, die es
zusammenführt.** Ein `RuleResult` wäre die dritte. Es existiert im Code nicht — es ist
nichts zurückzubauen, nur nicht anzufangen.

Der naheliegende Einwand — der `DesignWarning`-Kanal sei für *degradierte Zahlen*, nicht
für Designurteile — trägt nicht: `DesignWarning.category` ist ein **freier String**, und
die heute vergebenen Werte sind `'authority'` und `'trim_quality'`, beides Designurteile.
Die 35 Regeln des Working Papers brauchen eine eigene `category`, kein eigenes Schema und
keinen eigenen Endpunkt.

| Sub-Issue | neu |
|---|---|
| #675 | geschlossen → #1127 |
| #676 | umgeschrieben, blockiert von #1125 |
| #673 | kollidiert separat mit `Q-AV-8` (Eigenmoden hinter dem Massenmodell; `Cnr`/`Clr` nur im AVL-Pfad) |


### #61 / #62 — umgeschrieben · 2026-08-16 · **das Urteil prüft nur eine von drei Achsen**

Das Audit zitierte `stability_service.get_stability_summary` als alleinige Autorität.
**Diese Funktion existiert nicht** — sie war im Audit erfunden. Real ist
`classify_stability(static_margin_pct)` (`stability_service.py:70`), und sie beruht
ausschließlich auf der statischen Reserve:

> `>5% → stable, 0-5% → neutral, <0% → unstable`

`Cnb` und `Clb` werden berechnet, in `stability_results` gespeichert — und für das Urteil
nie gelesen. Gemessen über 13 Zeilen: Flugzeuge 8 und 42 tragen `Cnb = −0.0014`, also das
falsche Vorzeichen für Wetterfahnenstabilität, und heißen `stable`. Flugzeug 47 zeigt eine
statische Reserve von **119 %** des MAC. Der Benutzer sieht davon nur `Stability: stable`
(`MarkerDetailBox.tsx:72`).

`BR-AA14` 🟢 **beschreibt alle drei Tests** (`Cma < 0`, `Cnb > 0`, `Clb < 0`) — der Code
setzt einen um. **#61 hat also recht, dass sie fehlen**, und unrecht nur darin, sie im
Frontend herzuleiten. → **#1128** als Vorbedingung.

**Vom Maintainer korrigiert:** die Spider-Web-Ansicht aus §6 D existiert für Stabilität
nicht. `RadarChart.tsx` wird ausschließlich von `MissionCompliancePanel.tsx` im
Mission-Bereich genutzt. Der Punkt ist Neuentwicklung, kein zu bewahrender Bestand — meine
Einordnung als „Ausnahme von BR-FE36" ging von einem falschen Ist-Zustand aus. #62 ist
jetzt Sub-Issue von #61.


### Gruppe 2 — die Freeze-Grenze · 2026-08-16

**#941 war nie blockiert.** ADR 0002 §1 friert `aircraft_topology/` und
`GeneralJSONEncoderDecoder.py` ein; `VaseModeWingCreator.py` liegt in
`airplane/creator/wing/` und steht in **keiner** der Listen. Das Schwesterdokument liest
das richtig (`cad-designer-topology/design.md:11`: *„`creator/**` … are open"*), zwei
Traceability-Zeilen behaupteten das Gegenteil **unter Berufung auf dieselbe ADR**. Beide
korrigiert (`ef0b3cef`). Die teurere Sorte Spec-Fehler: er stoppt erlaubte Arbeit, und
niemand widerspricht einer ADR.

**#283 umgeschrieben.** Kern ADR-konform; präzisiert wurde die Klausel *„Bugs found →
separate bug ticket"*, die für die eingefrorene Zone dem ADR widerspricht
(*„deliberately not fixed"*). Neu: Funde in `aircraft_topology/` werden
**Charakterisierungstests** — ausdrücklich als *dokumentiertes* Verhalten gekennzeichnet,
sonst wird der Test zum Argument gegen eine spätere Korrektur (Beispiel
`_main_wing_index = 0`, die schlafende ≈8×-Referenzflächenverwechslung). Alles außerhalb
ist reguläres Bug-Ticket. Zusätzlich: die Spec führt mit TT-01…TT-25 einen präziseren
Wellenschnitt als die LOC-Wellen des Tickets.

**Offen und maintainer-pflichtig:** #762 (echt im Freeze — Präzedenz gh-934) und #57
(zweiter Erzeugungspfad neben „neuer Creator").


## Das Muster hinter den bearbeiteten Fällen

Fünfmal an einem Tag dieselbe Struktur — **richtige Logik hinter einer Eingabe, die niemand
liefert**:

| | Mechanismus | wodurch abgeschaltet |
|---|---|---|
| **#1096** | Hinge-Clearance-Guard | Default eines optionalen Parameters, den kein Aufrufer setzt |
| **#1124** | Ausschlags-Sättigungsprüfung | greift je Steuervariable statt je physischer Fläche |
| **#1125** | klassenabhängige Leitwerksbänder | Quellfeld ist in der gesamten DB leer |
| **#1126** | V-n-Hüllkurve mit Lastvielfachen-Markern | Marker hartkodiert auf 1.0, Wert steckt im Freitext |
| **#1128** | Stabilitätsurteil | prüft nur die Längsachse; `Cnb`/`Clb` gespeichert und ungelesen |

Das ist keine Nachlässigkeit beim Extrahieren, sondern eine Eigenschaft dieser Codebasis:
sie ist reich an differenzierter Logik, die auf Konfiguration wartet, die nie ankommt.

**Weder ein Aufrufgraph noch ein Lesedurchgang findet das.** Alle drei Fälle wurden erst
durch eine **Messung gegen echte Daten** sichtbar — beim Implementieren (#1096) oder beim
Nachprüfen einer Audit-Behauptung (#1124, #1125). Für die verbleibenden Kollisionen heißt
das: wo das Audit *„das gibt es schon"* schreibt, ist die Frage nicht, ob der Code existiert,
sondern **ob er je mit echten Daten läuft**.
