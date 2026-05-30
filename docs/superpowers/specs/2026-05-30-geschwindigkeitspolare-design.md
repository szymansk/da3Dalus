# Geschwindigkeitspolare im „Analysis – Polar"-Tab

**Datum:** 2026-05-30
**Status:** Akzeptiert (Design), bereit für Implementierungsplanung
**Sprache der UI:** Deutsch/Englisch gemischt wie im Bestand (Labels englisch, Tooltips teils deutsch)

## Ziel

Im Tab **„Analysis – Polar"** zusätzlich eine **Geschwindigkeitspolare**
(Sinkrate `w` [m/s] über Fluggeschwindigkeit `V` [m/s]) anzeigen. Neben der
gegebenen Masse (Design-Assumption `mass`, calculated **oder** estimate) sollen
**weitere Massen** als Vergleichskurven angegeben werden können
(Wasserballast-/Flächenbelastungs-Effekt beim Segler).

## Entscheidungen (vom Nutzer bestätigt)

1. **Datenbasis:** Echte AeroBuildup-α-Sweep-CL/CD (an die angezeigte
   Widerstandspolare gekoppelt). Andere Massen skalieren die Kurve analytisch.
2. **Massen-Eingabe:** Liste absoluter Massen in **kg**, vorbefüllt mit der
   effektiven Assumption-Masse.
3. **Darstellung:** Zusätzliches Chart in der bestehenden Polar-Grid.
4. **Eingabeformat:** Deutsches Zahlenformat — **Dezimal-Komma**, **Semikolon
   als Trenner**, z. B. `1,5; 2,0; 2,5`. Parser akzeptiert auch `.` als
   Dezimaltrenner.

## Physik (eine Aero-Rechnung, analytisch über Masse skaliert)

Aerodynamische Beiwerte CL/CD (die Widerstandspolare) sind
**massenunabhängig** — nur die bei gegebener Geschwindigkeit erreichte CL hängt
von der Masse ab. Ein einziger AeroBuildup-α-Sweep liefert die CL/CD-Punkte;
pro Masse `m` rein analytisch:

```
für jeden Sweep-Punkt mit CL > 0:
    V(CL) = sqrt( 2 · m · g / (rho · S_ref · CL) )      # Gleitflug-Geschwindigkeit
    w(CL) = V(CL) · (CD / CL)                            # Sinkrate (positiv = sinkend)
```

- Nur **CL > 0** wird berücksichtigt (stationärer Gleitflug; negative/Null-CL
  liefern kein sinnvolles V).
- Konsequenz: Massen skalieren die Kurve mit `V, w ∝ sqrt(m)` →
  **kein zusätzlicher Aero-Lauf** nötig, nur Algebra über die bestehende Polare.
- `g = 9.81`, `rho = asb.Atmosphere(altitude).density()`, `S_ref` aus dem
  bereits gebauten ASB-Airplane (`asb_airplane.s_ref`).

### Markante Punkte je Kurve

- **V_stall** — bei `CL_max` (Maximum der Sweep-CL): `V = sqrt(2 m g / (rho S CL_max))`.
- **V_min_sink / w_min** — Punkt mit minimalem `w`.
- **V_best_glide / (L/D)_max** — Punkt mit minimalem `w/V` (= maximalem `V/w` =
  maximalem `CL/CD`).

Zur Konsistenz-Validierung: `w_min` aus dem diskreten Sweep muss näherungsweise
mit dem geschlossenen `_min_sink_rate(...)` aus
`assumption_compute_service.py` übereinstimmen (gleiche Physik, Anderson §6.7.2).

## Darstellung

- Neues Plotly-Chart **„Geschwindigkeitspolare (w über V)"** in der bestehenden
  Polar-Grid (`AnalysisViewerPanel`, Bereich `activeTab === "Polar"`).
- **Eine Kurve pro Masse** mit **Legende** (Masse in kg). Basis-Masse
  hervorgehoben (kräftige Farbe/dicker), weitere Massen in abgesetzten Farben.
- **Segler-Konvention:** `V` auf der x-Achse, **Sinkrate nach unten** aufgetragen
  (y-Werte = `−w`), y-Achse beschriftet als `w [m/s]` (Sinken).
- Marker + Annotation für **V_min_sink** und **V_best_glide** (auf der
  Basis-Masse-Kurve; optional je Kurve).

## Architektur & Komponenten

### Backend

**Schema** (`app/schemas/AeroplaneRequest.py`):
- `AlphaSweepRequest` erhält optionales Feld
  `masses_kg: Optional[list[float]] = None` (jeweils `> 0`).

**Schema** (neu, `app/schemas/aeroanalysisschema.py` oder passendes Modul):
```python
class SpeedPolarCurve(BaseModel):
    mass_kg: float
    is_base: bool                 # entspricht der effektiven Assumption-Masse
    V: list[float]                # m/s, aufsteigend nach V sortiert
    w: list[float]                # m/s, Sinkrate positiv
    cl: list[float]
    cd: list[float]
    v_stall: float | None
    v_min_sink: float | None
    w_min: float | None
    v_best_glide: float | None
    ld_max: float | None

class SpeedPolar(BaseModel):
    base_mass_kg: float
    s_ref: float
    rho: float
    altitude: float
    curves: list[SpeedPolarCurve]
```

**Service** (`app/services/analysis_service.py`):
- Neuer reiner Helper
  `_compute_speed_polar(cl, cd, masses_kg, base_mass_kg, s_ref, rho) -> SpeedPolar`.
  Vollständig unit-testbar ohne DB/Aero.
- `analyze_alpha_sweep(...)` ergänzt: effektive Masse aus Assumption (`mass`)
  laden; `masses = (request.masses_kg or []) ∪ {base}`; `s_ref` aus
  `asb_airplane`, `rho` aus `altitude`; `speed_polar` berechnen und in die
  Antwort aufnehmen.
- Antwort additiv:
  ```python
  return {
      "analysis": result,
      "characteristic_points": characteristic_points,
      "speed_polar": speed_polar,          # NEU
      "aircraft_name": ...,
  }
  ```
- Massenliste: deduplizieren, aufsteigend sortieren; Basis-Masse markieren
  (`is_base`). Liefert immer mindestens die Basis-Kurve.

**Endpoint:** unverändert — `POST /aeroplanes/{id}/alpha_sweep` (additives
Request-/Response-Feld). Keine neue Route.

### Frontend

**Hook** (`frontend/hooks/useAnalysis.ts`):
- `AlphaSweepParams` erhält `masses_kg?: number[]`.
- `AnalysisResult`/Rückgabe erhält `speedPolar` (aus `data.speed_polar`
  extrahiert; null wenn nicht vorhanden).

**ConfigPanel** (`frontend/components/workbench/AnalysisConfigPanel.tsx`):
- Neuer Prop `effectiveMassKg?: number | null` (aus `currentMassKg` in
  `app/workbench/analysis/page.tsx`, analog zu `designCgX`).
- Neues Textfeld **„Massen [kg]"** im Polar-Bereich, vorbefüllt mit
  `effectiveMassKg` (z. B. `"1,5"`). Placeholder `z. B. 1,5; 2,0; 2,5`.
- Parser `parseMasses(input): number[]`:
  ```
  input.split(";") → je Token trim → "," durch "." ersetzen → parseFloat
  → nur endliche Werte > 0 behalten
  ```
- `handleRunPolar` übergibt `masses_kg: parseMasses(massesInput)`.

**Viewer** (`frontend/components/workbench/AnalysisViewerPanel.tsx`):
- Neues Chart in der Polar-Grid, gespeist aus `result.speedPolar.curves`.
- `PlotlyChart` minimal erweitern: Unterstützung mehrerer benannter Traces
  (`traces: {name, x, y, color}[]`) + `showLegend?: boolean`. Bestehende
  Single-Trace-Aufrufe bleiben unverändert (Abwärtskompatibilität).
- y-Werte als `−w` auftragen (Sinken nach unten); Marker für V_min_sink /
  V_best_glide.

## Scope (YAGNI)

**Enthalten:** echte Sweep-Daten, kg-Liste (deutsches Format), ein neues Chart
mit Mehr-Massen-Kurven + markante Punkte; additive Backend-Erweiterung; Tests.

**Nicht enthalten (separat):**
- Parabolischer Umschalter (CD0 + k·CL²).
- Tangenten-Overlay vom Ursprung (Sollfahrt).
- Reynolds-Re-Run pro Masse.
- Bereits gefundene Alt-Bugs (nur als separate Bug-Tickets notiert, **nicht** in
  diesem Feature behoben):
  - `sweep_var`-Dropdown und Analysis-Tool-/Flight-Profile-Selektoren sind
    dekorativ (`handleRunPolar` ignoriert sie).
  - `Number.parseFloat(alphaStart) || -5` verwirft eine eingegebene `0` als
    Sweep-Start.

## Tests (TDD, Ziel >80 %)

**Backend** (`app/tests/`):
- `_compute_speed_polar`: Formeln V/w korrekt; **√m-Skalierung** zwischen zwei
  Massen; CL≤0-Punkte gefiltert; `w_min` konsistent mit `_min_sink_rate`
  (Toleranz); leere/None-Massenliste → genau Basis-Kurve; `is_base` korrekt
  gesetzt; Dedup/Sortierung.
- Integration: `analyze_alpha_sweep` liefert `speed_polar` mit ≥1 Kurve für ein
  Referenzflugzeug (z. B. Sailplane), Werte plausibel
  (V_stall < V_min_sink < V_best_glide-Größenordnung; w_min > 0).

**Frontend** (`frontend/__tests__/`):
- `useAnalysis`: extrahiert `speedPolar` aus Mock-Response korrekt; null wenn
  Feld fehlt.
- `parseMasses`: `"1,5; 2,0; 2,5"` → `[1.5, 2.0, 2.5]`; gemischt `.`/`,`;
  leere/ungültige Tokens verworfen; negative/0 verworfen.
- Viewer rendert N Traces aus `speedPolar.curves` (N = Anzahl Massen) inkl.
  Legende.

## Risiken / Annahmen

- CL/CD aus AeroBuildup sind für den relevanten Bereich (CL>0) monoton genug,
  dass V/w sinnvolle Polaren ergeben; sehr kleine CL (hohes V) bleiben Teil der
  Kurve (rechter Ast).
- `S_ref` und `mass`-Assumption sind vorhanden (sonst klare Fehler-/Leerzustände
  wie im Bestand).
- Additive Erweiterung von `alpha_sweep` bricht bestehende Consumer nicht
  (neues optionales Feld + neuer Response-Key).
