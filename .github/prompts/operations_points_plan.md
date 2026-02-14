# Operating-Point-Set Generation mit Flight-Profile-Integration (inkl. Dutch-Roll Startpunkt)

## Summary
Wir überarbeiten die Spezifikation (`operating_points.md`) und implementieren einen generatorbasierten Workflow, der:

1. aus `aircraft_id` + zugewiesenem `flight_profile` ein Standard-Operating-Point-Set erzeugt,
2. jeden Punkt **trimmt**, **validiert**, **fallbackt**,
3. Punkte + Sets **persistent** speichert,
4. **pro Aircraft** eigene OP-Datensätze verwaltet (keine Shared-OPs),
5. einen zusätzlichen **Dutch-Roll Startpunkt** als **getrimmten (oder markiert ungetrimmten) Ausgangszustand** erzeugt, inkl. **Controls/Ruderausschlägen** als Ergebnis.

---

## Entscheidungen (festgelegt & präzisiert)

### 1) Mapping-Modell: Pro Aircraft kopieren
- Operating Points und Operating Point Sets sind **aircraft-spezifisch**.
- **DB-Integrität** soll diese Entscheidung technisch absichern (siehe Datenmodell).

### 2) Dutch-Roll Typ: „Trimmed excitation start state“
- Der OP ist **ein statischer Zustand** (kein Zeitverlauf).
- „Excitation“ meint: Startzustand für nachgelagerte Sweep/Time-Simulationen, nicht dass der OP selbst Zeitverläufe enthält.

### 3) Units in Storage (SI-konsistent)
- alpha/beta in **rad**, p/q/r in **rad/s**, velocity in **m/s**, altitude in **m**.
- Controls/Deflections: entweder **deg** oder **rad** einheitlich festlegen.  
  Hinweis: AeroSandbox nutzt bei `with_control_deflections(...)` Grad-Konventionen (downwards-positive).  
  → Wenn DB rad speichert: konsequente Konvertierung (deg ↔ rad) erforderlich.  
  Quelle: AeroSandbox Geometry API (Control deflections) https://aerosandbox.readthedocs.io/en/master/autoapi/aerosandbox/geometry/

---

## AeroSandbox-Bezug: Nutzung & Pflicht-Checks

### A) Ruderausschläge modellieren: grundsätzlich JA
- AeroSandbox bietet `Airplane.with_control_deflections({...})` zum Setzen von Control-Deflections.  
  Quelle: https://aerosandbox.readthedocs.io/en/master/autoapi/aerosandbox/geometry/

**Konsequenz:** Ruderausschläge/Controls sind Teil des **Trim-Ergebnisses** und müssen im **Operating Point** gespeichert werden (nicht nur im Flight Profile).

### B) Stability Derivatives für Dutch-Roll: verfügbar, aber Validität prüfen
- AeroSandbox bietet `run_with_stability_derivatives(alpha, beta, p, q, r)`.  
  Quelle: https://aerosandbox.readthedocs.io/en/develop/autoapi/aerosandbox/
- Changelog-Hinweis: Rate derivatives (p/q/r) „not yet tested“.  
  Quelle: https://peterdsharpe.github.io/AeroSandbox/CHANGELOG.html

**Pflicht-Check:** Wenn Dutch-Roll-Analysen auf p/q/r-Derivatives basieren → Tests/Benchmarks oder zunächst nur alpha/beta-Derivatives verwenden.

### C) Kritischer Implementierungs-Check: wirken Deflections in eurer Analyse wirklich?
- Es existieren Berichte, dass Deflections in bestimmten Analysepfaden (z.B. VLM) nicht wie erwartet berücksichtigt wurden.  
  Quelle: https://github.com/peterdsharpe/AeroSandbox/issues/134

**Pflicht-Check:** Für eure gewählte AeroSandbox-Analyse (VLM/Buildup/…) muss ein Test nachweisen: *Deflection ≠ 0 → Kräfte/Momente ändern sich.*

---

## Revised Prompt (`operating_points.md`) – konsistent

### Scope
- Flight Profiles sind implementiert; OP-Task fokussiert auf **Generator + Persistenz + API**.
- Keine Flight-Profile-CRUD-Anforderung im OP-Prompt.

### Input-Quelle
- Primär: `aircraft.flight_profile_id` → geladenes `RCFlightProfile`.
- Fallback defaults nur, wenn kein Profil zugewiesen ist.

### Datenmodell-Regeln
- Operating Points und Sets sind **aircraft-spezifisch**.
- Jeder Operating Point speichert:
  - Zustände (V, h, alpha, beta, p, q, r, …)
  - **Controls/Deflections** (rudder/aileron/elevator, ggf. flap, throttle/power) als **Trim-Ergebnis**
  - **Status/Warnungen strukturiert** (kein reines Freitext-Tagging)

### Minimal-Set (bestehende 10 Punkte) + neu (11) `dutch_roll_start`

**(11) dutch_roll_start**
- config = clean
- velocity = `max(cruise_speed, 1.3 * Vs_clean)`
- target: level-flight trim, koordinierter Geradeausflug als Basis (`beta_target = 0` robust)
- optionaler Seed für spätere Excitation: `excitation_hint = {"beta_deg": ±2}` (nur Metadaten)
- output: statischer OP

**Begründung:** „beta≠0 level-flight trim“ ist möglich, setzt aber voraus, dass:
1) eure Trim-API Controls als Variablen zulässt und zurückliefert,
2) Deflections in eurer AeroSandbox-Analyse tatsächlich wirken (Pflicht-Check oben).

### Validation/Fallback-Policy (präzisiert, OP-abhängig)
- Einheitliche Statusklasse pro OP: `TRIMMED | NOT_TRIMMED | INVALID | LIMIT_REACHED`.
- Speed-Fallback ist nicht immer „+“:
  - stall/approach: +5…+15%
  - max_speed: −5…−15%
  - range/endurance: fallback abhängig von Zieldefinition (speed- vs power/throttle-gebunden)
- Config fallback: landing/takeoff → clean
- Persistiere Soft-Fails als `NOT_TRIMMED` + warnings; Pipeline läuft weiter.

### Output-Kontrakt
- `alpha` immer `list[float]` Länge 1.
- `beta,p,q,r` sind Trim-Resultat (nicht künstlich auf Target zurückgesetzt).
- `controls` ist Bestandteil jedes OP-Outputs (mindestens bei `TRIMMED`, optional leer bei `NOT_TRIMMED`).

---

## Public API / Interface Changes

### Schema (z.B. `aeroanalysisschema.py`)
- `OperatingPointSchema.alpha: List[float]` (min_items=1, max_items=1).
- Units-Beschreibungen: rad / rad/s / m/s / m.
- **Neu:** `controls: dict[str, float]`
  - z.B. `{"elevator_deg": ..., "aileron_deg": ..., "rudder_deg": ..., "throttle": ...}`
  - Konvention für Einheiten und Keys festlegen.
- **Neu:** `status: Enum`, `warnings: list[str]`, optional `excitation_hint`.

### Models (z.B. `analysismodels.py`)
- `OperatingPointModel.aircraft_id` (FK auf `aeroplanes.id`)
- `OperatingPointSetModel.aircraft_id` (FK auf `aeroplanes.id`)

### Set↔Points Relation (konsistent zur Pro-Aircraft-Entscheidung)
**Option A (empfohlen, sauber): Join-Tabelle**
- `operating_pointset_points(set_id, op_id, order_index)`
- stabile Reihenfolge, saubere Referenzintegrität, leichtes Replace/Update.

**Option B (beibehalten list[int], aber technische Schuld)**
- harte Service-Guards + Consistency-Checks
- klare Delete/Replace-Regeln, sonst kaputte Referenzen.

### Alembic
- Migration: `operating_points.aircraft_id` + FK + Index
- Migration: `operating_pointsets.aircraft_id` + FK + Index
- Migration: Join-Tabelle (wenn Option A)
- Kompatibilität: `aircraft_id` zunächst nullable; später tighten.

---

## Service Layer (neu)

### `operating_point_generator_service.py`
`generate_operating_point_set(aircraft_uuid, profile_override=None, replace_existing=False)`

Helper:
- load aircraft + profile defaults
- compute `Vs_clean / Vs_to / Vs_ldg` (benötigt W, S, CLmax, rho(h))
- build OP targets (per OP-Typ)
- **trim solve** (inkl. controls als Entscheidungsvariablen)
- validation + OP-typischer fallback
- persist set + points in einer DB-Transaktion

### AeroSandbox-Checks als Code-Gates (Pflicht)
1) **Deflection-effect test:** gleicher Zustand, `rudder=0` vs `rudder=+5°` → Moment/Kraft muss sich ändern.  
   Quelle: https://github.com/peterdsharpe/AeroSandbox/issues/134
2) **Derivative-reliability gate:** wenn p/q/r-Derivatives genutzt werden → als experimental kennzeichnen oder per Test absichern.  
   Quelle: https://peterdsharpe.github.io/AeroSandbox/CHANGELOG.html

---

## API Endpoints

### Generator Endpoint (v2)
`POST /aircraft/{aircraft_id}/operating-pointsets/generate-default`

Body:
- `replace_existing: bool = false`
- `profile_id_override: Optional[int]`

Response:
- Set-Metadaten + OP-Liste inkl. `status`, `warnings`, `controls`.

### Bestehende CRUD Endpoints
- OP/Set Reads müssen `aircraft_id` filtern:
  - `GET /operating_pointsets?aircraft_id=...`
  - `GET /operating_points?aircraft_id=...` (neu oder integriert)

---

## Data Flow (Generator)

1. Aircraft laden (inkl. flight_profile assignment).
2. Profile laden oder Defaults verwenden.
3. `Vs_clean, Vs_to, Vs_ldg` berechnen.
4. Punkte in fester Reihenfolge erzeugen:
   1. stall_near_clean
   2. takeoff_climb
   3. best_angle_climb_vx
   4. best_rate_climb_vy
   5. cruise
   6. loiter_endurance
   7. max_range
   8. max_level_speed
   9. approach_landing
   10. turn_n2 (oder profile target n)
   11. dutch_roll_start
5. Für jeden Punkt:
   - targets definieren
   - trim call (liefert Zustand + controls)
   - validation
   - fallback chain (OP-abhängig)
   - normalized output (SI + controls)
6. Persistierung in einer DB-Transaktion:
   - OP rows
   - OP set row + relation (Join-Tabelle empfohlen)
7. Response: Set + OP-Metadaten + Warnungen.

---

## Failure Modes & Handling
- Backend calc/trim Funktion fehlt:
  - semantische Ersatzfunktion verwenden
  - als `NOT_TRIMMED` speichern, Pipeline nicht abbrechen
- Einzelner OP Soft-Fail:
  - markiert speichern (`NOT_TRIMMED` + warnings), Rest läuft weiter
- Kompletter DB-Fehler:
  - rollback, 500
- Aircraft/Profile not found:
  - 404
- Invalid profile constraints:
  - 422

---

## Tests (pytest)

### Schema Tests
- alpha ist Liste Länge 1
- controls Feld vorhanden (bei TRIMMED befüllt)
- unit consistency in descriptions/validation

### Service Unit Tests
- generator nutzt assigned profile
- fallback chain pro OP-Typ
- dutch_roll_start immer vorhanden
- NOT_TRIMMED path: status + warnings + neutrale/definierte defaults
- replace_existing behavior
- alle erzeugten OP rows haben korrektes `aircraft_id`

### DB/Integration
- Migration adds aircraft FK fields
- erzeugte Reihenfolge/Namen stimmen
- Set↔Points Relation ist konsistent und löscht/ersetzt korrekt (insb. bei replace_existing)

### AeroSandbox Integration Tests (kritisch)
- Deflection changes forces/moments in eurer Analyse (Gate)  
  https://github.com/peterdsharpe/AeroSandbox/issues/134
- Derivatives gating (wenn genutzt)  
  https://peterdsharpe.github.io/AeroSandbox/CHANGELOG.html

---

## Rollout
1. Migration deploy (nullable `aircraft_id`)
2. Service + Endpoint deploy
3. Optional backfill script für Legacy OP rows
4. Docs/UI: Generator route aktivieren
5. Monitoring:
   - trim fail rates per OP name
   - NOT_TRIMMED frequency
   - generation duration
   - deflection-effect health check (periodisch)

---

## Assumptions & Defaults
- Trim/back-end APIs sind über bestehende Analysis-Services erreichbar oder adapterbar.
- Initiale Migration hält `aircraft_id` nullable zur Rückwärtskompatibilität.
- Flight-Profile Eingaben können in deg/andere Units vorliegen; Service normalisiert konsequent zu SI.
- Dutch-Roll OP ist statischer Startpunkt (keine Zeitverlaufsdaten im OP-Schema).
- Controls/Deflections werden als Trim-Ergebnis im Operating Point persistiert (reproduzierbare Trims).