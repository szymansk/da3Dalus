# Feature-Inventar (Quelle fürs Feature-Dashboard)

Stand: autonomer Kampagnen-Lauf. 5 Haupt-Tabs + Subsysteme. ⭐ = hat Plotly/3D-Visualisierung (Screenshot-wert).

## Haupt-Tabs (workbench-Schritte)
1. **Mission** (`/workbench/mission`) — Missionsziele + 7-Achsen-Compliance-Radar ⭐. `mission_objective_service`, `mission_kpi_service`; `MissionCompliancePanel`/`MissionRadarChart`.
2. **Construction** (`/workbench`, `/workbench/airfoil-preview`) — Wing/Fuselage-Editor, 3D-Wireframe ⭐ + Stabilitäts-Overlay; Airfoil-Low-Re-Suitability (3 Lesarten) ⭐. `wing_service`, `fuselage_service`, `airfoil_low_re_service`, `suitability_service`; `AeroplaneTree`, `WingOutlineViewer`, `AirfoilPreviewViewerPanel`.
3. **Analysis** (`/workbench/analysis`) — Polaren, Stabilität, Operating-Points, Trefftz, Streamlines, V-n-Envelope, Sizing ⭐⭐. `analysis_service`, `operating_point_generator_service`, `stability_service`, `polar_re_table_service`, `avl_*`; `AnalysisViewerPanel`.
4. **Components** (`/workbench/components`) — Bibliothek (Motoren/Akkus/ESC/Servos/Material/Props) + Construction-Parts-Baum. `component_service`, `construction_part_service`.
5. **Plans** (`/workbench/construction-plans`) — baumbasierte CAD-Automation (Creator-Schritte → STEP/STL), Templates. `construction_plan_service`, `cad_service`.

## Subsysteme / Sizing
- **Antriebsstrang/Powertrain-Sizing** — `powertrain_sizing_service` `/powertrain/sizing`; Katalog-Sweep (Motor+ESC+Akku), `CotsPickerDialog`.
- **Endurance/Range (elektrisch)** — `endurance_service` `/endurance`; `EnduranceCard`.
- **Matching-Chart (T/W–W/S)** ⭐ — `matching_chart_service`; `MatchingChartTab` (ziehbarer Designpunkt).
- **Field-Lengths (TO/LDG)** — `field_length_service` (Roskam + RC-Modi hand_launch/bungee/belly_land).
- **Loading-Scenarios + CG-Envelope** ⭐ — `loading_scenario_service`.
- **Tail-Sizing (V_H/V_V)** — `tail_sizing_service`.
- **Design-Assumptions + computation_context** — `assumption_compute_service` (Polar-Fit, MAC, S_ref, Oswald, v_stall, v_md, v_min_sink, mass…); CALCULATED/ESTIMATED-Toggle.
- **OpenVSP-Import** — `openvsp_import_service` (Geometrie + Masse).
- **CAD/3D-Export** ⭐ — STEP/STL/Tessellation; `cad_service` (ProcessPool/OCCT), 20+ Creators.

## Dashboard-Tabs (geplant)
Je Feature-Bereich ein Tab mit: Kurzbeschreibung (was es dem Nutzer bringt) + Smoke-Screenshot + Status. Beispiel-Tab „Auslegung des Antriebsstrangs" (Powertrain-Sizing). Diese-Session-Fokus: **Airfoil-Suitability**-Suite (Low-Re-Scoring, 3 Lesarten, Familien inkl. reflexed, Filter, Speed-Polare, Welt-AoA).
