# Design: Powertrain Solution-Space Sizing (Phase 1)

**Datum:** 2026-06-13
**Scope:** Backend (neuer Service + Schemas + v2-Endpoint) + Frontend (neuer Tab)
**Epic:** #197 (Powertrain Sizing) · **Status:** Spec — wartet auf Review

## Motivation / Reframing

Das heutige `powertrain_sizing_service` macht einen **Katalog-Sweep**
(Motor × Akku × ESC) und rankt Treffer. Praktisch unbrauchbar: die DB hat
**0 Akkus und 0 ESCs** (5 Motoren, 2 Props), η_prop ist eine Konstante
(0.65), das `propeller`-Antwortfeld bleibt leer.

**Neue Richtung (Phase 1):** Statt aus einem leeren Katalog zu picken,
berechnen wir die **benötigten Komponenten-Specs / den zulässigen
Lösungsraum** aus Mission + Aero. Der Designer bekommt **alle zulässigen
Lösungen** (nicht ein Auto-Optimum), wählt frei per **Spaltenfilter**, und
erhält eine **Spec zum Online-Shoppen** (ESC ≥ A @ V, Akku ≥ mAh @ ≥C,
Motor ≥ W). Konkrete **Katalog-Treffer** werden markiert, wo vorhanden.

## Bestätigte Entscheidungen (mit User)

- **Output:** Anforderungs-Specs / Feasible-Region **plus** Katalog-Treffer-Markierung.
- **Kein Auto-Optimum:** alle zulässigen Lösungen anzeigen, Designer wählt via Spaltenfilter.
- **Hebel:** Zellzahl S (Spannung) primär; Prop = Annahme-Band bis Phase 2.
- **Plot:** Option B — **Kapazität × C-Rate** (Akku-Shopping-Raum), Marker je Zellzahl, Feasible-Floors.
- **Neuer Frontend-Tab.**
- **APC-Prop-Daten = Phase 2** (Ticket #615, wieder offen) — schränkt den Raum später ein.

## Experten-Grundlage (Designpfad)

Synthese aus `rc-aircraft-designer` (Lennon, Roxxy/Multiplex-Fibel,
Drela-Motormodell, UIUC-Prop-DB) und `aircraft-design-scholz`
(Sadraey, Scholz):

1. **Invarianten** aus Mission+Aero (Polare → `P_req(V)`):
   - `P_reise` (elektrisch) → dimensioniert **Energie/Wh**.
   - `P_top` (bei V_top) → dimensioniert **Peak-Leistung → Motor/ESC/C-Rate**.
   - Endurance-FoM `C_L^{1.5}/C_D` bei `V_mp`; Range-FoM `L/D` bei `V_md`.
2. **Prop ist der Anker** (Ø aus Freigang/Tip-Mach ≤ 0.5; Steigung aus
   Missions-P/D-Tabelle) — Phase 1 als Annahme-Band.
3. **Zellzahl S wählen** (mehr S → weniger Strom, da `P=V·I`).
4. **Abgeleitet:** `KV = RPM_ziel/(V·0.85)`; Akku `mAh = E/V`,
   `C = I_peak/Kapazität`; ESC `I ≥ 1.25–1.5 × I_peak`.

**Echte Freiheitsgrade:** Prop (Ø×Steigung) + Spannung (S). Rest abgeleitet.
Sadraey bestätigt: 2D-Feasible-Region ist das richtige Mittel für einen
unterbestimmten Antrieb; der Akku ist selbst ein 2D-Trade (Wh × C-Rate).

## Physik-/Rechenmodell (Phase 1)

Einheiten: SI intern (m, m/s, W, J); UI zeigt mAh/Wh/A/V.

**Invarianten (aus Mission+Aero, gh-924 single source of truth):**
- `C_L(V) = 2·m·g / (ρ·V²·S_ref)`; `C_D = c_d0 + C_L²/(π·e·AR)`.
- `P_aero(V) = ½·ρ·V³·S_ref·C_D`.
- `P_elec(V) = P_aero(V) / (η_prop·η_motor·η_esc)`.
- `P_reise = P_elec(V_reise)`, `P_top = P_elec(V_top)` (Peak).
- Energie `E = P_reise · t_ziel / DoD` [Wh].

**Pro Zellzahl S (über η_prop-Band [η_lo, η_hi]):**
- `V_nom = S · 3.7`, `V_sag = S · 3.5` (Last).
- `I_peak = P_top / (V_sag · η_motor · η_esc)`.
- `Kapazität_min = E / V_nom · 1000` [mAh].
- `C_min = I_peak / (Kapazität_min/1000)`.
- `ESC_min = I_peak · ESC_marge` (default 1.4).
- `Motor_min = P_top` (Burst); Continuous ≈ `P_reise`.
- `KV ≈ RPM_ziel / (V_nom · 0.85)` (RPM_ziel aus Prop-Annahme + V_top/Pitch).
- η_prop-Band ⇒ jede Größe wird ein **Intervall** (Region statt Punkt).

**Feasible-Floors im (Kapazität, C)-Plot:**
- vertikal: `Kapazität ≥ Kapazität_min` (Energie).
- Kurve: `C ≥ C_min(Kapazität) = I_peak/(Kapazität/1000)` (Peak-Strom).
- Region offen nach ↗ („mehr mAh / mehr C schadet nicht").

**Default-Annahmen (justierbar im UI):**
- Zellzahl-Liste: `[2S, 3S, 4S, 6S]` (konfigurierbar).
- η_prop-Band `[0.65, 0.78]`, η_motor `0.85`, η_esc `0.94`.
- DoD `0.80`; ESC-Marge `1.4×`; C-Marge `1.25×`; Last-RPM-Faktor `0.85`.
- Prop-P/D nach Missionstyp (3D 0.5 · Trainer 0.6–0.7 · Segler 0.7–0.9 · Speed 1.0).

## Architektur

### Backend (layered, python-conventions)
- **`app/services/powertrain_solution_space_service.py`** (neu):
  - liest Mission+Aero aus `assumption_computation_context` (gh-924) +
    Design-Assumptions (mass, V-Werte, t_ziel); kein eigener 4. cd0/e-Pfad.
  - rechnet Invarianten + pro-Zellzahl-Ableitung + Feasible-Floors.
  - markiert Katalog-Treffer: query Motoren/Props/(Akku/ESC) aus `components`
    und matcht gegen die berechneten Mindest-Specs.
  - reines Python (keine CadQuery/AeroSandbox-Importe) → schnelle Fast-Tier-Tests.
- **`app/schemas/powertrain_solution_space.py`** (neu): `SolutionRow`,
  `FeasibleRegion`, `ShoppingSpec`, `PowertrainSolutionSpaceResponse`,
  `SolutionSpaceAssumptions` (Request/Override).
- **v2-Endpoint** `GET /aeroplanes/{id}/powertrain/solution-space`
  (+ optionale Query/Body-Overrides für Annahmen). Dünn, delegiert an Service.
- Der alte `powertrain_sizing_service` (Katalog-Sweep) **bleibt** vorerst;
  der neue Tab nutzt den Lösungsraum-Service. Spätere Ablösung separat.

### Frontend (Next App Router, neuer Tab)
- Neuer Tab „Powertrain" im Component/Analysis-Bereich (analog vorhandener Tabs).
- **Plotly-Region** (Kapazität × C, Metren-/SI-Konvention der Achsen-Daten):
  Feasible-Region schattiert, Marker je Zellzahl, Floors.
- **Filterbare Lösungstabelle** (Spalten S/V/Motor-W/Peak-A/ESC-A/mAh/min-C/Wh/Masse/Katalog),
  Spaltenfilter (numerische Schwellen + „nur Katalog-Treffer").
- **Annahmen-Controls** (η-Band, DoD, Margen, Zellzahl-Liste, Prop-P/D).
- **Spec-Zeile** für die gewählte/markierte Zeile.
- `useSWR` gegen den neuen Endpoint; English-only UI (Quality/Powertrain-Terme).

## Fehlerfälle / Design-Warnungen
- Fehlt Mission/Aero im Kontext (kein Recompute) → Design-Warnung + sichtbare
  Annahme-Defaults (konsistent mit gh-956: nicht still defaulten).
- `e`/`cd0` aus dem Kontext lesen (gh-924); fehlt's → warnen, nicht still 0.8.
- Unphysische Eingaben (V_top ≤ V_reise, t ≤ 0) → klare Validierungsfehler.

## Tests
- **Backend (pytest, fast tier, kein Aero-Import):** Invarianten-Rechnung
  gegen Handrechnung; pro-Zellzahl-Ableitung (mehr S → weniger I_peak, weniger
  mAh, gleiche Wh); Feasible-Floors; Katalog-Match (Motor vorhanden → ✓,
  Akku/ESC fehlen → kein Treffer); Warnung bei fehlendem Kontext.
- **Frontend (vitest, Node 22):** Tabelle rendert Zeilen je Zellzahl;
  Spaltenfilter reduziert Zeilen; Spec-Zeile spiegelt Auswahl; Plot-Komponente
  rendert Region (Daten-Props), Layout in Playwright verifizieren (Memory:
  className-only reicht nicht).
- Coverage ≥ 80 % auf neuem Code (Service ist reines Python → CI-Fast-Tier deckt ab).

## Ticket-Decomposition (unter Epic #197)
1. **Backend:** Solution-Space-Service + Schemas + v2-Endpoint (+ Katalog-Match).
2. **Frontend:** neuer Powertrain-Tab — Lösungstabelle + Spaltenfilter + Annahmen-Controls + Spec-Zeile.
3. **Frontend:** Feasible-Region-Plot (Plotly, Kapazität×C) + Verknüpfung mit Tabellen-Auswahl.
4. (vorhanden) **#615** — APC-Prop-Performance-Modell (Phase 2): schnürt den Raum ein (η(J), RPM, Strom).

Reihenfolge: 1 → (2 ‖ 3) → später 4.

## Out of Scope (Phase 1)
- APC-Datensatz / Prop-Performance-Modell (#615, Phase 2).
- Statik-Schub / Startstrecke; Steig-/Manöver-Constraints über V_top hinaus.
- Ablösung/Entfernen des alten Katalog-Sweep-Service.
- Server-seitige Persistenz der gewählten Lösung (zunächst nur Anzeige).
- Powertrain-Default-Warnungen aus #960 (separat, aber kompatibel).
