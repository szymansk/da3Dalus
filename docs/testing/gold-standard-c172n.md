# Gold Standard Reference — Cessna 172N Skyhawk

> **Purpose.** Reference data sheet for **manually smoke-testing** the
> da3Dalus design → analysis pipeline. Enter the data from section
> **A. INPUTS** into the app step-by-step (in the order shown), then run
> the analysis and verify the app's outputs against section
> **B. EXPECTED OUTPUTS** within the listed tolerances.
>
> Sister document for the Schleicher ASK-21: [`gold-standard-ask21.md`](./gold-standard-ask21.md).

## Konfidenz-Legende

| Marker | Meaning |
|:---:|---|
| ✓ | **Verified** — directly from primary source (Cessna POH / FAA TCDS / Roskam) |
| ◯ | **Typical** — widely cited, but specific value varies slightly between sources |
| ? | **Estimated** — derived analytically or from secondary references |

## Quellen

1. **Cessna 172N POH** — *Pilot's Operating Handbook, Model 172N Skyhawk*, Cessna Aircraft Co., 1977. [PDF mirror (Bakersfield Flying Club)](https://www.bakersfieldflyingclub.com/wp-content/uploads/2016/11/C172N-1977-POH.pdf); [1978 PDF (Wings Flight School)](https://wingsflightschool.com/document/Cessna-172N-POH-1978.pdf). Primary for V-speeds, mass, CG, performance.
2. **FAA Type Certificate Data Sheet 3A12** — Cessna 172 series, Rev. 86, 2023. [PDF](https://static1.squarespace.com/static/5cbd9e8265a707b68560908d/t/64fd9b657a74bb2edeb772df/1694341990018/Cessna+172N+TCDS+3A12+Rev86.pdf); [Summary at Parrish Aviation](https://www.parrishaviation.com/blog/cessna-172-type-certificate-data-sheet-tcds-3a12). Primary for geometric and certification limits.
3. **Roskam, J.** — *Airplane Design Part VI: Preliminary Calculation of Aerodynamic, Thrust and Power Characteristics*, DARcorp, 1990. Primary for stability derivatives (consumed via UIUC FlightGear linear model below).
4. **UIUC FlightGear linear model** — `cessna172/linear.html`, Roskam-derived C-172 linear stability tables. [Mirror](https://us1mirror.flightgear.org/terrasync/fgdata/fgdata_2020_3/Aircraft-uiuc/models/cessna172/linear.html). **Primary source for B3 stability derivatives** — replaces all Roskam-cited but unverifiable numbers.
5. **PyFME** — Python flight mechanics engine, `cessna_172.py` (Roskam + DATCOM cited). [GitHub](https://github.com/AeroPython/PyFME/blob/master/src/pyfme/aircrafts/cessna_172.py). Cross-check on geometry and aero coefficients.
6. **Skytamer Cessna 172N data** (Jane's All The World's Aircraft excerpts) — [skytamer.com/Cessna_172N.html](https://www.skytamer.com/Cessna_172N.html). Primary for tail dimensions and propeller diameter.
7. **Phillips, W.F.** — *Mechanics of Flight*, 2nd ed., Wiley, 2010. Detailed stability examples.
8. **UIUC Airfoil Database** — `naca2412.dat`.

> **Note on retracted citation.** A previous version of this document
> cited *NASA CR-3022 — Tomerlin & Lankford "Flight Test Evaluation
> of a Cessna 172"*. Web verification (NTRS search, 2026-05) shows
> that NASA CR-3022 is in fact Kuhlman, J.M., "Analytical Studies of
> Separated Vortex Flow on Highly Swept Wings" (Old Dominion U., 1978)
> — **not a Cessna 172 report**. The citation has been removed.

> The variant **172N (1976–1984)** is chosen because it is the
> single most cited Cessna in academic aerospace literature.
> The 172R/S (post-1996) has better modern data but less peer-reviewed
> derivative tables.

---

## Quick Reference — Cessna 172N

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 1900" width="700" stroke="currentColor" stroke-width="3" fill="none" font-family="monospace" font-size="30">
  <!-- ====== TOP VIEW ====== nose pointing up -->
  <g transform="translate(100, 60)">
    <text x="0" y="-20" font-size="34" stroke="none" fill="currentColor" font-weight="bold">TOP VIEW</text>
    <!-- Fuselage: 8.28m long, ~1.05m max width -->
    <path d="M 600 0 Q 555 35 540 90 Q 530 140 535 180 L 535 700 Q 540 760 555 800 L 600 828 L 645 800 Q 660 760 665 700 L 665 180 Q 670 140 660 90 Q 645 35 600 0 Z"/>
    <!-- Wing: root chord 1.625m at y=235..397.5, tip chord 1.118m -->
    <!-- starboard half from x=600..1150 (550cm = 5.5m half-span) -->
    <path d="M 600 235 L 1150 235 L 1150 347 L 600 397 Z"/>
    <!-- port mirror -->
    <path d="M 600 235 L 50   235 L 50   347 L 600 397 Z"/>
    <!-- Strut (V-strut on each side, from fuselage low to wing mid-span underside) -->
    <line x1="565" y1="400" x2="350" y2="280" stroke-dasharray="4,3" stroke-width="2"/>
    <line x1="635" y1="400" x2="850" y2="280" stroke-dasharray="4,3" stroke-width="2"/>
    <!-- Horizontal stabilizer: span 3.40m = 340cm, chord ~0.5m at rear -->
    <rect x="430" y="720" width="340" height="55"/>
    <!-- Vertical fin in top view: thin centerline strip extended -->
    <rect x="595" y="650" width="10" height="170"/>
    <!-- Engine cowling / propeller -->
    <line x1="503" y1="0" x2="697" y2="0" stroke-width="6"/>
    <text x="600" y="-30" text-anchor="middle" stroke="none" fill="currentColor" font-size="22">prop ⌀ 1.93 m</text>
    <!-- Dimensions -->
    <line x1="50" y1="900" x2="1150" y2="900" stroke-width="1.5"/>
    <line x1="50"   y1="885" x2="50"   y2="915" stroke-width="1.5"/>
    <line x1="1150" y1="885" x2="1150" y2="915" stroke-width="1.5"/>
    <text x="600" y="945" text-anchor="middle" stroke="none" fill="currentColor">b = 11.00 m</text>
    <line x1="1210" y1="0" x2="1210" y2="828" stroke-width="1.5"/>
    <line x1="1195" y1="0"   x2="1225" y2="0"   stroke-width="1.5"/>
    <line x1="1195" y1="828" x2="1225" y2="828" stroke-width="1.5"/>
    <text x="1260" y="420" stroke="none" fill="currentColor">L = 8.28 m</text>
  </g>

  <!-- ====== SIDE VIEW ====== nose pointing left -->
  <g transform="translate(100, 1080)">
    <text x="0" y="-20" font-size="34" stroke="none" fill="currentColor" font-weight="bold">SIDE VIEW</text>
    <!-- Fuselage silhouette: nose with engine, cabin bulge, tail boom -->
    <path d="M 0 130 L 60 110 L 100 95 Q 180 80 280 75 L 360 65 L 460 75 Q 540 80 620 95 L 760 165 L 828 200 L 828 220 L 460 230 Q 280 230 100 215 L 60 200 L 0 175 Z"/>
    <!-- Engine cowling / firewall line -->
    <line x1="100" y1="95" x2="100" y2="215" stroke-width="1.5" stroke-dasharray="6,3"/>
    <!-- High wing seen edge-on: small rectangle above fuselage -->
    <rect x="260" y="60" width="195" height="14" fill="currentColor"/>
    <!-- Wing strut (V-strut from lower fuselage to wing underside) -->
    <line x1="280" y1="74" x2="280" y2="170" stroke-width="2"/>
    <line x1="440" y1="74" x2="280" y2="170" stroke-dasharray="3,3" stroke-width="2"/>
    <!-- Conventional empennage: V-fin + H-stab at low position -->
    <path d="M 680 200 L 800 70 L 828 70 L 828 200 Z"/>
    <rect x="725" y="195" width="105" height="10" fill="currentColor"/>
    <text x="828" y="55" text-anchor="end" stroke="none" fill="currentColor" font-size="20">V-fin</text>
    <!-- Tricycle landing gear: nose wheel + main wheels -->
    <line x1="120" y1="215" x2="120" y2="275" stroke-width="2"/>
    <circle cx="120" cy="280" r="14" stroke-width="2"/>
    <line x1="345" y1="220" x2="320" y2="290" stroke-width="2"/>
    <circle cx="320" cy="295" r="16" stroke-width="2"/>
    <!-- Propeller circle (side view appears as a tall ellipse) -->
    <line x1="0" y1="35" x2="0" y2="240" stroke-width="2"/>
    <text x="-15" y="135" text-anchor="end" stroke="none" fill="currentColor" font-size="20">prop</text>
    <!-- Dimension: total length -->
    <line x1="0" y1="340" x2="828" y2="340" stroke-width="1.5"/>
    <text x="414" y="375" text-anchor="middle" stroke="none" fill="currentColor">8.28 m</text>
    <!-- Dimension: height -->
    <line x1="-50" y1="55" x2="-50" y2="295" stroke-width="1.5"/>
    <text x="-80" y="180" text-anchor="middle" stroke="none" fill="currentColor" font-size="22" transform="rotate(-90 -80 180)">2.72 m</text>
  </g>

  <!-- ====== FRONT VIEW ====== nose toward viewer -->
  <g transform="translate(100, 1500)">
    <text x="0" y="-20" font-size="34" stroke="none" fill="currentColor" font-weight="bold">FRONT VIEW</text>
    <!-- High wing with 1.73° dihedral: tip rise = 5.5m × tan(1.73°) ≈ 16.6 cm -->
    <line x1="50"   y1="93" x2="600"  y2="76" stroke-width="6"/>
    <line x1="600"  y1="76" x2="1150" y2="93" stroke-width="6"/>
    <!-- Wing thickness: NACA 2412 → 12% × 1.625 = 19.5cm at root -->
    <line x1="50"   y1="111" x2="600"  y2="92" stroke-width="6"/>
    <line x1="600"  y1="92"  x2="1150" y2="111" stroke-width="6"/>
    <!-- Cabin / fuselage cross-section -->
    <rect x="555" y="92" width="90" height="115" rx="20"/>
    <!-- Wing strut (V) -->
    <line x1="565" y1="200" x2="370" y2="93" stroke-width="2"/>
    <line x1="635" y1="200" x2="830" y2="93" stroke-width="2"/>
    <!-- Vertical fin behind cabin -->
    <line x1="600" y1="92" x2="600" y2="20" stroke-width="6"/>
    <!-- Propeller -->
    <line x1="503" y1="155" x2="697" y2="155" stroke-width="2"/>
    <ellipse cx="600" cy="155" rx="97" ry="6"/>
    <!-- Tricycle gear -->
    <line x1="600" y1="207" x2="600" y2="260" stroke-width="2"/>
    <line x1="500" y1="220" x2="450" y2="275" stroke-width="2"/>
    <line x1="700" y1="220" x2="750" y2="275" stroke-width="2"/>
    <circle cx="600" cy="270" r="14" stroke-width="2"/>
    <circle cx="445" cy="285" r="16" stroke-width="2"/>
    <circle cx="755" cy="285" r="16" stroke-width="2"/>
    <!-- Dimension -->
    <line x1="50" y1="335" x2="1150" y2="335" stroke-width="1.5"/>
    <text x="600" y="370" text-anchor="middle" stroke="none" fill="currentColor">b = 11.00 m</text>
  </g>
</svg>

| Größe | Wert | Konf. |
|---|---|:---:|
| Spannweite *b* | 11.00 m (Jane's: 10.92 m / 35 ft 10 in) | ✓ |
| Flügelfläche *S* | 16.17 m² (174 ft²) | ✓ |
| Streckung *AR* | 7.32 (with b=11.00) / 7.37 (with Jane's b=10.92) | ✓ |
| Mittlere aerodynamische Tiefe *MAC* | 1.4935 m (58.8 in) | ✓ |
| Länge *L* | 8.28 m (27 ft 2 in) | ✓ |
| Höhe (überall) | 2.72 m (8 ft 11 in) | ✓ |
| Leermasse (Skyhawk II equipped) | 649 kg (1430 lb) — range 1379–1480 lb depending on avionics | ◯ |
| MTOM | **1043 kg (2300 lb)** | ✓ |
| Cruise speed (75% Pwr) | 122 KTAS @ 8000 ft | ✓ |
| Best glide | 65 KIAS → L/D ≈ 9 | ✓ |
| Stall V_S0 (full flaps) | 33 KCAS / 41 KIAS | ✓ |
| V_NE | 158 KIAS | ✓ |
| Engine | Lycoming O-320-H2AD, 160 HP | ✓ |
| Propeller | McCauley 1C160, **75 in** (1.91 m) fixed pitch — Jane's | ✓ |

---

# A. INPUTS

Reihenfolge entspricht dem Design-Workflow der App.

## A1. Mission Objectives

| Parameter | Wert | Einheit | Quelle | Konf. |
|---|---|---|---|:---:|
| Aircraft type | 4-seat single-engine high-wing GA aircraft | — | Cessna | ✓ |
| Crew + Pax | 4 (1 pilot + 3 pax) | — | Cessna | ✓ |
| Useful load | 870 lb (395 kg) | lb | POH | ✓ |
| Max baggage | 120 lb (54 kg) | lb | POH | ✓ |
| Fuel capacity | 40 gal usable (151 L = 109 kg) | gal | POH | ✓ |
| Range @ 75 % Power, 8000 ft | 440 nm (815 km), 4 h endurance | nm | POH | ✓ |
| Cruise speed @ 75 % | 122 KTAS @ 8000 ft | kt | POH | ✓ |
| Cruise altitude | 4000–10 000 ft typ. | ft | POH | ◯ |
| Service ceiling | 14 200 ft | ft | POH | ✓ |
| Stall speed (V_S0, full flaps) | **33 KCAS / 41 KIAS** | kt | POH | ✓ |
| Takeoff ground roll (SL, ISA, MTOM) | 805 ft | ft | POH | ✓ |
| Takeoff over 50 ft obstacle | 1440 ft | ft | POH | ✓ |
| Landing ground roll | 520 ft | ft | POH | ✓ |
| Landing over 50 ft | 1250 ft | ft | POH | ✓ |
| Climb rate (SL, MTOM) | 770 fpm | fpm | POH | ✓ |
| Limit load factor (flaps up) | +3.8 g / -1.52 g | g | TCDS | ✓ |
| Limit load factor (flaps down) | +3.0 g / 0 g | g | TCDS | ✓ |
| Category | Normal / Utility | — | TCDS | ✓ |

## A2. Design Assumptions

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Initial mass estimate *m* | 1043 (MTOM) | kg | ✓ |
| Target CG location *x_CG* | typical 41.5 in aft of datum ≈ 1.054 m | m | ◯ |
| Target static margin | **15 %** MAC | — | ◯ |
| Assumed CL_max (clean) | 1.40 | — | ◯ |
| Assumed CL_max (flaps full) | 2.10 | — | ◯ |
| Assumed CD₀ | 0.030 | — | ◯ |
| Assumed Oswald *e* | 0.77 | — | ◯ |
| Load-factor limit | +3.8 g | g | ✓ |

> The C-172 "datum" is the **firewall** (aft side). All POH CG values
> are in **inches aft of datum**. When entering into the app the unit
> convention (mm vs m vs in) must be respected — see A6.

## A3. Wing Configuration

The C-172 wing is a **moderately tapered, untwisted-airfoil, constant-airfoil
high-wing planform** with strut bracing.

### A3.1 Main wing — global parameters

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Span *b* | 11.00 | m | ✓ |
| Reference area *S* | 16.17 | m² | ✓ |
| Aspect ratio *AR* | 7.32 | — | ✓ |
| Taper ratio λ | 0.687 (c_tip / c_root = 1.118 / 1.625) | — | ✓ |
| Sweep (quarter-chord) | ≈ 0° | ° | ◯ |
| Dihedral | 1.73 (1° 44′) | ° | ✓ |
| Incidence (root) | +1.5 (+1° 30′) | ° | ✓ |
| Twist (washout root→tip) | **3.0** (geometric, +1.5° root → -1.5° tip) | ° | ✓ |
| Mean aerodynamic chord *MAC* | 1.4935 (4.9 ft) | m | ✓ |
| Wing position on fuselage | high-wing, strut-braced | — | ✓ |

### A3.2 Wing sections (entry into the wing editor)

| Station | y from centreline (m) | chord (m) | twist (°) | airfoil |
|---|---|---|---|---|
| Root | 0.00 | 1.625 | +1.5 | NACA 2412 |
| Tip  | 5.50 | 1.118 | -1.5 | NACA 2412 |

> **Profile selection:** The C-172N uses **NACA 2412** uniformly from
> root to tip. This is a 12 %-thick, 2 %-cambered classical NACA
> 4-digit section — the same family as the 2415 used by the Piper
> Cub and many other GA aircraft.

### A3.3 Control surfaces & high-lift devices

| Surface | Type | Span (each, % b/2) | Chord (% local) | Konf. |
|---|---|---|---|:---:|
| Aileron | conventional, hinged | outer ≈ 40 % | ≈ 22 % | ◯ |
| **Flaps** | **single-slotted**, 0° / 10° / 20° / 30° | inner ≈ 60 % | ≈ 30 % | ✓ |

> **Flap settings (POH 172N):**
> - 0° — clean
> - 10° — takeoff (recommended for short-field)
> - 20° — approach
> - 30° — landing (full)
>
> V_FE = 110 KIAS (flaps 10°) | 85 KIAS (flaps ≥ 20°)

### A3.4 Wing planform (zur visuellen Prüfung)

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 550" width="720" stroke="currentColor" stroke-width="3" fill="none" font-family="monospace" font-size="28">
  <text x="20" y="40" font-size="32" stroke="none" fill="currentColor" font-weight="bold">WING PLANFORM (full span, view from above)</text>
  <!-- centreline -->
  <line x1="700" y1="100" x2="700" y2="430" stroke-dasharray="6,4" stroke-width="1.5"/>
  <text x="715" y="115" stroke="none" fill="currentColor" font-size="22">centreline</text>
  <!-- starboard half: root c=162.5 at x=700..1250 (half-span 550 cm) -->
  <!-- LE at y=130 straight; TE at root y=292.5; TE at tip y=243.5 -->
  <path d="M 700 130 L 1250 130 L 1250 243 L 700 293 Z"/>
  <!-- port mirror -->
  <path d="M 700 130 L 150  130 L 150  243 L 700 293 Z"/>
  <!-- Flap region: inner 60% of half-span -->
  <rect x="700" y="277" width="330" height="16" fill="currentColor" opacity="0.4"/>
  <rect x="370" y="277" width="330" height="16" fill="currentColor" opacity="0.4"/>
  <text x="865" y="320" stroke="none" fill="currentColor" font-size="22" text-anchor="middle">flap (single-slotted)</text>
  <!-- Aileron region: outer ~40% -->
  <rect x="1030" y="245" width="220" height="14" fill="currentColor" opacity="0.6"/>
  <rect x="150"  y="245" width="220" height="14" fill="currentColor" opacity="0.6"/>
  <text x="1140" y="240" stroke="none" fill="currentColor" font-size="22" text-anchor="middle">aileron</text>
  <!-- chord labels -->
  <text x="725" y="200" stroke="none" fill="currentColor" font-size="22">c_root = 1.625 m</text>
  <text x="1260" y="195" stroke="none" fill="currentColor" font-size="22">c_tip = 1.118 m</text>
  <!-- Dimension: span -->
  <line x1="150" y1="380" x2="1250" y2="380" stroke-width="1.5"/>
  <line x1="150"  y1="370" x2="150"  y2="390" stroke-width="1.5"/>
  <line x1="1250" y1="370" x2="1250" y2="390" stroke-width="1.5"/>
  <text x="700" y="415" text-anchor="middle" stroke="none" fill="currentColor" font-size="22">b = 11.00 m  /  S = 16.17 m²  /  AR = 7.32</text>
  <text x="700" y="500" text-anchor="middle" stroke="none" fill="currentColor" font-size="22">Profile: NACA 2412 throughout · Twist: +1.5°(root) → -1.5°(tip) · Dihedral: 1.73°</text>
</svg>

## A4. Fuselage

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Overall length | 8.28 | m | ✓ |
| Maximum height (cabin) | ≈ 1.30 | m | ◯ |
| Maximum width (cabin) | ≈ 1.00 | m | ✓ |
| Cabin length | ≈ 2.05 | m | ◯ |
| Type of structure | aluminum semi-monocoque | — | ✓ |
| Datum (POH) | firewall (aft side) | — | ✓ |
| Wing carry-through *x* | ≈ 1.20 m aft of firewall ≈ 2.10 m aft of nose | m | ◯ |
| Equivalent diameter (drag) | ≈ 1.15 | m | ? |

## A5. Tail Configuration

### A5.1 Conventional empennage

The C-172 uses a **conventional (cruciform-like) tail**: horizontal
stabilizer mounted on the fuselage tail boom, vertical fin attached
above. **Not a T-tail.** The H-stab is **all-moving** (stabilator) on
some variants but **fixed-with-elevator** on the 172N.

### A5.2 Horizontal stabilizer

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Span | **3.45** (11 ft 4 in, Jane's) | m | ✓ |
| Area (planform, incl. elevator) | **2.00** (21.56 ft², Jane's) | m² | ✓ |
| Aspect ratio | **5.95** (b² / S) | — | ✓ |
| Mean chord (S / b) | ≈ 0.58 | m | ✓ |
| Sweep (LE) | ≈ 0° | ° | ◯ |
| Dihedral | 0° | ° | ✓ |
| Incidence | -1.5 to 0° (typ. slight downward) | ° | ? |
| Airfoil | NACA 0009 / 0010 symmetric | — | ◯ |
| Tail arm *l_h* (CG → c/4 H-stab) | ≈ 4.60 | m | ◯ |
| **Tail volume coefficient *V_h*** | **≈ 0.38** (geometric: S_h · l_h / S · MAC) — see note | — | ? |

### A5.3 Vertical stabilizer

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Height (fin) | ≈ 1.20 | m | ◯ |
| Area (fin only) | **1.04** (Jane's) | m² | ✓ |
| Area (rudder) | **0.69** | m² | ✓ |
| Area (fin + rudder total) | **1.73** | m² | ✓ |
| Airfoil | symmetric, ≈ NACA 0010 | — | ◯ |
| **Tail volume coefficient *V_v*** | **≈ 0.027** (geometric: S_v · l_v / S · b) — see note | — | ? |

> **Tail volume coefficient note.** A previous version of this
> document gave V_h = 0.85 and V_v = 0.043 as "Roskam-typical".
> Recomputing with the now-verified geometry (S_h = 2.00 m²,
> l_h ≈ 4.60 m, S = 16.17 m², MAC = 1.49 m, S_v = 1.04 m²,
> b = 11.00 m) gives:
> - V_h = (2.00 × 4.60) / (16.17 × 1.49) = **0.38**
> - V_v = (1.04 × 4.60) / (16.17 × 11.00) = **0.027**
>
> These match the actual C-172 geometry better. The 0.85 / 0.043
> figures appear to be misremembered or to use a non-standard
> definition (e.g., exposed-area, effective-area). Use the
> geometric values for sanity-checking the app's output.

### A5.4 Control surfaces

| Surface | Position | Type | Konf. |
|---|---|---|:---:|
| Elevator | TE of H-stab, full span | conventional, with trim tab | ✓ |
| Rudder | TE of V-fin, full height | conventional | ✓ |
| Elevator trim tab | mechanical (wheel in cabin) | — | ✓ |

## A6. Mass & CG / Weight Items

### A6.1 Mass states

| State | Mass (kg) | Mass (lb) | Konf. |
|---|---|---|:---:|
| Empty (bare Skyhawk, 1977 POH) | 626 | 1379 | ◯ |
| Empty (Skyhawk II, 1977 POH) | 636 | 1403 | ◯ |
| Empty (Skyhawk II, 1978 POH) | 644 | 1419 | ◯ |
| Empty (Skyhawk II equipped, Jane's) | **649** | **1430** | ◯ |
| Empty (typical fully-equipped) | up to 671 | up to 1480 | ◯ |
| Pilot only (170 lb) | 726 | 1600 | ◯ |
| 2 pax, fuel half | ≈ 900 | ≈ 1985 | ◯ |
| **MTOM** | **1043** | **2300** | ✓ |

> **Empty mass spread.** The "Cessna 172N" empty mass varies from
> 1379 lb (bare Skyhawk, no nav equipment) to 1480 lb (well-equipped
> IFR Skyhawk II) depending on avionics, paint, options, and POH
> revision year. The 1430 lb value used here corresponds to a typical
> equipped "Skyhawk II" per Jane's All The World's Aircraft.

### A6.2 CG envelope

| Parameter | Wert (in aft of datum) | Wert (m aft of datum) | Konf. |
|---|---|---|:---:|
| Datum | firewall | 0 | ✓ |
| Forward CG limit @ 1950 lb | 33.0 in | 0.838 m | ✓ |
| Forward CG limit @ 2300 lb (MTOM) | 35.5 in | 0.902 m | ✓ |
| Aft CG limit (all weights) | 47.3 in | 1.201 m | ✓ |
| MAC leading edge | ≈ 35.6 in | ≈ 0.904 m | ◯ |
| MAC trailing edge | ≈ 94.3 in (35.6 + 58.7) | ≈ 2.395 m | ◯ |
| Typical cruise CG | ≈ 41.5 in | ≈ 1.054 m | ◯ |

### A6.3 CG envelope diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 600" width="500" stroke="currentColor" stroke-width="2" fill="none" font-family="monospace" font-size="22">
  <text x="20" y="40" font-size="26" stroke="none" fill="currentColor" font-weight="bold">CG ENVELOPE — Cessna 172N</text>
  <!-- Axes -->
  <line x1="120" y1="500" x2="900" y2="500" stroke-width="2"/>
  <line x1="120" y1="500" x2="120" y2="100" stroke-width="2"/>
  <!-- x axis: CG (in aft of datum) 30..50 in -->
  <!-- y axis: mass (lb) 1300..2400 -->
  <!-- mapping: x = 120 + (cg-30)/(50-30)*780 -->
  <!--          y = 500 - (m-1300)/(2400-1300)*400 -->
  <!-- Aft limit at 47.3 in: x = 120 + 17.3/20*780 = 120+675 = 795 -->
  <line x1="795" y1="500" x2="795" y2="100" stroke-dasharray="6,4" stroke-width="1.5"/>
  <text x="795" y="90" text-anchor="middle" stroke="none" fill="currentColor" font-size="20">aft 47.3 in</text>
  <!-- Forward limit varies with weight: linear from 33.0@1950 lb to 35.5@2300 lb -->
  <!-- At 1300 lb: x = 120 + 3/20*780 = 120+117 = 237 (extrapolated, not actually limiting) -->
  <!-- At 1950 lb (y=300): cg=33.0, x = 120 + 3/20*780 = 237 -->
  <!-- At 2300 lb (y=156): cg=35.5, x = 120 + 5.5/20*780 = 120+214.5 = 334 -->
  <line x1="237" y1="300" x2="334" y2="156" stroke-dasharray="6,4" stroke-width="1.5"/>
  <line x1="237" y1="500" x2="237" y2="300" stroke-dasharray="6,4" stroke-width="1.5"/>
  <text x="285" y="280" text-anchor="middle" stroke="none" fill="currentColor" font-size="18">fwd limit (mass-dependent)</text>
  <!-- Permitted CG region (shaded) -->
  <path d="M 237 500 L 237 300 L 334 156 L 795 156 L 795 500 Z" fill="currentColor" opacity="0.07"/>
  <!-- Reference points -->
  <!-- Empty 1430 lb @ ~37 in -->
  <circle cx="393" cy="448" r="6" fill="currentColor"/>
  <text x="410" y="453" stroke="none" fill="currentColor" font-size="18">empty 1430</text>
  <!-- Pilot only 1600 lb @ ~38 in -->
  <circle cx="432" cy="386" r="6" fill="currentColor"/>
  <text x="450" y="390" stroke="none" fill="currentColor" font-size="18">solo 1600</text>
  <!-- Typical cruise 2050 lb @ 41.5 in -->
  <circle cx="568" cy="222" r="6" fill="currentColor"/>
  <text x="585" y="226" stroke="none" fill="currentColor" font-size="18">cruise 2050</text>
  <!-- MTOM 2300 lb @ 41.5 in -->
  <circle cx="568" cy="131" r="8" fill="currentColor"/>
  <text x="585" y="135" stroke="none" fill="currentColor" font-size="18">MTOM 2300</text>
  <!-- Axis labels -->
  <text x="510" y="555" text-anchor="middle" stroke="none" fill="currentColor" font-size="22">CG position aft of firewall (in)</text>
  <text x="60" y="300" text-anchor="middle" stroke="none" fill="currentColor" font-size="22" transform="rotate(-90 60 300)">mass (lb)</text>
  <!-- X tick marks -->
  <text x="120" y="525" text-anchor="middle" stroke="none" fill="currentColor" font-size="18">30</text>
  <text x="510" y="525" text-anchor="middle" stroke="none" fill="currentColor" font-size="18">40</text>
  <text x="900" y="525" text-anchor="middle" stroke="none" fill="currentColor" font-size="18">50</text>
  <!-- Y tick marks -->
  <text x="105" y="505" text-anchor="end" stroke="none" fill="currentColor" font-size="18">1300</text>
  <text x="105" y="305" text-anchor="end" stroke="none" fill="currentColor" font-size="18">1850</text>
  <text x="105" y="105" text-anchor="end" stroke="none" fill="currentColor" font-size="18">2400</text>
</svg>

### A6.4 Weight breakdown (typical loaded, for entering into Weight Items)

| Item | Mass (kg) | Position (in aft of firewall) | Konf. |
|---|---|---|:---:|
| Empty airframe (incl. engine, prop, oil) | 649 | 38.0 | ◯ |
| Pilot (170 lb) | 77 | 37.0 | ✓ |
| Front pax (170 lb) | 77 | 37.0 | ✓ |
| Rear pax × 2 (170 lb each) | 154 | 73.0 | ✓ |
| Fuel (40 gal × 6 lb/gal) | 109 | 48.0 | ✓ |
| Baggage area 1 (≤ 120 lb) | up to 54 | 95.0 | ✓ |

> **Important unit conversion:** the app may want all `Weight Item`
> positions in metres aft of the nose, not inches aft of firewall.
> The firewall is approximately **0.85 m aft of the nose**, so add
> 0.85 m to the in→m converted value. Alternatively, place the datum
> at the firewall and adjust the nose position accordingly.

## A7. Propulsion (Cessna only — ASK-21 has none)

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Engine | Lycoming O-320-H2AD | — | ✓ |
| Type | 4-cyl horizontally-opposed, naturally aspirated, carbureted | — | ✓ |
| Rated power | 160 HP @ 2700 RPM | HP | ✓ |
| BSFC @ cruise | ≈ 0.42 lb/(HP·h) | — | ◯ |
| Propeller | McCauley 1C160 fixed-pitch | — | ✓ |
| Prop diameter | **1.91 m (75 in / 6 ft 3 in)** — Jane's; some sources cite 76 in | m | ✓ |
| Prop blades | 2 | — | ✓ |

> For VLM/AVL analysis the propeller is typically *not* modelled. The
> design path test in the app may skip propulsion entirely; if the
> "Mass & CG" section uses an engine weight estimate, plug **129 kg
> (incl. firewall-forward installation)** as a placeholder.

---

# B. EXPECTED OUTPUTS

Werte, die die App nach erfolgreicher Analyse zeigen *sollte*. Toleranzen
sind für **Tier B** gesetzt; Tier-C-Größen sind zusätzlich aufgelistet,
aber als optional markiert.

## B1. Aerodynamic Coefficients (Tier B)

### B1.1 Clean configuration (flaps 0°)

| Größe | Erwarteter Wert | Toleranz | Quelle | Konf. |
|---|---|---|---|:---:|
| **CL_α** (whole aircraft) | **5.143 1/rad** ≈ 0.0898 1/° | ±10 % | UIUC FlightGear / Roskam | ✓ |
| CL_α_w (wing alone, clean) | 4.6 1/rad | ±10 % | Roskam VI (derived) | ◯ |
| ~~CL_α_h (horizontal tail)~~ | (probably confused with CL_q below; H-tail-alone slope ≈ 3.5–4.5 1/rad) | — | — | ? |
| CL_0 (zero alpha, clean) | 0.31 | ±15 % | Roskam VI | ◯ |
| **CL_max** clean | **1.40** | ±10 % | NACA 2412 + 3D + wing | ✓ |
| α at CL_max | ≈ 16° | ±2° | wing | ◯ |
| **CD₀** clean (gear extended) | **0.031** (UIUC) / 0.030 (PyFME) | ±20 % | UIUC / PyFME | ✓ |
| **Oswald factor *e*** | **0.758** (specific) / 0.75 range | — | AeroToolbox / typical | ✓ |
| **L/D_max** | **≈ 10** | ±10 % | POH glide ratio | ✓ |
| CL at L/D_max | ≈ 0.85 | ±15 % | derived | ◯ |

### B1.2 Flap configurations

| Config | CL_max | ΔCL_max | ΔCD₀ | Konf. |
|---|---|---|---|:---:|
| Clean (flaps 0°) | 1.40 | — | 0 | ✓ |
| Flaps 10° (T/O) | 1.55 | +0.15 | +0.005 | ◯ |
| Flaps 20° (approach) | 1.70 | +0.30 | +0.020 | ◯ |
| Flaps 30° (landing, full) | **2.10** | **+0.70** | **+0.055** | ✓ |

> The clean and full-flap CL_max values are *derived from POH stall
> speeds* via CL_max = 2·W/(ρ·V_S²·S), with V_S = 51 KIAS (clean) and
> V_S0 = 41 KIAS (flaps full) at MTOM = 1043 kg. The intermediate
> values are interpolations consistent with NACA single-slotted-flap
> data.

## B2. Performance Points (Tier B)

| Größe | Erwarteter Wert | Toleranz | Quelle | Konf. |
|---|---|---|---|:---:|
| V_S clean (CAS) | 44 KCAS / 51 KIAS | ±5 % | POH | ✓ |
| V_S0 full flaps (CAS) | 33 KCAS / 41 KIAS | ±5 % | POH | ✓ |
| V_X (best angle climb) | 59 KIAS | ±3 kt | POH | ✓ |
| V_Y (best rate climb) | 73 KIAS | ±3 kt | POH | ✓ |
| Best glide speed (clean, MTOM) | 65 KIAS | ±3 kt | POH | ✓ |
| Climb rate (SL, MTOM) | 770 fpm | ±10 % | POH | ✓ |
| Cruise speed @ 75 % | 122 KTAS @ 8000 ft | ±5 % | POH | ✓ |
| L/D_max | ≈ 9–10 | ±15 % | POH / Roskam | ✓ |
| Range @ 75 % | 440 nm (40 gal usable) | ±10 % | POH | ✓ |
| Takeoff over 50 ft (SL, ISA, MTOM) | 1440 ft | ±15 % | POH | ✓ |
| Landing over 50 ft (SL, ISA, MTOM) | 1250 ft | ±15 % | POH | ✓ |
| Service ceiling | 14 200 ft | ±10 % | POH | ✓ |

## B3. Stability (Tier C — Cessna 172N is the strongest gold-standard here)

> For the C-172N, stability derivatives are **peer-reviewed and
> tabulated** in Roskam Part VI (worked example). This makes the C-172N
> a much stronger reference for the stability axis than the ASK-21.

### B3.1 Longitudinal (cruise condition, M ≈ 0.13, sea level, MTOM, CG @ 0.27 c̄)

All values verified against UIUC FlightGear C-172 linear model (Roskam-derived).

| Derivative | Wert (1/rad) | Toleranz | Quelle | Konf. |
|---|---|---|---|:---:|
| CL_α | **5.143** | ±10 % | UIUC | ✓ |
| CL_q | 3.9 | ±15 % | UIUC | ✓ |
| CL_δe | 0.430 | ±15 % | UIUC | ✓ |
| CM_α | **-0.89** | ±15 % | UIUC | ✓ |
| CM_q | -12.4 | ±20 % | UIUC | ✓ |
| CM_δe | -1.28 | ±15 % | UIUC | ✓ |
| CD_α | 0.130 | ±20 % | UIUC | ✓ |

| Aircraft property | Wert | Toleranz | Konf. |
|---|---|---|:---:|
| Neutral point (stick-fixed, power off) | ≈ 37 % MAC | ±5 % MAC | ◯ |
| Static margin @ typical cruise CG (27 % MAC) | ≈ 10 % MAC | ±5 % MAC | ◯ |
| Static margin @ aft CG (32 % MAC) | ≈ 5 % MAC | ±5 % MAC | ◯ |
| Short-period frequency | ≈ 2.5 rad/s | ±20 % | ? |
| Short-period damping ratio | ≈ 0.7 | ±30 % | ? |
| Phugoid period | ≈ 32 s | ±20 % | ? |

### B3.2 Lateral-Directional (cruise condition, same as above)

All values verified against UIUC FlightGear C-172 linear model (Roskam-derived).

| Derivative | Wert (1/rad) | Toleranz | Quelle | Konf. |
|---|---|---|---|:---:|
| CY_β | -0.31 | ±20 % | UIUC | ✓ |
| CY_p | -0.037 | ±30 % | UIUC | ✓ |
| CY_r | 0.21 | ±20 % | UIUC | ✓ |
| Cl_β (dihedral effect) | **-0.089** | ±20 % | UIUC | ✓ |
| Cl_p | -0.47 | ±15 % | UIUC | ✓ |
| Cl_r | 0.096 | ±20 % | UIUC | ✓ |
| Cl_δa | **±0.178** (UIUC: -0.178; sign convention varies) | ±15 % | UIUC | ◯ |
| CN_β | **+0.065** | ±20 % | UIUC | ✓ |
| CN_p | -0.030 | ±30 % | UIUC | ✓ |
| CN_r | -0.099 | ±20 % | UIUC | ✓ |
| CN_δr | **-0.0657** (UIUC) | ±15 % | UIUC | ✓ |

> **Sign convention note.** UIUC FlightGear publishes Cl_δa = -0.178
> (negative). Whether this comes out positive or negative depends on
> the aileron-deflection sign convention: "positive δa = right wing
> TE down" gives -0.178; "positive δa = right wing TE up (right roll)"
> flips the sign. The app's convention determines which value is
> correct.

| Mode | Wert | Toleranz | Konf. |
|---|---|---|:---:|
| Spiral mode | leicht divergent (T₂ ≈ 30 s) | qual. | ◯ |
| Dutch roll period | ≈ 4 s | ±30 % | ? |
| Dutch roll damping | ≈ 0.1 (lightly damped) | qual. | ◯ |
| Roll mode time constant | ≈ 0.5 s | ±30 % | ? |

---

# C. Offene Punkte / Lower Confidence

Nach der Recherche-Iteration (FAA TCDS, Jane's via Skytamer, UIUC
FlightGear Roskam-Modell, PyFME) bleiben folgende Werte unverifiziert:

- **Span 11.00 m vs 10.92 m** — POH rundet auf 36 ft 1 in (11.00 m);
  Jane's gibt 35 ft 10 in (10.92 m). 11.00 m ist nominell, 10.92 m
  ist die echte Geometrie. Wenn die App auf 5 mm genau rechnet, ist
  das relevant.
- **MAC leading-edge position** — die genaue Lage relativ zum Datum
  hängt von der Wing-Mounting-Geometrie ab; hier sind 35.6 in nur ein
  Mittelwert
- **TCDS-Rev-Spread bei der vorderen CG-Grenze** — verschiedene
  TCDS-Revisionen geben 35.5 in vs. 38.5–40 in @ 2300 lb. Vor
  ernsthafter Nutzung Rev. 86 PDF direkt prüfen.
- **H-stab Profil** und **V-stab Profil** — typisch NACA 0009/0010,
  aber kein Primärquellen-Zitat gefunden
- **H-stab Wurzel-/Tip-Tiefe** — nur Span und Fläche sind belegt;
  Tiefenverteilung mangels Quelle approximiert
- **Tail arm l_h** — kein Primärquellen-Zitat; geometrisch geschätzt
- **CL_α_h (horizontal tail alone)** — der frühere Wert 3.9 1/rad
  war wahrscheinlich eine Verwechslung mit CL_q (= 3.9, whole-aircraft
  pitch-rate derivative). H-Tail-alone-Slope dürfte 3.5–4.5 1/rad sein
- **Cl_δa Vorzeichen** — UIUC hat -0.178, je nach Konvention ±
- **Damping derivatives** (CM_q, CN_r usw.) — UIUC-Werte sind
  Berechnungs- nicht Flugtestwerte → höhere Unsicherheit als ±20 %
- **Modes** (period, damping ratio) — aus Derivaten abgeleitet,
  nicht direkt gemessen — bleiben bei `?`

---

# D. Smoke-Test-Hinweise

Beim manuellen Smoke-Test durch die App:

1. **Reihenfolge im UI** sollte A1 → A6 (+ A7 Propulsion falls
   vorhanden) entsprechen. Wenn die App "Mission Objectives" nicht
   als eigene Sektion hat (gh-Issue), dann V_S, climb rate, field
   length, V_NE im Hinterkopf behalten und nachher prüfen, *wo* sie
   sich verstecken.
2. **Einheiten** — die App verwendet `mm` in WingConfig und `m` in
   der DB. POH-Werte sind in **inch und lb**; immer umrechnen.
   `1 in = 25.4 mm`, `1 lb = 0.4536 kg`, `1 KIAS @ SL = 0.5144 m/s`.
3. **CL_max** der App ist meist eine **2D-Profilangabe**; Tabelle B1
   listet **3D-Whole-Aircraft-CL_max**. Bei NACA 2412 ist CL_max 2D
   ≈ 1.6; das 3D-CL_max der ganzen 172 ist niedriger (~1.40) wegen
   3D-Verlusten und Wing-Twist-Verlust.
4. **Flap-Konfigurationen** sind das beste Tier-C-Mittel zum Testen
   von High-Lift-Devices, falls die App das unterstützt.
5. **Stability-Tab** der App sollte beim 172 die Werte aus B3
   reproduzieren — das ist *der* Hauptwert dieses Gold-Standards
   gegenüber dem ASK-21.
6. **Neutral point** sollte in der Nähe von **37 % MAC** liegen;
   wenn die App einen anderen Wert anzeigt, prüfen ob die
   Tail-Volume-Coefficients und der CG korrekt eingegeben wurden.
7. **L/D_max** der 172 ist überraschend niedrig (≈ 10). Wenn die
   App > 15 zeigt, fehlt sehr wahrscheinlich der **parasitäre
   Widerstand** (Fahrwerk, Streben, Antennen, Cooling-Drag etc.).
