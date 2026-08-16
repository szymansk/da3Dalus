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
