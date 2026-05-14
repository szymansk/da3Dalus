# Gold Standard Reference — Schleicher ASK-21

> **Purpose.** Reference data sheet for **manually smoke-testing** the
> da3Dalus design → analysis pipeline. Enter the data from section
> **A. INPUTS** into the app step-by-step (in the order shown), then run
> the analysis and verify the app's outputs against section
> **B. EXPECTED OUTPUTS** within the listed tolerances.
>
> Sister document for the Cessna 172N: [`gold-standard-c172n.md`](./gold-standard-c172n.md).

## Konfidenz-Legende

| Marker | Meaning |
|:---:|---|
| ✓ | **Verified** — directly from primary source (Schleicher manual / Idaflieg measurement) |
| ◯ | **Typical** — widely cited, but specific value varies slightly between sources |
| ? | **Estimated** — derived analytically or from secondary references |

## Quellen

1. **Schleicher GmbH** — *ASK-21 Flight Manual (POH)*, April 1980 — [PDF (Darlton GC mirror)](https://www.darltonglidingclub.co.uk/wp/wp-content/uploads/2020/09/FlightManual-ASK21.pdf). Primary for V-speeds, CG envelope, mass states.
2. **Schleicher GmbH** — *Instructions For Continued Airworthiness / Maintenance Manual*, FAA-approved Mar 1983 — [PDF](http://www.jerslash.net/~jer/photos/CAP/ASK-21-N221CP-Maint-Manual.pdf). Primary for all geometric data (sections I.4, VI.1).
3. **Schleicher GmbH** — official product page — [alexander-schleicher.de/en/flugzeuge/ask-21](https://www.alexander-schleicher.de/en/flugzeuge/ask-21/). Cross-check on dimensions and mass.
4. **Idaflieg Sommertreffen-Vermessungen** — public sailplane polar database. Primary for measured CL/CD polars at the 525 kg reference mass.
5. **Thomas, F.**: *Fundamentals of Sailplane Design*, College Park Press, 1999. Polar data, design rationale.
6. **Wikipedia (citing Jane's 1988-89)** — [Schleicher ASK 21](https://en.wikipedia.org/wiki/Schleicher_ASK_21). Cross-check on placarded V-speeds and load factors.
7. **UIUC Airfoil Coordinates Database** — `fxs02196.dat` (Wortmann FX S 02-196), `fx60126.dat` (Wortmann FX 60-126).

---

## Quick Reference — ASK-21

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1900 1750" width="720" stroke="currentColor" stroke-width="3" fill="none" font-family="monospace" font-size="34">
  <!-- ====== TOP VIEW ====== nose pointing up -->
  <g transform="translate(100, 60)">
    <text x="0" y="-20" font-size="36" stroke="none" fill="currentColor" font-weight="bold">TOP VIEW</text>
    <!-- Fuselage: 8.35m long, ~0.7m max width — slim sailplane pod -->
    <path d="M 850 0 Q 820 30 815 100 L 815 720 Q 815 820 850 850 Q 885 820 885 720 L 885 100 Q 880 30 850 0 Z"/>
    <!-- Wing: trapezoidal approximation, root chord 1.50m at y=250..400, tip chord 0.50m (Schleicher Maint. Manual §I.4) -->
    <!-- starboard -->
    <path d="M 850 250 L 1700 250 L 1700 300 L 850 400 Z"/>
    <!-- port -->
    <path d="M 850 250 L 0   250 L 0   300 L 850 400 Z"/>
    <!-- Horizontal stab (T-tail): 3.10m span, 1.92 m² area (mean chord ~0.62m), at rear -->
    <rect x="695" y="780" width="310" height="62"/>
    <!-- Vertical fin in top view: thin centerline strip -->
    <rect x="845" y="690" width="10" height="155"/>
    <!-- Dimension lines -->
    <line x1="0" y1="930" x2="1700" y2="930" stroke-width="1.5"/>
    <line x1="0"    y1="915" x2="0"    y2="945" stroke-width="1.5"/>
    <line x1="1700" y1="915" x2="1700" y2="945" stroke-width="1.5"/>
    <text x="850" y="975" text-anchor="middle" stroke="none" fill="currentColor">b = 17.00 m</text>
    <line x1="1760" y1="0" x2="1760" y2="850" stroke-width="1.5"/>
    <line x1="1745" y1="0"   x2="1775" y2="0"   stroke-width="1.5"/>
    <line x1="1745" y1="850" x2="1775" y2="850" stroke-width="1.5"/>
    <text x="1810" y="430" stroke="none" fill="currentColor">L = 8.35 m</text>
  </g>

  <!-- ====== SIDE VIEW ====== nose pointing left -->
  <g transform="translate(100, 1100)">
    <text x="0" y="-20" font-size="36" stroke="none" fill="currentColor" font-weight="bold">SIDE VIEW</text>
    <!-- Fuselage silhouette -->
    <path d="M 0 180 Q 30 140 80 130 Q 200 105 320 105 L 380 95 Q 420 88 480 100 L 770 175 L 835 215 L 835 235 L 380 235 Q 200 235 80 230 Q 30 220 0 200 Z"/>
    <!-- Wing seen edge-on -->
    <path d="M 240 175 L 360 175 L 360 182 L 240 182 Z" fill="currentColor"/>
    <!-- Vertical fin -->
    <path d="M 660 175 L 770 30 L 835 30 L 835 175 Z"/>
    <!-- Horizontal stab (T-tail) -->
    <path d="M 720 22 L 835 22 L 835 38 L 720 38 Z" fill="currentColor"/>
    <!-- Canopy bubble outline -->
    <path d="M 130 130 Q 220 80 350 80 L 420 95 L 130 130 Z" stroke-dasharray="6,4"/>
    <!-- Dimension -->
    <line x1="0" y1="290" x2="835" y2="290" stroke-width="1.5"/>
    <text x="420" y="335" text-anchor="middle" stroke="none" fill="currentColor">8.35 m</text>
  </g>

  <!-- ====== FRONT VIEW ====== nose toward viewer -->
  <g transform="translate(100, 1450)">
    <text x="0" y="-20" font-size="36" stroke="none" fill="currentColor" font-weight="bold">FRONT VIEW</text>
    <!-- Wing with ~3° dihedral: tip rises 44 cm over half-span 850 cm -->
    <line x1="0"    y1="120" x2="850"  y2="164" stroke-width="6"/>
    <line x1="850"  y1="164" x2="1700" y2="120" stroke-width="6"/>
    <!-- Fuselage cross-section (~0.65m × 0.85m elliptical) -->
    <ellipse cx="850" cy="175" rx="35" ry="48"/>
    <!-- T-tail: vertical fin + horizontal stab -->
    <line x1="850" y1="127" x2="850" y2="40" stroke-width="6"/>
    <line x1="707" y1="40" x2="993" y2="40" stroke-width="6"/>
    <!-- Dimension -->
    <line x1="0" y1="240" x2="1700" y2="240" stroke-width="1.5"/>
    <text x="850" y="285" text-anchor="middle" stroke="none" fill="currentColor">b = 17.00 m</text>
  </g>
</svg>

| Größe | Wert | Konf. |
|---|---|:---:|
| Spannweite *b* | 17.00 m | ✓ |
| Flügelfläche *S* | 17.95 m² | ✓ |
| Streckung *AR* | 16.1 | ✓ |
| Mittlere aerodynamische Tiefe *MAC* | 1.12 m | ✓ |
| Länge *L* | 8.35 m | ✓ |
| Höhe (overall) | 1.55 m | ✓ |
| Leermasse | 360 kg | ✓ |
| Referenzmasse (Polar) | **525 kg** | ✓ |
| MTOM (dual) | 600 kg | ✓ |
| L/D max | 34 @ 90 km/h | ✓ |
| Min sink | 0.65 m/s @ 74 km/h | ✓ |
| Stall (clean) | 65 km/h IAS | ✓ |
| V_NE | 280 km/h | ✓ |
| Lastvielfache (Utility, CS-22) | +5.3 g / -2.65 g | ◯ |
| Aerobatic placard @ V_A | +6.5 g / -4.0 g | ◯ |

---

# A. INPUTS

Reihenfolge entspricht dem Design-Workflow der App.

## A1. Mission Objectives

| Parameter | Wert | Einheit | Quelle | Konf. |
|---|---|---|---|:---:|
| Aircraft type | two-seat training & utility sailplane | — | Schleicher | ✓ |
| Crew | 2 (or 1 solo) | — | Schleicher | ✓ |
| Range / Endurance | not relevant (soaring) | — | — | — |
| Cruise speed (design) | 90 km/h IAS (≈ 25 m/s) | km/h | Idaflieg | ✓ |
| Stall speed (target, clean) | 65 km/h IAS | km/h | Schleicher | ✓ |
| Approach speed | 90 km/h IAS | km/h | Schleicher | ✓ |
| V_NE | 280 km/h IAS | km/h | Schleicher | ✓ |
| Manoeuvring V_A | 180 km/h IAS | km/h | Schleicher | ✓ |
| Field length | n/a (winch / aerotow) | — | — | — |
| Service ceiling | not certified-limited (typ. ≤ 6000 m AGL in wave) | — | — | — |
| Limit load factor (CS-22 Utility) | +5.3 g / -2.65 g | g | CS-22 Utility | ◯ |
| Placarded limit (aerobatic, @ V_A) | **+6.5 g / -4.0 g** | g | Wikipedia / Jane's | ◯ |
| Ultimate load factor | +7.95 g / -3.98 g | g | derived (1.5 × limit) | ◯ |
| Aerobatic category | Utility + limited aerobatics | — | Schleicher | ✓ |

> The ASK-21 has no propulsion mission. *Takeoff* is via winch or aerotow,
> not under own power. **Wenn die App ein Feld "Takeoff Field Length"
> verlangt: leer lassen oder n/a — dieser Use-Case existiert nicht.**

## A2. Design Assumptions

These are *initial estimates* the designer would enter before iterating
toward the analysis. They are intentionally rougher than the final values
in section B.

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Initial mass estimate *m* | 525 | kg | ✓ |
| Target CG location *x_CG* | 0.330 (≈ 33 % MAC from LE root) | m | ◯ |
| Target static margin | **15 %** MAC | — | ◯ |
| Assumed CL_max (clean) | 1.40 | — | ◯ |
| Assumed CD₀ | 0.012 | — | ◯ |
| Assumed Oswald *e* | 0.85 | — | ◯ |
| Load-factor limit *n_max* | +5.3 g | g | ✓ |

> Static margin and CG values are *targets* — the actual measured CG
> envelope is in **A6**.

## A3. Wing Configuration

The ASK-21 wing is a **double-trapezoidal planform** (inner section
near-rectangular, outer section tapered). For first-pass design entry,
an equivalent single-trapezoid approximation is acceptable; refine to
two sections if the app supports it.

### A3.1 Main wing — global parameters

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Span *b* | 17.00 | m | ✓ |
| Reference area *S* | 17.95 | m² | ✓ |
| Aspect ratio *AR* | 16.1 | — | ✓ |
| Taper ratio (c_tip / c_root) | 0.33 | — | ✓ |
| Sweep (quarter-chord) | ≈ 0° | ° | ◯ |
| Dihedral | **4.0** | ° | ✓ |
| Incidence (root) | **+2.0** | ° | ✓ |
| Twist (washout root→tip) | ≈ 2.0 (estimated, factory data not published) | ° | ? |
| Mean aerodynamic chord *MAC* | **1.12** | m | ✓ |
| MAC LE position aft of wing LE root | 0.008 | m | ✓ |
| Wing position on fuselage | mid-wing | — | ✓ |

### A3.2 Wing sections (entry into the wing editor)

| Station | y from centreline (m) | chord (m) | twist (°) | airfoil |
|---|---|---|---|---|
| Root (inner)| 0.00 | **1.50** | +2.0 | **Wortmann FX S 02-196** |
| Tip (outer) | 8.50 | **0.50** | ≈ 0   | **Wortmann FX 60-126** |

> **Profile selection — corrected from research:** The Schleicher
> Maintenance Manual §I.4 unambiguously specifies **two different
> airfoils**:
> - **Wortmann FX S 02-196** for the inner wing
> - **Wortmann FX 60-126** for the wingtip section
>
> The earlier "single-airfoil simplification" was an *unverified*
> assumption. For accurate analysis, model both airfoils with the
> transition at the inner/outer panel break (~y = 3 m).
>
> **Wing planform:** Schleicher gives only the inner chord (1.50 m)
> and outer/tip chord (0.50 m). The wing is *double-trapezoidal*
> but the exact break station and chord at break are not in the
> factory data. Single-trapezoid approximation gives S ≈ 17.0 m²
> vs the actual 17.95 m² — i.e., the inner panel is wider than a
> single-trapezoid approximation would suggest.

### A3.3 Control surfaces

| Surface | Span / area (each side) | Chord | Konf. |
|---|---|---|:---:|
| Aileron | **2.80 m span, area 1.12 m² (both ailerons total)** | inner 0.24 m → outer 0.16 m | ✓ |
| Airbrakes (Schempp-Hirth) | **0.35 m² each, 1.35 m span, 0.13 m height** | upper wing only | ✓ |
| Flaps | **none** | — | ✓ |

> The ASK-21 has **no flaps**. High-lift devices are limited to the
> Schempp-Hirth-style airbrakes for glide-path control. All values
> from Schleicher Maintenance Manual §I.4.

### A3.4 Wing planform (zur visuellen Prüfung)

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1900 600" width="720" stroke="currentColor" stroke-width="3" fill="none" font-family="monospace" font-size="30">
  <!-- spanwise axis horizontal, chordwise vertical -->
  <text x="20" y="40" font-size="34" stroke="none" fill="currentColor" font-weight="bold">WING PLANFORM (starboard half + root mirror)</text>
  <!-- centreline -->
  <line x1="950" y1="100" x2="950" y2="450" stroke-dasharray="6,4" stroke-width="1.5"/>
  <text x="965" y="115" stroke="none" fill="currentColor" font-size="22">centreline</text>
  <!-- starboard half: root LE at y=150, root TE at y=300 (chord 1.50m =150) -->
  <!-- break at y_LE=150, y_TE=270 (chord 1.20m =120) at x=950+300=1250 -->
  <!-- tip at x=950+850=1800, y_LE=150, y_TE=200 (chord 0.50m=50) -->
  <path d="M 950 150 L 1800 150 L 1800 200 L 1250 270 L 950 300 Z"/>
  <!-- port mirror -->
  <path d="M 950 150 L 100  150 L 100  200 L 650  270 L 950 300 Z"/>
  <!-- aileron region (outer 30% of half-span: from x=1300 to x=1800 starboard) -->
  <line x1="1300" y1="155" x2="1800" y2="155" stroke-dasharray="10,5" stroke-width="2"/>
  <text x="1500" y="135" stroke="none" fill="currentColor" font-size="22" text-anchor="middle">aileron region</text>
  <!-- airbrake region (mid-span ~x=1100-1180) -->
  <rect x="1100" y="180" width="80" height="15" fill="currentColor" stroke="none"/>
  <text x="1140" y="225" stroke="none" fill="currentColor" font-size="20" text-anchor="middle">airbrake</text>
  <!-- dimensions -->
  <line x1="950" y1="350" x2="1250" y2="350" stroke-width="1.5"/>
  <line x1="950"  y1="340" x2="950"  y2="360" stroke-width="1.5"/>
  <line x1="1250" y1="340" x2="1250" y2="360" stroke-width="1.5"/>
  <text x="1100" y="378" stroke="none" fill="currentColor" font-size="22" text-anchor="middle">inner panel y=0..3.0 m</text>
  <line x1="1250" y1="400" x2="1800" y2="400" stroke-width="1.5"/>
  <line x1="1250" y1="390" x2="1250" y2="410" stroke-width="1.5"/>
  <line x1="1800" y1="390" x2="1800" y2="410" stroke-width="1.5"/>
  <text x="1525" y="428" stroke="none" fill="currentColor" font-size="22" text-anchor="middle">outer panel y=3.0..8.5 m</text>
  <!-- chord labels -->
  <text x="970"  y="240" stroke="none" fill="currentColor" font-size="22">c_root = 1.50 m</text>
  <text x="1810" y="180" stroke="none" fill="currentColor" font-size="22">c_tip = 0.50 m</text>
  <line x1="1820" y1="500" x2="1820" y2="540" stroke-width="1.5"/>
  <text x="850" y="525" stroke="none" fill="currentColor" font-size="22">all dimensions in metres, viewed from above (TE at bottom)</text>
</svg>

## A4. Fuselage

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Overall length | 8.35 | m | ✓ |
| Cockpit (inner) width | **0.71** | m | ✓ |
| Cockpit (inner) height | **1.00** | m | ✓ |
| Cockpit length (tandem) | ≈ 2.30 | m | ◯ |
| Type of structure | composite (FRP) pod-and-boom | — | ✓ |
| **Fuselage wetted area** | **12.33** | m² | ✓ |
| Equivalent diameter (for drag) | ≈ 0.85 | m | ? |
| Wing carry-through location | x ≈ 2.7 m aft of nose | m | ? |

> Aerodynamically the rear fuselage is a long slender tail boom; the
> forward section is a wider canopy pod. For VLM the fuselage is
> usually represented as a body of revolution or omitted (contribution
> mostly via tail moment arm).

## A5. Tail Configuration

### A5.1 T-Tail layout

The ASK-21 uses a **T-Tail** — horizontal stabilizer mounted on top of
the vertical fin.

### A5.2 Horizontal stabilizer (mounted on top of V-fin)

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Span | **3.10** | m | ✓ |
| Area (incl. elevator) | **1.92** | m² | ✓ |
| Aspect ratio | **5.05** | — | ✓ |
| Mean chord (S / b) | ≈ 0.62 | m | ✓ |
| Sweep (LE) | ≈ 0° | ° | ◯ |
| Dihedral | 0° | ° | ✓ |
| Incidence | 0° | ° | ✓ |
| Airfoil | likely Wortmann family (factory data lists fin airfoil only) | — | ? |
| Tail arm *l_h* (CG → c/4 H-stab) | ≈ 4.40 | m | ? |
| Tail volume coefficient *V_h* | ≈ 0.45 (derived from geometry) | — | ? |

### A5.3 Vertical stabilizer

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Height above hull CL | **1.37** | m | ✓ |
| Area (fin only, excl. rudder) | **0.91** | m² | ✓ |
| Area (fin + rudder total) | **1.36** | m² | ✓ |
| Upper chord | **0.80** | m | ✓ |
| Lower chord (at hull) | **1.17** | m | ✓ |
| Airfoil | **Wortmann FX 71-L-150/30** | — | ✓ |
| Tail volume coefficient *V_v* | ≈ 0.022 (derived from geometry) | — | ? |

> **Schleicher's tail chord convention** uses upper/lower (not root/tip)
> because the V-fin tapers in the opposite sense from a typical wing:
> chord is *largest at the hull* (1.17 m) and *smallest at the top* (0.80 m).
> The V-fin uses the laminar **Wortmann FX 71-L-150/30** — *not* a NACA
> symmetric airfoil as previously assumed.

### A5.4 Control surfaces

| Surface | Span / area | Chord | Konf. |
|---|---|---|:---:|
| Elevator | full-span of H-stab, area **0.576 m²** | **30.1 %** of H-stab chord | ✓ |
| Rudder | full height of fin, area **0.45 m²**, mean chord **0.33 m** | **≈ 33 %** of fin chord | ✓ |
| Trim tab | on elevator | spring-trim, mechanical | ◯ |

## A6. Mass & CG / Weight Items

### A6.1 Mass states

| State | Mass (kg) | Quelle | Konf. |
|---|---|---|:---:|
| Empty | 360 | Schleicher | ✓ |
| Solo (one 85 kg pilot) | 445 | derived | ✓ |
| **Reference (Idaflieg polar)** | **525** | Idaflieg | ✓ |
| Dual (two 85 kg pilots) | 530 | derived | ✓ |
| MTOM | 600 | Schleicher | ✓ |

### A6.2 CG envelope

| Parameter | Wert | Einheit | Konf. |
|---|---|---|:---:|
| Datum (per Schleicher) | Wing LE at y = 0.4 m (NOT root rib) | — | ✓ |
| Forward CG limit (loaded) | **+234** (≈ 20.2 % MAC) | mm aft of datum | ✓ |
| Aft CG limit (loaded) | **+469** (≈ 41.1 % MAC) | mm aft of datum | ✓ |
| Typical loaded CG | +330 (≈ 30 % MAC) | mm aft of datum | ◯ |

> **Datum correction:** Schleicher uses a datum that is offset from
> the wing leading edge at the root rib. The factory CG envelope
> (234–469 mm) is referenced to **wing LE at y = 0.4 m from the
> aircraft centreline** — i.e., the leading edge measured at a span
> station 0.4 m outboard of the centreline. This was previously
> documented as "Wing LE at root rib" which is **technically wrong**.
>
> When entering CG into the app's `xyz_ref` field, use the same
> datum convention the app expects. If the app's datum is the nose,
> compute CG_app = (wing-LE-at-y=0.4m position from nose) + 0.234 to
> 0.469 m.

### A6.3 CG envelope diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 600" width="500" stroke="currentColor" stroke-width="2" fill="none" font-family="monospace" font-size="22">
  <text x="20" y="40" font-size="26" stroke="none" fill="currentColor" font-weight="bold">CG ENVELOPE — ASK-21</text>
  <!-- Axes -->
  <line x1="120" y1="500" x2="900" y2="500" stroke-width="2"/>
  <line x1="120" y1="500" x2="120" y2="100" stroke-width="2"/>
  <!-- x axis: CG position in mm aft of LE (240..500) -->
  <!-- y axis: mass (kg) 350..650 -->
  <!-- forward limit at 270, aft limit at 470 -->
  <!-- mapping: x = 120 + (cg-240)/(500-240)*780 -->
  <!--          y = 500 - (m-350)/(650-350)*400 -->
  <!-- Forward limit at cg=234: x = 120 + (234-220)/(500-220)*780 = 159 -->
  <line x1="159" y1="500" x2="159" y2="100" stroke-dasharray="6,4" stroke-width="1.5"/>
  <text x="159" y="90" text-anchor="middle" stroke="none" fill="currentColor" font-size="20">fwd 234</text>
  <!-- Aft limit at cg=469: x = 120 + (469-220)/(500-220)*780 = 814 -->
  <line x1="814" y1="500" x2="814" y2="100" stroke-dasharray="6,4" stroke-width="1.5"/>
  <text x="814" y="90" text-anchor="middle" stroke="none" fill="currentColor" font-size="20">aft 469</text>
  <!-- Permitted CG region (shaded) -->
  <rect x="159" y="100" width="655" height="400" fill="currentColor" opacity="0.07"/>
  <!-- Reference points -->
  <!-- Empty 360 kg, typ CG (assume 350 mm aft) -->
  <circle cx="450" cy="487" r="6" fill="currentColor"/>
  <text x="465" y="490" stroke="none" fill="currentColor" font-size="18">empty 360 kg</text>
  <!-- Solo 445 kg @ ~330 -->
  <circle cx="390" cy="360" r="6" fill="currentColor"/>
  <text x="405" y="365" stroke="none" fill="currentColor" font-size="18">solo 445</text>
  <!-- Reference 525 @ 330 -->
  <circle cx="390" cy="253" r="8" fill="currentColor"/>
  <text x="405" y="258" stroke="none" fill="currentColor" font-size="18">REF 525</text>
  <!-- MTOM 600 @ 360 -->
  <circle cx="450" cy="153" r="6" fill="currentColor"/>
  <text x="465" y="157" stroke="none" fill="currentColor" font-size="18">MTOM 600</text>
  <!-- Axis labels -->
  <text x="510" y="555" text-anchor="middle" stroke="none" fill="currentColor" font-size="22">CG position aft of LE-root (mm)</text>
  <text x="60" y="300" text-anchor="middle" stroke="none" fill="currentColor" font-size="22" transform="rotate(-90 60 300)">mass (kg)</text>
  <!-- X tick marks (range 220..500 mm) -->
  <text x="120" y="525" text-anchor="middle" stroke="none" fill="currentColor" font-size="18">220</text>
  <text x="510" y="525" text-anchor="middle" stroke="none" fill="currentColor" font-size="18">360</text>
  <text x="900" y="525" text-anchor="middle" stroke="none" fill="currentColor" font-size="18">500</text>
  <!-- Y tick marks -->
  <text x="105" y="505" text-anchor="end" stroke="none" fill="currentColor" font-size="18">350</text>
  <text x="105" y="305" text-anchor="end" stroke="none" fill="currentColor" font-size="18">500</text>
  <text x="105" y="105" text-anchor="end" stroke="none" fill="currentColor" font-size="18">650</text>
</svg>

### A6.4 Weight breakdown (typical, for entering into Weight Items)

| Item | Mass (kg) | Position x (m, aft of nose) | Konf. |
|---|---|---|:---:|
| Empty airframe | 360 | ≈ 2.90 | ◯ |
| Front pilot | 85 | ≈ 1.80 | ◯ |
| Rear pilot (optional) | 85 | ≈ 2.70 | ◯ |
| Parachute (per pilot) | 8 | as pilot | ◯ |

> The CG_x values **in metres aft of the nose** (not aft of LE) need to
> be computed by the user when entering weight items, since the app's
> datum may be the nose. The numeric difference is the distance
> nose → wing LE root, which is ≈ 2.70 m.

---

# B. EXPECTED OUTPUTS

Werte, die die App nach erfolgreicher Analyse zeigen *sollte*. Toleranzen
sind für **Tier B** gesetzt; Tier-C-Größen sind zusätzlich aufgelistet,
aber als optional markiert.

## B1. Aerodynamic Coefficients (Tier B)

| Größe | Erwarteter Wert | Toleranz | Quelle | Konf. |
|---|---|---|---|:---:|
| **CL_α** (whole aircraft, clean) | 5.4 1/rad ≈ 0.094 1/° | ±10 % | Idaflieg / analytisch | ◯ |
| **CL_max** (clean, low Re) | 1.40 | ±10 % | Schleicher (V_S) | ✓ |
| α at CL_max | ≈ 14 ° | ±2 ° | Idaflieg | ◯ |
| CL_0 | ≈ 0.30 | — | derived (FX S 02-196 camber) | ? |
| **CD₀** (zero-lift drag) | 0.010 – 0.014 | ±20 % | Idaflieg polar fit | ◯ |
| **Oswald factor *e*** | 0.85 – 0.95 | — | analytisch, hohe AR | ◯ |
| **L/D_max** | **34** | ±10 % | Schleicher / Idaflieg | ✓ |
| CL at L/D_max | ≈ 0.75 | ±15 % | derived | ◯ |
| CDi at CL=1.0 (induced drag) | ≈ 0.024 | ±15 % | analytisch | ◯ |

### B1.1 Reference polar points (from Idaflieg @ 525 kg)

| V (km/h IAS) | V (m/s) | Sink (m/s) | Glide ratio L/D | Konf. |
|---|---|---|---|:---:|
| 74 | 20.6 | 0.65 | 31.6 | ✓ |
| 90 | 25.0 | 0.74 | **34.0** | ✓ |
| 100 | 27.8 | 0.85 | 32.7 | ◯ |
| 120 | 33.3 | 1.20 | 27.8 | ◯ |
| 150 | 41.7 | 2.10 | 19.8 | ◯ |
| 200 | 55.6 | 4.50 | 12.3 | ◯ |

> Die App rechnet typischerweise in CL/CD vs α; zur Vergleichbarkeit
> kann die Polare über  `CL = 2 W / (ρ V² S)` und  `CD = CL · sink/V`
> umgerechnet werden, mit ρ = 1.225 kg/m³, W = 525 × 9.81 = 5150 N,
> S = 17.95 m².

## B2. Performance Points (Tier B)

| Größe | Erwarteter Wert | Toleranz | Quelle | Konf. |
|---|---|---|---|:---:|
| V_stall clean (CAS) | 65 km/h (18.1 m/s) | ±5 % | Schleicher | ✓ |
| V at min sink (CAS) | 74 km/h @ 525 kg (~67 km/h at lower weights) | ±5 % | Schleicher / Wikipedia | ◯ |
| V at best glide (CAS) | 90 km/h (25.0 m/s) | ±5 % | Schleicher | ✓ |
| Min sink rate | 0.65 m/s | ±10 % | Schleicher | ✓ |
| L/D max | 34 | ±10 % | Schleicher | ✓ |
| V_NE (CAS) | 280 km/h | — | Schleicher (Grenzwert) | ✓ |
| V_A maneuvering | 180 km/h | — | Schleicher | ✓ |

## B3. Stability (Tier C — optional aber mitgeliefert)

| Größe | Erwarteter Wert | Toleranz | Quelle | Konf. |
|---|---|---|---|:---:|
| Neutral point (stick-fixed) | ≈ 0.48 m aft of LE root (≈ 45 % MAC) | ±5 % MAC | analytisch | ? |
| Static margin (typical CG @ 0.33 m) | ≈ 15 % MAC | ±5 % MAC | analytisch | ? |
| CM_α (whole aircraft) | ≈ -0.8 1/rad | ±20 % | analytisch | ? |
| CM_q | ≈ -10 1/rad | ±30 % | analytisch | ? |
| CN_β | ≈ +0.07 1/rad | ±30 % | analytisch | ? |
| Cl_β | ≈ -0.08 1/rad (positives Dihedraleffekt) | ±30 % | analytisch | ? |
| Spiral mode | leicht konvergent oder neutral | — | typ. Segler | ◯ |
| Dutch roll damping | gut gedämpft | — | typ. Segler | ◯ |
| Phugoid period | ≈ 25–30 s @ V=90 km/h | ±20 % | analytisch | ? |

> Stability-Derivate für die ASK-21 sind **nicht** in einer
> öffentlichen Quelle in geprüfter Form publiziert (anders als
> Cessna 172 in Roskam). Die Tier-C-Werte sind daher mit großer
> Toleranz versehen und als „typisch hohe-AR-Segler" zu verstehen.
> Für strengere Validierung der Stabilitätsachse → bevorzugt mit der
> Cessna 172N arbeiten.

---

# C. Offene Punkte / Lower Confidence

Nach der Recherche-Iteration (Schleicher Maintenance Manual + Flight
Manual als Primärquellen) bleiben folgende Werte unverifiziert:

- **Wing twist / washout** — Schleicher veröffentlicht nur den
  Wurzel-Einstellwinkel (+2°). Der genaue Verlauf zum Tip ist nicht
  publiziert. Die hier verwendete Annahme 2° Washout ist heuristisch.
- **Wing planform-Knick (break station + chord)** — Schleicher gibt
  nur Innen-Tiefe (1.50 m) und Tip-Tiefe (0.50 m). Die genaue
  Position des Knicks ist nicht in den Werksdaten.
- **H-Stab Profil** — Maintenance Manual listet nur das Fin-Profil
  (FX 71-L-150/30); das HT-Profil wird nicht separat aufgeführt.
- **Tail arm l_h** und resultierende Tail-Volume-Coefficients
  *V_h*, *V_v* — nicht in den Werksdaten; geometrisch abgeschätzt
  aus Drei-Seiten-Riss-Proportionen.
- **CD₀** Bandbreite 0.010–0.014 — exakter Wert hängt von der
  Polar-Fit-Methode ab.
- **CL_α whole aircraft** — keine peer-reviewed Quelle, nur
  analytische Schätzung über AR-Korrektur.
- **Stabilitätsderivative** (gesamt B3) — bestätigt: **keine
  peer-reviewed öffentliche Quelle für ASK-21 existiert**. Für
  strenge Validierung der Stabilitätsachse → Cessna 172N verwenden.
- **Limit load factor (Konflikt)** — CS-22 Utility = +5.3 / -2.65 g;
  Schleicher placardiert +6.5 / -4 g bei V_A=180 km/h (per Jane's).
  Beide Werte sind je nach Definition gültig; vor Verwendung
  Schleicher POH §I.2 konsultieren.

---

# D. Smoke-Test-Hinweise

Beim manuellen Smoke-Test durch die App:

1. **Reihenfolge im UI** sollte A1 → A6 entsprechen. Wenn die App z. B.
   "Mission Objectives" nicht hat (gh-Issue), dann diesen Schritt
   überspringen — *aber notieren*.
2. **Einheiten** — die App verwendet `mm` in WingConfig und `m` in der
   DB. Achtung beim Eingeben von Wing-Sections.
3. **CL_max** der App ist meist eine **2D-Profilangabe** in Design
   Assumptions, nicht das 3D-Whole-Aircraft-CL_max. Tabelle B1.
   listet das **3D-Whole-Aircraft-CL_max**.
4. **Compare** das *Polar-Chart* der App optisch gegen die Werte in
   B1.1 — eyeballing ±10 % ist ausreichend für Smoke-Test.
5. Wenn die App den Neutralpunkt zeigt, prüfen ob er im Bereich
   **40–50 % MAC** liegt (s. B3).
