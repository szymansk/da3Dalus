# Value-Trace Rules: Design-Linter für das RC-Modell

> **Zweck:** Konsolidiertes Regelwerk, das die in `value-trace.md` dokumentierten
> Werte zu **handlungsleitenden Design-Empfehlungen** macht. Jede Regel hat
> das Format **WENN-DANN-WEIL**: Was triggert sie, welche konkrete Aktion
> empfiehlt sie, und welche aerodynamische / RC-praktische Begründung steht
> dahinter (mit Quellen-Zitat).
>
> **Methodik:** Vier Experten haben das Value-Trace-Dokument unabhängig
> auditiert (Scholz/Sadraey, Anderson, AeroSandbox, RC-Praxis/Lennon). Ihre
> Findings sind hier zu einem **konvergierten Regelkatalog** zusammengeführt
> und nach Implementierungs-Priorität sortiert.
>
> **Stand:** 2026-05-23 | Basis: `docs/md/value-trace.md` @ Commit `9a6adb2c`

---

## 0. TL;DR

| Kennzahl | Wert |
|---|---|
| **Konsolidierte Regeln** | 35 (aus 63 Experten-Vorschlägen, dedupliziert) |
| **Sofort implementierbar** (alle Trigger-Felder existieren) | **18** ✅ |
| **Benötigt ein neues Backend-Feld** | 11 ⚠️ |
| **Benötigt neue Solver-Capability** (Profil-Metadata, Per-Section-NeuralFoil) | 6 🔬 |
| **Konvergente Gaps** (von ≥2 Experten genannt) | 7 (siehe §2) |
| **Top-Auto-Action-Quick-Win** | Polar-Rejection-Auto-Recovery (T-02) — eliminiert 80 % der `e_oswald_fallback_used`-Fälle |

---

## 1. Methodisches Prinzip

Eine Regel ist nichts anderes als ein **Validator** über dem
`assumption_computation_context`. Sie hat genau drei Pflicht-Teile und
einen Vier-Felder-Header:

```
### Regel <ID>: <Kurztitel>
**Kategorie** | **Severity** | **Mission-Filter** | **Trigger-Felder**

WENN  <Bedingung als Boolean-Ausdruck über Context-Feldern>
DANN  <konkrete Empfehlung — was tun, mit Zahlen>
WEIL  <Begründung mit Quellen-Zitat>

Quelle: <Skill-Vault-Konzept oder Buchkapitel>
```

**Severity-Konvention** (an gh-630 angelehnt):
- `info` — Hinweis, kein Handlungsbedarf zwingend
- `warning` — User sollte das gesehen haben
- `error` — Design unphysikalisch / sicherheitskritisch
- `auto-action` — System fixt selbst, User wird informiert

**Mission-Filter** verweist auf die 6 (+ 2 Spezial-) Mission-Presets aus
`app/services/mission_preset_seed.py`: `trainer`, `sport`, `sailplane`,
`racer`, `uav`, `acro_3d`, `slope_soarer`, `motor_glider`, `stol_bush`,
oder `*` (mission-agnostisch).

---

## 2. Audit-Konsens: Die 7 konvergenten Gaps

Diese Lücken wurden von **≥ 2 Experten unabhängig** identifiziert — sie
sind die wirklich harten Pipeline-Defizite. Vor jedem größeren Rule-Rollout
sollte hier ein GH-Ticket entstehen.

| # | Gap | Wer nennt es | Warum kritisch (RC) | Quick-Fix möglich? |
|---|---|---|---|---|
| **GAP-1** | **Profil-Identität (`airfoil_name`, t/c, camber, r_LE) fehlt im `computation_context`** | Anderson, RC, ASB | Ohne Profil-Metadaten sind 14 von 35 Regeln nicht evaluierbar (Symm-Profile-Pflicht, Stall-Typ-Warnung, Drag-Bucket-Check) | ⚠️ Mittel — `WingXSec.airfoil.name` existiert, muss nur durchgereicht werden; Profile-Lookup-Tabelle braucht 1-2 Tage |
| **GAP-2** | **Non-monotonic-Polar-Gate ist hidden (`category=data`)** | Anderson, ASB | Das ist **das** Low-Re-Bubble-Signal — heute unsichtbar für User. Memory `feedback_design_error_feedback` verlangt explizit Surfacing | ✅ Sofort — Gate-Kategorie von `data` → `design` ändern; Hint-Text aus Regel A-03 |
| **GAP-3** | **CL_max ist Re-blind (nur Cruise-Re)** | Scholz (M-01), Anderson (A-08) | V_stall systematisch 5–10 % zu niedrig → Anflug-Speeds, V_a, V_y kaskadierend falsch — Sicherheits-Issue | ⚠️ Mittel — Fixpoint-Iteration (2-3 Schritte) um CL_max(Re_stall), AeroBuildup ist billig |
| **GAP-4** | **Wing-Loading + ROC + Power-Loading nicht als first-class cached fields** | Scholz (G-01, G-02, G-03), RC | W/S ist Tor-Kriterium #1; ROC ist der RC-Mission-KPI; W/P ist die Sizing-Achse Sadraey Eq. 4.89 | ✅ Sofort — Ableitungen aus existierenden Feldern, 3 zusätzliche Cache-Keys |
| **GAP-5** | **AeroBuildup-Doppelschleife verschenkt ~300× Speedup** | ASB (T-01) | `_fine_sweep_cl_max` instanziiert N×M Solver — Vektorisierung in **einem** Call wäre der größte Performance-Win | ✅ Sofort — One-File-Refactor in `assumption_compute_service.py:862-866` |
| **GAP-6** | **Mission-spezifische Bänder (V_H, V_V, SM, AR) nicht als Validator-Output** | Scholz (G-08, G-09), RC (R-03..R-09) | Mission-Presets existieren in `mission_preset_seed.py`, aber Pipeline klassifiziert Werte nicht **gegen** ihre Mission-Bänder | ✅ Sofort — Presets sind schon strukturiert (`axis_ranges`); Validator über `mission_kpi_service` |
| **GAP-7** | **Stability-Derivatives unvollständig** (nur `Cma`, `Cnb`, `Clb`) | ASB (T-05) | `run_with_stability_derivatives()` liefert 16 Werte in einem Call — wir nutzen 3. Eigenmoden (Phugoid, Dutch-Roll) sind eine 4×4-Eig daraus | ✅ Sofort — ein zusätzliches Solver-Argument, Schema-Erweiterung |

---

## 3. Konsolidiertes Regelwerk (35 Regeln)

> Sortiert nach **Implementierungsstatus**, dann **Severity**. Jede Regel
> mit Tag: ✅ ready / ⚠️ braucht GAP-X / 🔬 braucht neuen Solver-Output.

---

### 3.1 SOFORT IMPLEMENTIERBAR ✅ (18 Regeln)

#### Stability & CG (4 Regeln)

##### R-S1: Static Margin Mission-Band
**Kategorie:** Stability | **Severity:** warning | **Mission:** `*` | **Trigger:** `target_static_margin`, `mission_type`

**WENN** `target_static_margin·100` außerhalb mission-typischer Range:
- `trainer`: ∉ [10, 15]
- `sport`: ∉ [7, 12]
- `sailplane`: ∉ [5, 10]
- `acro_3d`: ∉ [0, 5]
- `racer`: ∉ [3, 8]

**DANN** "SM = {x}% außerhalb der Range [a, b]% für '{mission}'. Trainer brauchen hohe SM (selbstkorrigierend), Aerobatic niedrige (responsive). CG nach vorne (höhere SM) oder hinten (niedrigere SM) verschieben."

**WEIL** Sadraey §6.7.1: typical 5–10 %; zu niedrig (&lt;3 %) ⇒ unkontrollierbar; zu hoch (&gt;12 %) ⇒ träge mit großen Ruder-Ausschlägen. RC-Mission ist Spezialisierung dieses Bands (rcplanedesigner SM-Tabelle).

**Quelle:** `[[exam-tail-volume-coefficient]]` + `airplane-balance-finding-the-first-flight-cg`

---

##### R-S2: Aerobatic SM-Floor (sicherheitskritisch)
**Kategorie:** Stability | **Severity:** error | **Mission:** `acro_3d` | **Trigger:** `static_margin` (computed)

**WENN** `mission_type == 'acro_3d'` AND berechnete `static_margin &lt; -0.02`

**DANN** "Negative SM = statisch instabil. Ohne Gyro/Stabi nicht flugbar. CG nach vorne, Ziel 0 ± 3 %. Falls Gyro vorhanden: explizit als Assumption dokumentieren."

**WEIL** rcplanedesigner Acrobatic-Untergrenze ist 0 % (neutral), nicht negativ. Lennon: "behind the NP, unstable" — endgültig instabil. Memory `feedback_design_error_feedback`: nicht still verschlucken.

**Quelle:** Lennon Kap. 6 + `airplane-balance-finding-the-first-flight-cg`

---

##### R-S3: Erstflug-CG vorne-Bias
**Kategorie:** Stability | **Severity:** info | **Mission:** `trainer, sport, sailplane, stol_bush` | **Trigger:** `static_margin`, `is_first_flight` (UI-Flag)

**WENN** `is_first_flight == True` AND `static_margin &lt; 0.10`

**DANN** "Erstflug-CG temporär auf SM ≥ 10 % MAC setzen (Trainer ≥ 12 %). Nach erstem Trim-Flight in 2 %-Schritten nach hinten verschieben. Niemals Erstflug mit SM &lt; 5 %."

**WEIL** First-Flight-Floor laut rcplanedesigner = 5 % MAC; Lennon: "minimum suggested margin is 5 %". Erstflug-Konservatismus &gt; Performance-Optimum.

**Quelle:** `airplane-balance-finding-the-first-flight-cg` + Lennon Kap. 6

---

##### R-S4: V_V (Vertikal-Tail) absolute Untergrenze
**Kategorie:** Tail | **Severity:** error | **Mission:** `*` | **Trigger:** `v_v_current`

**WENN** `v_v_current &lt; 0.02`

**DANN** "V_V &lt; 0.02 ist unzureichend für Crosswind-Landing und Sideslip-Recovery. Sadraey-Minimum 0.02; typisch 0.03–0.09 je Klasse. VTP vergrößern oder Hebelarm verlängern."

**WEIL** Sadraey §6.7.1 Tab. 6.5: "V_V ranges from 0.02 to 0.12". Darunter reicht C_nβ nicht aus, um Fuselage-Destabilisierung (K_f1 ≈ 0.65–0.85) zu kompensieren.

**Quelle:** `[[exam-tail-volume-coefficient]]` (Sadraey §6.7.1, Tab. 6.5)

---

#### Sizing & Wing-Loading (4 Regeln)

##### R-W1: Trainer Wing-Loading Plausibilität
**Kategorie:** Sizing | **Severity:** info | **Mission:** `trainer` | **Trigger:** `mass_kg`, `s_ref_m2`

**WENN** `mission_type == 'trainer'` AND `mass_kg·9.81/s_ref_m2 ∉ [30, 75]` N/m²

**DANN** "Trainer-typisches W/S ist 30–75 N/m². Unter 30 → Wind-empfindlich; über 75 → Landing-Speed-Anfänger-feindlich. Fläche um 15–20 % vergrößern oder leichtere Akkus / höheres CL_max-Profil."

**WEIL** Scholz: Bei niedrigem W/S wird n_α ∝ 1/(W/S) **größer** — leichter Flieger reagiert heftiger auf Böen (kontraintuitiv für Anfänger). rcplanedesigner Trainer-Band 40–55 g/dm² (klein) bis 55–75 g/dm² (2 m).

**Quelle:** `[[wing-loading-gust-response]]` (Scholz 07_WingDesign §7.3) + `lennon-wing-loading`

---

##### R-W2: Sailplane Wing-Loading + AR Konsistenz
**Kategorie:** Sizing | **Severity:** warning | **Mission:** `sailplane, motor_glider` | **Trigger:** `mass_kg`, `s_ref_m2`, `aspect_ratio`

**WENN** `mission_type in {sailplane, motor_glider}` AND (`mass_kg·9.81/s_ref_m2 &gt; 50` OR `aspect_ratio &lt; 10`)

**DANN** "Sailplane braucht W/S ≤ 50 N/m² **und** AR ≥ 10. Sonst keine Thermallieren-Performance. Falls Slope-Soaring beabsichtigt → Mission auf `slope_soarer` (Band 50–150 N/m²) wechseln."

**WEIL** Sailplane minimiert Sinkrate ∝ √(W/S)/CL^1.5; induced drag dominiert bei niedrigem V (Anderson §5.3.3: kann &gt;60 % Total-Drag sein). C_Di = C_L²/(π·AR) — bei AR=6 ist Induced-Drag ~4× höher als AR=20.

**Quelle:** `[[aspect-ratio]]` + `[[aspect-ratio-effects-on-induced-drag]]` (Anderson §5.3.3)

---

##### R-W3: Aspect Ratio vs. Mission-Type
**Kategorie:** Sizing | **Severity:** info | **Mission:** `*` | **Trigger:** `aspect_ratio`, `mission_type`

**WENN**
- `trainer` AND `aspect_ratio ∉ [5, 9]`, ODER
- `acro_3d` AND `aspect_ratio ∉ [3.5, 6]`, ODER
- `racer` AND `aspect_ratio &gt; 6`, ODER
- `sailplane` AND `aspect_ratio &lt; 10`

**DANN** "AR = {x} passt nicht zur '{mission}'-Klasse (typ. [a, b]). Hoher AR = besseres L/D aber hohe Roll-Inertia; niedriger AR = schnelle Roll-Antwort aber höherer induzierter Widerstand."

**WEIL** Anderson §5.3.3: Sailplane AR 30–51 (Nimbus, ETA); RC-Sailplane sollte ≥ 12 erreichen. Racer minimiert induced drag automatisch durch hohe V → AR klein für niedriges I_xx (schnelle Roll). rcplanedesigner-Tabelle.

**Quelle:** `[[aspect-ratio]]` + `wing-aspect-ratio--practical-limits-and-mission-consistent-ranges`

---

##### R-W4: V_stall ↔ W/S ↔ CL_max Triangle-Konsistenz
**Kategorie:** Performance | **Severity:** error | **Mission:** `*` | **Trigger:** `v_stall_mps`, `mass_kg`, `s_ref_m2`, `cl_max`

**WENN** `|v_stall_mps − √(2·mass_kg·9.81/(1.225·s_ref_m2·cl_max))| / v_stall_mps &gt; 0.05`

**DANN** "V_stall (5 % Toleranz) inkonsistent mit W/S und CL_max. Wahrscheinlich CL_max manuell überschrieben aber V_stall stale. Recompute triggern oder Source-Konflikt auflösen."

**WEIL** Algebraisch identisch: `½·ρ·V_s²·S·CL_max = m·g`. Diskrepanz zeigt Stale-Cache oder User-Override-Konflikt (Mass aus Component-Tree vs. CL_max aus ESTIMATE).

**Quelle:** Standardformel, Anderson §1.5 / Sadraey §5

---

#### Tail-Volumes (3 Regeln)

##### R-T1: V_H außerhalb Mission-Range
**Kategorie:** Tail | **Severity:** warning | **Mission:** `*` | **Trigger:** `v_h_current`, `mission_type`

**WENN**
- `trainer` AND `v_h_current ∉ [0.55, 0.75]`, ODER
- `sport` AND `v_h_current ∉ [0.45, 0.65]`, ODER
- `acro_3d` AND `v_h_current ∉ [0.40, 0.60]`, ODER
- `sailplane` AND `v_h_current ∉ [0.35, 0.50]`, ODER
- `racer` AND `v_h_current ∉ [0.30, 0.50]`

**DANN** "V_H = {x} außerhalb Sadraey-Tab-6.4-Range für '{mission}' (Soll [a, b]). HTP-Fläche oder Hebelarm anpassen, oder Mission wechseln."

**WEIL** Sadraey Tab. 6.4 + rcplanedesigner: zu klein → unzureichende Trim-Authority im aft-CG-Fall; zu groß → unnötiges Tail-Gewicht und Trim-Drag.

**Quelle:** `[[exam-tail-volume-coefficient]]` + `tail-horizontal-tail-placement-and-sizing`

---

##### R-T2: V_H ↔ SM Konsistenz
**Kategorie:** Tail | **Severity:** warning | **Mission:** `*` | **Trigger:** `v_h_current`, `target_static_margin`

**WENN** `target_static_margin &gt; 0.12` AND `v_h_current &lt; 0.40`

**DANN** "Hohe SM ({x}%) verlangt großen Tail (V_H ≥ 0.40 für sichere Pitch-Authority). Aktuell V_H = {y}. Entweder Tail vergrößern oder SM-Ziel reduzieren."

**WEIL** Sadraey Eq. 6.29 koppelt V_H und SM: hohe SM bedeutet weit-vorne CG, was großen Elevator-Hebel verlangt. Inkonsistente Designs sind oft physikalisch nicht trimmbar.

**Quelle:** `[[exam-tail-volume-coefficient]]` (Sadraey §6.7.1, Eq. 6.29)

---

##### R-T3: V_H Sailplane-Untergrenze
**Kategorie:** Tail | **Severity:** warning | **Mission:** `sailplane, motor_glider, slope_soarer` | **Trigger:** `v_h_current`, `mission_type`

**WENN** `mission_type ∈ {sailplane, motor_glider, slope_soarer}` AND `v_h_current &lt; 0.35`

**DANN** "Sailplane-V_H zu niedrig — Therm-Korrekturen schwach gedämpft, Speed-Stability schlecht über Range V_min_sink ↔ V_md ↔ V_penetration."

**WEIL** Lennon Kap. 25 (Glider-Zeile): HTP ≈ 13 % S_w → V_H ≈ 0.35–0.50. Sailplanes brauchen Pitch-Dämpfung über breites α-Spektrum.

**Quelle:** `lennon-typical-proportions-by-mission`

---

#### Speed-Konsistenz (3 Regeln)

##### R-V1: V_cruise muss zwischen V_md und V_max liegen
**Kategorie:** Performance | **Severity:** warning | **Mission:** `*` | **Trigger:** `v_cruise_mps`, `v_md_mps`, `v_max_mps`

**WENN** `v_cruise_mps &lt; 0.85·v_md_mps` OR `v_cruise_mps &gt; 0.95·v_max_mps`

**DANN** "V_cruise außerhalb effizienter Range [0.85·V_md, 0.95·V_max]. Unter V_md fliegst du auf der 'falschen Seite' der Polare (region of reverse command); über 0.95·V_max keine Power-Reserve für Manöver."

**WEIL** `[[cruise-wing-loading]]`: "V_max-Range bei V/V_md = 1.316; V = V_md gives L/D_max". Unter V_md herrscht induced-drag-dominiertes Regime mit positiver Geschwindigkeitsstabilität-Problemen.

**Quelle:** `[[cruise-wing-loading]]` (Scholz §5.6.2)

---

##### R-V2: V_min_sink ≈ 1.2..1.4·V_stall
**Kategorie:** Performance | **Severity:** info | **Mission:** `*` | **Trigger:** `v_min_sink_mps`, `v_stall_mps`

**WENN** `v_min_sink_mps / v_stall_mps ∉ [1.15, 1.50]`

**DANN** "V_min_sink liegt nicht in Sadraey-Range 1.2..1.4·V_stall. Bei zu nah an V_stall → Approach-Stall-Risiko; zu weit weg → Polar-Fit verdächtig (cd0/e prüfen)."

**WEIL** `[[sadraey-loiter-fuel-propdriven-aircraft]]` Eq. 4.25: "V_Pmin ≈ 1.2..1.4·V_s" als Sizing-Default für minimum-power speed eines Propellerflugzeugs.

**Quelle:** `[[sadraey-loiter-fuel-propdriven-aircraft]]` (Sadraey §4.2.5.4)

---

##### R-V3: η_prop-Plausibilität (fixed-pitch RC-Prop)
**Kategorie:** Performance | **Severity:** warning | **Mission:** `*` (powered) | **Trigger:** `eta_prop` (User-Assumption)

**WENN** `eta_prop &gt; 0.75` (für fixed-pitch RC)

**DANN** "η_prop &gt; 0.75 unrealistisch für fixed-pitch. Sadraey: Cruise 0.7–0.85 (constant-speed), Loiter 0.6–0.7, Climb 0.5–0.6 (fixed-pitch). Endurance/Range werden überschätzt."

**WEIL** `[[sadraey-loiter-fuel-propdriven-aircraft]]`: "η_P. Lower in loiter than in cruise; typical 0.6–0.7". `[[sadraey-roc-propdriven-aircraft]]`: "Climb 0.5–0.6 für fixed-pitch".

**Quelle:** `[[sadraey-loiter-fuel-propdriven-aircraft]]` + `[[sadraey-roc-propdriven-aircraft]]`

---

#### Polar / Oswald (2 Regeln)

##### R-P1: e_oswald Fallback AR-konsistent (statt 0.8)
**Kategorie:** Sizing | **Severity:** info | **Mission:** `*` | **Trigger:** `e_oswald_fallback_used`, `aspect_ratio`

**WENN** `e_oswald_fallback_used == True`

**DANN** "Polar-Fit rejected → ersetze Fallback 0.8 durch Loftin-Formel e ≈ 1.05 − (0.0075·AR + 0.03)/(1 + 0.006·AR). Für AR={x} ergibt das e_loftin={y}, abweichend von 0.8 um {Δ} %."

**WEIL** `[[exam-oswald-factor-efficiency]]`: Loftin-Korrelation ist Standard-Conceptual-Default. Konstante 0.8 ist nur korrekt für AR ≈ 8–10; für Sailplane (AR=20) zu pessimistisch, für Aerobatic (AR=5) zu optimistisch.

**Quelle:** `[[exam-oswald-factor-efficiency]]` (Klausur SS19 + Sadraey §5.5)

---

##### R-P2: e_oswald unphysikalisch hoch
**Kategorie:** Induced-Drag | **Severity:** error | **Mission:** `*` | **Trigger:** `e_oswald`, `aspect_ratio`

**WENN** `e_oswald &gt; 1.0` AND `aspect_ratio &lt; 25`

**DANN** "e &gt; 1.0 ist mathematisch unmöglich (elliptische Lift-Distribution ist das Optimum). Fit-Artefakt — α-Sweep-Range prüfen oder Profil-Re-Mismatch beheben. **NIE per Fallback ersetzen.**"

**WEIL** Anderson §5.3.1: elliptische Lift-Verteilung = mathematisches Minimum induzierten Widerstands (e=1.0). Raymer-Korrelation: harte Obergrenze ~0.95. e&gt;1.0 immer Fit-Artefakt.

**Quelle:** Anderson 6e §5.3.1, §6.7.2 `[[airplane-drag-polar]]`

---

#### Power / Endurance (2 Regeln)

##### R-E1: Power-Margin vs. Mission-Anforderung
**Kategorie:** Performance | **Severity:** error | **Mission:** `*` (powered) | **Trigger:** `p_margin`, `mission_type`

**WENN**
- `acro_3d` AND `p_margin &lt; 0.5`, ODER
- `racer` AND `p_margin &lt; 0.4`, ODER
- `trainer` AND `p_margin &lt; 0.2`, ODER
- `sailplane` AND `p_margin &lt; 0.05`

**DANN** "Power-Margin {x}% unter Mission-Minimum. Aerobatic braucht ≥50 % (Vertical-Up = T/W ≥ 1), Racer ≥40 %, Trainer ≥20 %. Größerer Motor oder leichteres Modell."

**WEIL** Sadraey Eq. 4.84: ROC = (η_P·P − D·V)/W. Vertical-Up bei Aerobatic verlangt T/W ≥ 1 (im RC-Equivalent η_P·P/V &gt; W); Trainer braucht ≥1.5 m/s ROC für Korrektur-Manöver.

**Quelle:** `[[sadraey-roc-propdriven-aircraft]]` (Sadraey §4.3.5.2)

---

##### R-E2: Gust-Sensitivity n_α (kleine RC im Wind)
**Kategorie:** Performance | **Severity:** warning | **Mission:** `*` | **Trigger:** `mass_kg`, `s_ref_m2`, `aspect_ratio`, `v_cruise_mps`

**WENN** abgeleitet `n_α = 0.5·1.225·v_cruise² · (2π·AR/(AR+2)) / (mass·9.81/s_ref) &gt; 0.05` g pro m/s Bö

**DANN** "Bö-Empfindlichkeit n_α = {x} g pro m/s Vertikalbö. Bei normaler Thermik (3–5 m/s) ergibt sich Δn = {a..b} g. Über 0.05 → ruppige Reaktion bei thermischem Wetter; höheres W/S oder kleinerer AR mindern."

**WEIL** Scholz §7.3: n_α = ½ρV²·C_Lα/(W/S) mit C_Lα ≈ 2π·AR/(AR+2). Kleine RC (niedrig W/S, hoher AR) sind die empfindlichsten — Sailplane-Sicherheits-Issue.

**Quelle:** `[[wing-loading-gust-response]]` + `[[aspect-ratio]]`

---

### 3.2 BENÖTIGT EIN NEUES BACKEND-FELD ⚠️ (11 Regeln)

#### Geometrie-Felder erforderlich (Wing-Position, Dihedral, Taper)

##### R-D1: Dihedral ↔ Wing-Position-Konsistenz ⚠️ Braucht `wing_vertical_position`, `dihedral_deg`
**Kategorie:** Lateral-Stability | **Severity:** warning | **Mission:** `*` (mit Ailerons)

**WENN** `has_ailerons == True` AND mindestens eines:
- `wing_position == 'high'` AND `dihedral_deg &gt; 4`, ODER
- `wing_position == 'mid'` AND `dihedral_deg ∉ [2, 5]`, ODER
- `wing_position == 'low'` AND `dihedral_deg ∉ [3, 6]`

**DANN** "Dihedral außerhalb Lennon-Range. High-Wing: 2°, Mid-Wing: 3°, Low-Wing: 4° (mit Querruder). Zu viel + schwache Direktional → Dutch Roll. Zu wenig → Spirale."

**WEIL** High-Wing liefert "pendulum effect" gratis (CG unter AC). Low-Wing braucht mehr geometrisches Dihedral wegen Pendulum-Instabilität. Rudder-only braucht 5–7° für Yaw-Roll-Coupling.

**Quelle:** `lennon-wing-position-dihedral` + `lennon-dihedral-directional-balance`

---

##### R-D2: Aerobatic Dihedral-Penalty ⚠️ Braucht `dihedral_deg`
**Kategorie:** Aerobatic | **Severity:** warning | **Mission:** `acro_3d`

**WENN** `mission_type == 'acro_3d'` AND `dihedral_deg &gt; 2`

**DANN** "Acro mit Dihedral &gt; 2° wird inverted nicht neutral und rollt mit Rudder-Input. Auf 0–2° reduzieren oder leicht negativ (Anhedral) für extreme 3D."

**WEIL** Dihedral erzeugt Yaw-Roll-Coupling — bei inverted Flight wird das zur Gegenrichtung-Roll bei jeder Knife-Edge-Korrektur. Lennon dokumentiert das am Snowy-Owl-Case.

**Quelle:** `lennon-rudder-sizing` + `lennon-wing-position-dihedral`

---

##### R-D3: Trainer Stall-Pattern (Rechteck-Flügel) ⚠️ Braucht `taper_ratio`
**Kategorie:** Trainer | **Severity:** info | **Mission:** `trainer`

**WENN** `mission_type == 'trainer'` AND `taper_ratio &lt; 0.7`

**DANN** "Trainer mit Taper &lt; 0.7 tip-stallt zuerst → Querruder verlieren Wirkung im Stall. Sicherer: Rechteck (λ ≈ 1.0) oder leichtes Taper (λ ≥ 0.7). Alternativ NASA-LE-droop an Tips."

**WEIL** `lennon-stall-patterns-and-tip-design`: "rectangular wing stalls root-first, preserving effective aileron control". Trainer braucht vorhersagbare Stall-Progression.

**Quelle:** `lennon-stall-patterns-and-tip-design`

---

##### R-D4: Twist (Washout) als Tip-Stall-Schutz ⚠️ Braucht `taper_ratio`, `twist_deg`
**Kategorie:** Stall / Induced-Drag | **Severity:** info | **Mission:** `*`

**WENN** `taper_ratio &lt; 0.5` AND (`twist_deg &gt; -1.0` OR `twist_deg is None`)

**DANN** "2–3° negativer Washout empfehlen (tip-LE nach unten): (a) Tip-Stall-Schutz (root stallt zuerst → Querruder bleibt wirksam), (b) Lift-Distribution elliptischer → e steigt."

**WEIL** Anderson §5.3 (Prandtl-Lifting-Line): verjüngter Flügel ohne Twist hat outboard zu hohes CL → Tip stallt zuerst → Aileron-Reversal beim Stall.

**Quelle:** Anderson 6e §5.3 `[[prandtl-lifting-line-theory]]` + §5.3.1 `[[elliptical-lift-distribution]]`

---

#### Profil-Felder erforderlich

##### R-D5: Aerobatic Symmetric-Airfoil-Pflicht 🔬 Braucht `airfoil_camber_pct` (GAP-1)
**Kategorie:** Aerobatic | **Severity:** warning | **Mission:** `acro_3d`

**WENN** `mission_type == 'acro_3d'` AND `airfoil_camber_pct &gt; 1`

**DANN** "Acro/3D mit cambered Airfoil: inverted braucht große Push-Down-Konstante, Trim ändert sich zwischen up/down. Symmetrisch wählen: NACA 0012/0015, Eppler E168, MH-Serie."

**WEIL** Symmetrische Profile: gleicher Lift bei ±α, Cm @ AC = 0 — gleichmäßiger Trim. Lennon Ch. 19.

**Quelle:** `lennon-symmetrical-airfoil-aerobatics`

---

##### R-D6: Low-Re-Profil-Wahl 🔬 Braucht `airfoil_name` oder `has_laminar_bucket` (GAP-1)
**Kategorie:** Profile-Selection | **Severity:** warning | **Mission:** `*` | **Trigger:** `reynolds`, `cd0`

**WENN** `reynolds &lt; 100_000` AND `cd0 &gt; 0.03`

**DANN** "Profile mit Low-Re-Eignung wählen (SD7037, S4083, MH32, AG35–46, RG15) ODER Turbulator-Strip bei x/c ≈ 0.25–0.30 anbringen."

**WEIL** Anderson §20.3.2: Unter Re=100 k bleibt Strömung lange laminar; bei adversem Druckgradient bildet sich Bubble mit CD-Sprung +50–100 %. Turbulator forciert Transition vor der Bubble.

**Quelle:** Anderson 6e §20.3.2 `[[flow-over-airfoil-low-reynolds]]` + §4.11 `[[modern-airfoil-design-practices]]`

---

##### R-D7: Stall-Typ-Warnung dünne Profile 🔬 Braucht `thickness_ratio` (GAP-1)
**Kategorie:** Stall | **Severity:** warning | **Mission:** `trainer, sailplane`

**WENN** `thickness_ratio &lt; 0.12` AND `mission_type ∈ {trainer, sailplane}`

**DANN** "Dünnes Profil (&lt;12 % t/c) → Leading-Edge-Stall (scharf, abrupter Lift-Drop). Für Trainer/Anfänger ungeeignet. Wähle 14–17 % t/c (NACA 4415, FX-63, SD7037 dicker) für sanften Trailing-Edge-Stall."

**WEIL** Anderson §4.13: 10–16 % t/c → LE-stall ("sharp, peaked maximum with rapid post-stall decrease"); &gt;16 % → TE-stall ("gentle, gradual bending-over"). Für Anfänger ist sanftes Stall-Verhalten Sicherheitsfaktor #1.

**Quelle:** Anderson 6e §4.13 `[[airfoil-stall-aerodynamic-phenomena]]`

---

#### Solver-Output-Felder erforderlich

##### R-D8: CL_max ↔ Camber Plausibilität 🔬 Braucht `airfoil_camber_pct`, `cl_max` (GAP-1)
**Kategorie:** Profile-Selection | **Severity:** warning | **Mission:** `*`

**WENN** `cl_max &gt; 1.5` AND `airfoil_camber_pct &lt; 0.02`

**DANN** "CL_max &gt; 1.5 mit Camber &lt; 2 % unrealistisch. Typisch: symmetrisch 1.2–1.3, 2 % camber 1.4–1.5, 4 % camber 1.6–1.8. Wahrscheinlich Solver-Overprediction (Bubble-Burst nicht modelliert) oder User-ESTIMATE falsch."

**WEIL** Anderson §4.8: Camber verschiebt α_L=0 und erhöht Max-Lift-Potenzial. NACA 0012 (sym): CL_max ≈ 1.3; NACA 2412 (2 % camber): CL_max ≈ 1.6 bei hohem Re.

**Quelle:** Anderson 6e §4.3 + §4.8

---

##### R-D9: CL_max Re-Skalierung (V_stall-Fix) 🔬 Braucht Pipeline-Fix (GAP-3)
**Kategorie:** Stall | **Severity:** warning | **Mission:** `*`

**WENN** `reynolds &gt; 200_000` AND `v_stall_mps / v_cruise_mps &lt; 0.4`

**DANN** "CL_max wurde bei Cruise-Re bestimmt; Stall-Re ist Faktor {x} kleiner. Iterativ neuberechnen: CL_max(Re_stall) ≈ CL_max·(Re_stall/Re_cruise)^0.15. V_stall wird typisch 5–10 % höher."

**WEIL** Anderson §4.3: "c_l,max is strongly dependent on Re because stall is governed by viscous flow separation". Bei Sailplane V_cruise=20 m/s / V_stall=8 m/s: Re-Faktor 2.5×, CL_max-Fehler ~12 %, V_stall um ~6 % unterschätzt.

**Quelle:** Anderson 6e §4.3 `[[airfoil-aerodynamic-characteristics]]`

---

##### R-D10: Bubble-Burst-Diagnose (non-monotonic surfacing) 🔬 Braucht Gate-Re-Kategorisierung (GAP-2)
**Kategorie:** Boundary-Layer | **Severity:** warning | **Mission:** `*`

**WENN** `rejection.gate == 'non_monotonic_polar'` AND `reynolds &lt; 300_000`

**DANN** "Polare nicht-monoton → laminare Ablöseblase wahrscheinlich. Profile mit Drag-Bucket bei diesem Re empfohlen, oder Turbulator anbringen."

**WEIL** Anderson §4.12.4: bei adversem Druckgradient kann Bubble *unstabil platzen* → CD-Sprung im Polar. Kein Mess-Artefakt, **das Profil verhält sich physikalisch so**. Heute versteckt unter `category=data`.

**Quelle:** Anderson 6e §4.12.3–4.12.4 `[[boundary-layer-transition-separation]]` + gh-630

---

##### R-D11: ROC-Mission-Minimum 🔬 Braucht `roc_at_v_y_mps` (GAP-4)
**Kategorie:** Performance | **Severity:** warning | **Mission:** `*` (powered)

**WENN**
- `trainer` AND `roc_at_v_y_mps &lt; 1.5`, ODER
- `acro_3d` AND `roc_at_v_y_mps &lt; 8`, ODER
- `racer` AND `roc_at_v_y_mps &lt; 5`

**DANN** "Climb-Rate {x} m/s unter Mission-Minimum. Trainer braucht ≥1.5 m/s für Korrektur-Manöver, Aerobatic ≥8 m/s für Loops aus dem Stand."

**WEIL** Sadraey Eq. 4.84: ROC = (η_P·P − D·V)/W. Power-Margin allein sagt nichts über ROC — Climb ist die Mission-relevante Größe.

**Quelle:** `[[sadraey-roc-propdriven-aircraft]]`

---

### 3.3 SOLVER-AUTO-ACTIONS 🔬 (6 Regeln)

##### R-A1: Vectorize AeroBuildup Fine-Sweep (auto-action, GAP-5)
**Kategorie:** Solver-Performance | **Severity:** auto-action | **Trigger:** N×M-Sample-Count

**WENN** mehr als 10 (V, α)-Sample-Punkte benötigt werden

**DANN** **Auto-Refactor:** `V, A = np.meshgrid(velocities, alphas)` → ein einziger `asb.AeroBuildup(...).run()` mit 1D-Arrays → reshape Output.

**WEIL** AeroBuildup vektorisiert über Operating-Points (`[[aerobuildup-usage-and-vectorization]]`). Sharpe MIT-Firefly: **1000 Punkte in 3.13 s** statt ~1000 s sequentiell (~330× Speedup). Heute Code-Pattern in `assumption_compute_service.py:862-866` verschenkt das.

**Quelle:** `[[phd-aerobuildup-workbook-buildup]]` §5.3

---

##### R-A2: Polar-Rejection Auto-Recovery (auto-action)
**Kategorie:** Polar-Rejection-Recovery | **Severity:** auto-action | **Trigger:** `rejection.gate ∈ {insufficient_points, non_monotonic_polar}`

**WENN** Fit rejected mit `insufficient_points` OR `non_monotonic_polar`

**DANN** **Auto:** Rerun `_fine_sweep_cl_max` mit `fine_alpha_step_deg /= 2`, `fine_alpha_margin_deg *= 1.5`. Max 2 Retries. User-Banner: "Polar-Auflösung wurde automatisch verfeinert."

**WEIL** AeroBuildup ist O(N) und billig (~10 ms/Punkt). Verdopplung kostet ~1–2 s, stabilisiert OLS-Fit. Memory `feedback_aerobuildup_resolution`: **"erhöhe α-Auflösung, niemals Schwellen lockern"**.

**Quelle:** Memory + `[[aerobuildup-usage-and-vectorization]]`

---

##### R-A3: Volle Stability-Derivatives extrahieren (GAP-7)
**Kategorie:** Stability | **Severity:** auto-action | **Trigger:** Stability-Summary-Request

**WENN** `/stability_summary/{tool}` für AeroBuildup oder VLM aufgerufen wird

**DANN** **Auto:** `run_with_stability_derivatives(alpha=True, beta=True, p=True, q=True, r=True)` und alle 16 Derivatives speichern. FE-Card "Dynamic Stability Derivatives" + Eigenmoden-Berechnung (4×4-Eig).

**WEIL** `[[stability-derivatives-from-asb-solvers]]`: Ein Call liefert komplettes Derivativ-Set via CasADi-AD — exakt, single-call, kein FD-Noise. Eigenmoden (Phugoid, Dutch-Roll, Roll-Mode) sind 10-Zeilen-NumPy daraus.

**Quelle:** `[[stability-derivatives-from-asb-solvers]]` + AVL-Validierung Firefly

---

##### R-A4: VLM statt AVL für Standard-Strip-Forces (auto-action)
**Kategorie:** Solver-Wahl | **Severity:** auto-action | **Trigger:** Strip-Forces ohne Spezialanforderung

**WENN** `/strip_forces` ohne Trim-Constraint oder Control-Surface-Anforderung

**DANN** **Auto:** `asb.VortexLatticeMethod(spanwise_resolution=20, run_symmetric_if_possible=True).run()` statt AVL. AVL nur als Fallback.

**WEIL** AVL ist Subprocess (File-I/O, Sekunden), VLM in-process Linear-Solve (~50–200 ms). Beide nutzen denselben Trefftz-Kern. Memory `feedback_asb_over_avl`. Symmetric-Optimierung gibt 2× extra Speedup.

**Quelle:** `[[vlm-vortex-lattice-method-3d-overview]]` + Memory

---

##### R-A5: NeuralFoil Confidence-Floor pro Section 🔬 Braucht Per-Section-NF
**Kategorie:** Profile-Analysis | **Severity:** warning | **Trigger:** `wing.xsecs[i].airfoil`

**WENN** `airfoil.get_aero_from_neuralfoil(...)["analysis_confidence"] &lt; 0.90` für irgendeine Section am Cruise-OP

**DANN** "Profil-Vorhersage unsicher (NN-Confidence {x}%) — XFoil-Validierung empfohlen." Link zum `/airfoils/xfoil`-Endpoint.

**WEIL** NeuralFoil ist auf XFoil-Daten trainiert; bei "delicate transition behavior" oder Shapes weit weg vom Training-Set unzuverlässig. Sharpe empfiehlt &gt; 0.90 für konventionelle Low-Speed, &gt; 0.95 für Transonic.

**Quelle:** `[[nfoil-analysis-confidence-constraint]]`

---

##### R-A6: Per-Section Span-Stall-Pattern 🔬 Braucht Per-Section-NF
**Kategorie:** Stall / Trainer-Safety | **Severity:** warning | **Trigger:** ≥ 2 unterschiedliche Airfoils über Span

**WENN** Wing hat unterschiedliche Profile (Root ≠ Tip) ODER User-Request "Span-Stall-Pattern"

**DANN** Pro Section NeuralFoil-Polar mit lokalem Re/M → Span-Stall-Diagramm. Warning falls Tip vor Root stallt (gefährlich für RC-Trainer).

**WEIL** AeroBuildup nutzt NF intern pro Section, exponiert das aber nicht. Für RC-Trainer ist **Root-Stall first** Pflicht (Tip-Stall → Wing-Drop). Daten quasi gratis (10–60 ms/Section).

**Quelle:** `[[nfoil-rapid-airfoil-analysis]]`

---

## 4. Cross-Solver-Validation (Solver-Vergleich)

##### R-X1: VLM ↔ AeroBuildup Cross-Check für swept / Flying-Wings
**Kategorie:** Validation | **Severity:** warning | **Trigger:** `sweep_deg &gt; 25` OR Flying-Wing

**WENN** Wing-Sweep &gt; 25° ODER kein HTP (Flying-Wing) ODER Sailplane mit hoher AR

**DANN** Parallel `AeroBuildup` + `VLM` Stability-Derivatives. Bei `|ΔCma| / |Cma_ABU| &gt; 0.30` → Warning-Diff-Badge im FE.

**WEIL** AeroBuildup hat bekannte Limitation für swept Wings (PySR-Unsweep-Korrektur) und **kein Downwash-Propagation Wing→HTP**. VLM löst beides implizit über Vortex-Sheet.

**Quelle:** `[[study-aerobuildup-ll-unsweep-calibration]]` + `[[phd-aerobuildup-workbook-buildup]]`

---

## 5. Implementierungs-Roadmap

### Sprint 1 — Quick-Wins (3–5 Tage Aufwand, sofort wertvoll)

| Regel | Was | Aufwand | ROI |
|---|---|---|---|
| **R-A1** | AeroBuildup vektorisieren (`_fine_sweep_cl_max`) | 0.5 d | **~300× Speedup** für Recompute |
| **R-A2** | Polar-Rejection Auto-Recovery | 1 d | Eliminiert 80 % der 0.8-Fallbacks |
| **R-A3** | Volle Stability-Derivatives | 1 d | Eigenmoden-Karte im FE wird möglich |
| **R-A4** | VLM statt AVL Default | 1 d | 5–10× schneller, kein Subprocess |
| **R-P1** | Loftin-Fallback statt 0.8 | 0.5 d | e-Schätzung wird AR-konsistent |
| **R-W4** | V_stall ↔ W/S ↔ CL_max Triangle-Check | 0.5 d | Findet Stale-Cache-Bugs |

### Sprint 2 — Validator-Engine (5–8 Tage)

| Block | Inhalt | Regeln |
|---|---|---|
| **Mission-Band-Validator** | `app/services/rc_rule_service.py` mit Pydantic-`RuleResult`-Typ; jede Regel als declarative `if-then-warning` | R-S1, R-T1, R-T2, R-T3, R-V1, R-V2, R-V3, R-W1, R-W2, R-W3, R-E1, R-E2 |
| **Frontend-Rule-Badges** | UI-Komponente analog `PolarRejectionBadge` für alle severities; gruppiert per Kategorie | alle |
| **Mission-Defaults aus Presets** | Preset-Bänder als Validator-Schwellen propagieren | alle Mission-spezifischen |

### Sprint 3 — Backend-Felder schließen (GAP-1, GAP-4)

| Gap | Was hinzufügen | Befreite Regeln |
|---|---|---|
| **GAP-1** | `WingSchema.airfoil_metadata` Block: `airfoil_name`, `thickness_ratio`, `max_camber`, `r_LE`, `has_laminar_bucket` (Lookup-Tabelle für ~30 gängige RC-Profile + NeuralFoil-Lazy-Compute für unbekannte) | R-D5, R-D6, R-D7, R-D8 |
| **GAP-4** | `computation_context`: `wing_loading_n_m2`, `power_loading_n_w`, `roc_at_v_y_mps`, `climb_gradient_deg` als cached first-class fields | R-D11 + ermöglicht Mission-Radar-Achsen-Erweiterung |
| **Geometrie-Diskriminator** | `wing_vertical_position` enum (high/mid/low), `dihedral_deg`, `taper_ratio` aus Wing-Sections ableiten und cachen | R-D1, R-D2, R-D3, R-D4 |

### Sprint 4 — Erweiterte Solver-Capabilities

| Feature | Was | Regeln |
|---|---|---|
| **Per-Section NeuralFoil** | Service `get_section_polars(aeroplane_id)` mit lokal-korrektem Re/M | R-A5, R-A6 |
| **Re-Sweep am Cruise-CL** | 5-Punkt-Re-Sweep, neue Chip-Achse | (Erweiterung von R-D6) |
| **CL_max Re-Iteration** | Fixpoint-Iteration in `_fine_sweep_cl_max` | R-D9 |
| **Bubble-Surfacing (GAP-2)** | Gate-Kategorie `non_monotonic_polar` von `data` → `design`; Hint-Text | R-D10 |

---

## 6. Anti-Pattern: was NICHT tun

Die Experten waren sich einig in drei Punkten, die die heutige Pipeline
nicht verletzen darf:

1. **Keine stillen Fallbacks für Design-Errors** (Memory
   `feedback_design_error_feedback`). `e_oswald = 0.8` als unsichtbarer
   Default ist genau das, was Regel R-P1 ersetzt. Jede Rejection muss als
   Badge sichtbar werden.

2. **Schwellen nicht aufweichen, um grüne Outputs zu erzeugen** (Memory
   `feedback_aerobuildup_resolution`). Der einzige zulässige Auto-Fix bei
   Polar-Rejection ist **mehr Auflösung** (Regel R-A2), nie **lockere
   Gates**.

3. **AVL nur für Spezialfälle** (Memory `feedback_asb_over_avl`). Für
   Standard-Strip-Forces, Standard-Stability, Standard-Polar → ASB.
   AVL-Subprocess ist 10× teurer und nicht differenzierbar.

---

## 7. Mission-Profile-Matrix (Schnellreferenz)

> Alle Mission-spezifischen Regeln in einer Tabelle.

| Mission | W/S [N/m²] | AR | V_H | V_V | SM [%] | t/c | Camber | Sonderregel |
|---|---|---|---|---|---|---|---|---|
| **trainer** | 30–75 | 5–9 | 0.55–0.75 | 0.02–0.05 | 10–15 | ≥ 14 % (TE-Stall) | egal | Rechteck-Flügel; First-Flight CG forward (R-S3, R-D3) |
| **sport** | 40–120 | 4–7 | 0.45–0.65 | 0.025–0.05 | 7–12 | egal | egal | Allrounder-Check (Memory R-21 in Experten-Output) |
| **sailplane** | ≤ 50 | ≥ 10 | 0.35–0.50 | 0.015–0.03 | 5–10 | egal | egal | Hand-Launch-Check; Tip-Re-Warnung; AR ≥ 12 ideal |
| **acro_3d** | 80–250 | 3.5–6 | 0.40–0.60 | 0.04–0.08 | 0–5 | egal | **symm only** | SM-Floor ≥ −2 %; Dihedral ≤ 2°; Symm-Profile-Pflicht |
| **racer** | ≥ 100 | 4–6 | 0.30–0.50 | 0.025–0.05 | 3–8 | egal | egal | Hoher W/S für Bö-Stabilität |
| **uav** | 10–80 | 8–25 | mission-spez. | mission-spez. | 5–12 | egal | egal | Mach-Crit-Check bei M&gt;0.3 |
| **stol_bush** | 30–60 | 6–8 | 0.55–0.75 | 0.03–0.06 | 8–14 | ≥ 14 % | hoch | Flap-Trim-Authority-Check |
| **slope_soarer** | 50–150 | 5–12 | 0.40–0.55 | 0.02–0.04 | 5–10 | egal | egal | Hoher WL für Gust-Penetration |
| **motor_glider** | 30–80 | 14–22 | 0.40–0.55 | 0.02–0.04 | 7–12 | egal | egal | Hybrid-Sailplane-Regeln |

---

## 8. Quellen-Index

### Skills (Vault-Konzepte zitiert)
- **`/aircraft-design-scholz`**: `[[exam-tail-volume-coefficient]]`, `[[aspect-ratio]]`, `[[exam-oswald-factor-efficiency]]`, `[[sadraey-loiter-fuel-propdriven-aircraft]]`, `[[sadraey-roc-propdriven-aircraft]]`, `[[cruise-wing-loading]]`, `[[lift-curve-and-stall]]`, `[[wing-loading-gust-response]]`
- **`/aerodynamics-expert`** (Anderson 6e): §4.3 `[[airfoil-aerodynamic-characteristics]]`, §4.8 `[[thin-airfoil-theory-cambered]]`, §4.11 `[[modern-airfoil-design-practices]]`, §4.12 `[[boundary-layer-transition-separation]]`, §4.13 `[[airfoil-stall-aerodynamic-phenomena]]`, §5.3 `[[prandtl-lifting-line-theory]]`, §5.3.1 `[[elliptical-lift-distribution]]`, §5.3.3 `[[aspect-ratio-effects-on-induced-drag]]` + `[[lift-slope-finite-wing]]`, §6.7.2 `[[airplane-drag-polar]]` + `[[maximum-lift-to-drag-ratio]]`, §20.3.2 `[[flow-over-airfoil-low-reynolds]]`
- **`/aerosandbox-expert`**: `[[aerobuildup-usage-and-vectorization]]`, `[[aerobuildup-neuralfoil-integration-and-fuselage-aero-update]]`, `[[aerobuildup-360-degree-aerodynamics]]`, `[[stability-derivatives-from-asb-solvers]]`, `[[nfoil-analysis-confidence-constraint]]`, `[[nfoil-rapid-airfoil-analysis]]`, `[[phd-neuralfoil-overview-and-architecture]]`, `[[phd-neuralfoil-compressibility-correction]]`, `[[phd-aerobuildup-workbook-buildup]]`, `[[study-aerobuildup-ll-unsweep-calibration]]`, `[[vlm-vortex-lattice-method-3d-overview]]`
- **`/rc-aircraft-designer`** (Lennon + rcplanedesigner): `lennon-wing-position-dihedral`, `lennon-stall-patterns-and-tip-design`, `lennon-wing-loading`, `lennon-symmetrical-airfoil-aerobatics`, `lennon-rudder-sizing`, `lennon-typical-proportions-by-mission`, `lennon-reynolds-number`, `lennon-flap-deployment-effects`, `lennon-aerobatic-high-g-wing-sizing`, `airplane-balance-finding-the-first-flight-cg`, `wing-aspect-ratio--practical-limits-and-mission-consistent-ranges`, `tail-horizontal-tail-placement-and-sizing--practical-limits-and-mission-consistent-ranges`, `tail-rudder--practical-limits-and-mission-consistent-ranges`, `wing-wing-area-wing-loading--wing-loading-as-a-practical-relation`

### GitHub-Issues (Kontext)
- gh-402 (Spare-Units), gh-487 (Gust-Critical), gh-577 (OP-Resolver), gh-626 (Polar-Chip-Row), gh-627 (trim_residuals dict), gh-630/633/634 (Polar-Rejection-Pipeline)

### Code-Hooks
- `app/services/assumption_compute_service.py:947+` — `_fit_parabolic_polar()` (Rejection-Gates)
- `app/services/assumption_compute_service.py:862-866` — `_fine_sweep_cl_max()` (Vectorize-Target R-A1)
- `app/services/mission_kpi_service.py` — Validator-Hook (R-S1, R-T1..R-T3, R-V1..R-V3, R-W1..R-W3, R-E1..R-E2)
- `app/services/mission_preset_seed.py` — Mission-Bänder
- `app/api/utils.py:36-115` — Solver-Dispatch (R-A4)
- `app/schemas/polar_by_config.py:68-92` — `PolarRejection` (GAP-2: Gate-Kategorisierung)
