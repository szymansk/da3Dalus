# Turbulator als Flügel-Element — Positionsoptimierung & Performance-Integration

**Datum:** 2026-06-09
**Typ:** Feature (Epic mit Sub-Issues)
**Motivation:** eHawk (Elektro-UAV/RC, Spannweite 1,503 m, AR 11,3, Re ≈ 85k–265k).
Ziel des Nutzers: (1) die **optimale Turbulator-Position** bestimmen, um sie auf
die Fläche zu drucken, und (2) eine **genauere Performance-Aussage** treffen, ob
sich die Gleitzahl (~24) mit Turbulator verbessert.

---

## Problem

Bei niedrigen Reynolds-Zahlen (85k–265k) bildet sich auf der Profiloberseite eine
**laminare Ablöseblase (LSB)**, die Profilwiderstand kostet. Ein **Turbulator**
(erzwungene Transition) kann die Blase unterdrücken und L/D verbessern — aber nur
bei *richtiger* Position (Reibungs-vs-Blasen-Optimum, kein „so weit vorn wie
möglich"). da3Dalus kann den Turbulator heute weder modellieren noch seine
optimale Position bestimmen noch seinen Effekt sichtbar in die
Flugzeug-Performance einrechnen.

### Wichtiger Befund aus dem Brainstorming

- **XFOIL ist NICHT nötig.** NeuralFoil unterstützt erzwungene Transition bereits
  (`xtr_upper`/`xtr_lower`), deterministisch und ohne externe Binary. Der
  NeuralFoil-Endpoint akzeptiert die Parameter schon, und der AVL-Pfad
  (`inject_cdcl` + `CdclConfig.xtr_*`) trägt sie ebenfalls. Der cd-Effekt eines
  Turbulators ist damit heute prinzipiell rechenbar.
- XFOILs einzige echte Nische (volle `cp(x)`-Verteilung → LSB als Plateau
  sichtbar) wird **bewusst nicht** umgesetzt — passt nicht zur
  Determinismus-Linie des Projekts (NeuralFoil wurde genau deshalb gewählt).
- XFLR5 wird nicht integriert (reine Desktop-GUI ohne Headless-API; seine
  3D-Rolle macht in da3Dalus bereits AeroSandbox/AeroBuildup).

### Experten-Konsens (aerodynamics-expert + rc-aircraft-designer)

- Turbulator gehört auf die **Oberseite**, **knapp stromauf des laminaren
  Ablösepunkts** für den Auslegungs-CL. Typisch **x/c ≈ 0,5–0,65** in diesem
  Re-Band; **kein fester Wert** — wandert nach vorn, wenn Re/CL sinken.
- **Re fällt zur Spitze** → Blase außen schlimmer → Optimum wandert nach außen →
  **pro Schnitt** rechnen ist physikalisch zwingend.
- Mission: Segler/Thermik = Hauptnutzer; der eHawk hat motorisierten
  XC-/Thermiksegler-Charakter → genau die Kategorie, die profitiert.
- Direktive beider Experten: Position **aus der Polare am Schnitt-Re** bestimmen,
  nicht per festem Prozentwert. Das deckt sich exakt mit dem geplanten
  NeuralFoil-Sweep.

---

## Lösung (Architektur)

Der Turbulator wird ein **erstklassiges Flügel-Element wie eine Control Surface**
(`TrailingEdgeDevice`) — voller Stack, im UI an XSEC/Segment hinzufügbar, im
Modal editierbar, mit Optimierungs-Button. Wenn vorhanden, fließt er **zwingend**
in die Aerodynamik-Rechnung ein.

### Datenmodell (spiegelt das TrailingEdgeDevice-Muster)

Ein **optionaler Turbulator pro Segment** (singular, wie TED), Oberseite.

| Feld | Typ | Bedeutung |
|---|---|---|
| `form` | enum (`zigzag`, `dots`, `thread`) | Bauform (für spätere CAD-Geometrie) |
| `height_mm` | float | Höhe des Zackenbands/Fadens |
| `position_root` | float (x/c, 0..1) | Position an der Segmentwurzel |
| `position_tip` | float (x/c, 0..1) | Position an der Segmentspitze |
| `enabled` | bool | aktiv → muss in Rechnung |

Position root/tip ⇒ lineare Interpolation entlang der Spannweite (wie TED
`rel_chord_root`/`rel_chord_tip`).

**Stack (analog TED/Spare):**
- **cad_designer-Topologie:** neue `Turbulator`-Klasse + Feld an `WingSegment`
  / `WingConfiguration` (siehe Architektur-Entscheidung unten).
- **Pydantic-Schema:** `Segment.turbulator: Turbulator | None` in
  `app/schemas/wing.py`.
- **DB:** neue Tabelle `wing_xsec_turbulators` (FK auf `wing_xsec_details`,
  one-to-one) + Alembic-Migration.
- **Converter:** bidirektional Schema ↔ DB ↔ Topologie in
  `app/converters/model_schema_converters.py`.
- **Backward-Compat:** neue Felder sind `Optional=None`; alte WingConfigs laden
  unverändert (keine Versionsnummer im Projekt, Default-on-load-Muster).

### Architektur-Entscheidung: Read-only-Topologie

CLAUDE.md verbietet das Modifizieren der `cad_designer`-Topologie-Klassen.
`TrailingEdgeDevice`/`Spare` hängen aber bereits an `WingSegment` (vor der Regel
hinzugefügt). **Entscheidung des Maintainers:** `WingSegment`/`WingConfiguration`
werden um ein `turbulator`-Feld **erweitert** (100 % konsistent mit dem
TED-Muster, Creator liest direkt vom Segment) — als **bewusste, dokumentierte
Ausnahme**. CLAUDE.md wird entsprechend aktualisiert, damit der Präzedenzfall
festgehalten ist (Turbulator zur Liste der erlaubt-erweiterbaren Segment-Elemente
analog TED/Spare). `GeneralJSONEncoder/Decoder`-Verhalten wird über das
bestehende `__getstate__`/`from_json_dict`-Muster bedient.

### Auslegungspunkt — über Assumptions

Neue Assumption **`design_speed_mps`** nach dem bestehenden
estimate/calculated/active_source-Muster:
- **CALCULATED (Default):** aus `v_md_mps` (Minimum-Drag = bestes Gleiten) des
  `assumption_computation_context`.
- **ESTIMATE:** vom Nutzer überschreibbar.
- Der Optimierer nutzt den `effective_value` → daraus pro Schnitt das lokale Re
  (lokale Tiefe × V) und den lokalen Arbeits-cl.

### Optimierer (Kern, deterministisch)

Pro Schnitt am lokalen (cl, Re):
- Lokalen Arbeits-cl **aus dem vorhandenen `section_aoa_service`** ziehen
  (echte Auftriebsverteilung am Auslegungspunkt).
- NeuralFoil-**Sweep über `xtr_upper`** auf einem x/c-Gitter (z. B. 0,20–0,90).
- **Ziel:** cd minimieren bei festgehaltenem Arbeits-cl ⇒ max lokales l/d.
- Ausgabe pro Schnitt: `xtr_opt`, `cd_clean`, `cd_tripped`, `Δcd`, plus
  Plausibilitäts-Check gegen die natürliche Transition (NeuralFoil `Top_Xtr`).
- **Scope wählbar:** pro XSEC/Segment **oder** gesamt (eine repräsentative
  Position fürs ganze Profil/MAC).

### Performance-Delta (3D) — „wird die Gleitzahl > 24?"

Den vorhandenen Aero-Pfad **zweimal** fahren — ohne vs. mit `xtr_opt` pro Schnitt
— und das L/D-Delta ausweisen. **Default-Tool: AeroBuildup** (Projekt-Primär).
Der AVL-CDCL-Pfad trägt `xtr` ebenfalls und bleibt verfügbar.

### Pflicht-Integration

Sobald ein `enabled` Turbulator an einem Flügel hängt, **muss** der Aero-Pfad
seine `xtr_upper`-Werte pro Schnitt anwenden (kein optionales Beiwerk). Das
Hinzufügen/Ändern eines Turbulators triggert den Recompute (wie andere
Geometrie-/Assumption-Änderungen).

### Fehlerbehandlung

Schnitte ohne brauchbares Optimum (niedrige NeuralFoil-Confidence / kein
cd-Minimum) werden als **Warnung pro Schnitt** ausgewiesen — kein stiller
Fallback (Memory-Linie „Design-Error-Feedback").

### Frontend

- Turbulator an XSEC/Segment **hinzufügbar wie eine Control Surface**.
- **Modaler Dialog** zum Editieren: Form (dots/zigzag/…), Höhe, Position (x/c je
  Schnitt: root & tip).
- **Optimize-Button** stößt die Positionsoptimierung an (Scope: Schnitt/Segment
  oder gesamt).
- Nach Hinzufügen wird zwingend mit den resultierenden Werten gerechnet;
  L/D-Delta mit/ohne sichtbar.
- der Turbolator wird wie ein Control Surface mit in den Construction Preview eingezeichnet.

---

## Epic-Decomposition (Sub-Issues)

1. **Domain-Model & Persistenz** — `Turbulator`-Topologieklasse + WingSegment-
   Erweiterung (dokumentierte Read-only-Ausnahme + CLAUDE.md-Update),
   Pydantic-Schema, DB-Tabelle `wing_xsec_turbulators` + Migration, Converter,
   Backward-Compat, Serialisierung. **Keine Aero-Logik.**
2. **Optimizer-API & Aero-Integration** — `design_speed_mps`-Assumption
   (calculated aus v_md / overridable), NeuralFoil-xtr-Sweep-Service (pro
   Schnitt, Scope Schnitt/Segment/gesamt), `POST /aeroplanes/{id}/turbulator/
   optimize`, **Pflicht-AeroBuildup-Integration** (xtr pro Schnitt anwenden +
   with/without-L/D-Delta), Design-Warnung bei Nicht-Konvergenz. Fast-Tests mit
   gestubbtem NeuralFoil-Boundary + langsamer Integrationstest.
3. **Frontend** — Turbulator-Element an XSEC/Segment (wie Control Surface),
   Modal-Dialog (Form/Höhe/Position root&tip), Optimize-Button (Scope-Auswahl),
   Pflicht-Recompute-Trigger, L/D-Delta-Anzeige.

---

## Out of Scope

- **CAD-Geometrie des Turbulators** (gedruckter Zackenband-/Dot-Streifen auf der
  Fläche, neuer Creator) → **separates Folge-Ticket** nach dem Epic. Das
  Datenmodell trägt `form`/`height_mm` bereits, damit ein künftiger Creator die
  Info bekommt.
- **XFOIL / `cp(x)`-Visualisierung** der LSB → bewusst nicht (Determinismus-Linie).
- **XFLR5-Integration** → nicht möglich/nicht nötig.
- **Unterseiten-Turbulator** → später; jetzt nur Oberseite.
- Rumpf-/Interferenz-/Nacellenwiderstand fürs „ganze Flugzeug" → unverändert
  außerhalb dieses Features.

---

## Akzeptanzkriterien (Epic-Ebene)

- [ ] Ein Turbulator kann an einem Flügelsegment/XSEC modelliert, gespeichert und
      abwärtskompatibel geladen werden.
- [ ] Die optimale `xtr`-Position wird pro Schnitt (und „gesamt") am
      Assumptions-gesteuerten Auslegungspunkt deterministisch bestimmt.
- [ ] Ein aktiver Turbulator fließt zwingend in die AeroBuildup-Rechnung ein; das
      L/D-Delta mit/ohne ist abrufbar.
- [ ] Nicht-konvergente Schnitte werden als Warnung gemeldet, nicht still
      überdeckt.
- [ ] Im Frontend ist der Turbulator wie eine Control Surface hinzufügbar,
      editierbar (Modal) und optimierbar (Button).
- [ ] Im Preview ist der Turbolator in der 3D Darstellung des Flugzeugs deutlich als Linie sichtbar
- [ ] Test-Coverage > 80 %; Fast-Tier mit gestubbtem Solver-Boundary.
