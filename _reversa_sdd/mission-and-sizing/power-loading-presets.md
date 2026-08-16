# Power loading (`power_to_weight`) for the mission presets

Status: analysis / proposal. **No code, seed data or migration is changed by
this document.**

## 1. The unit is W/kg — and only W/kg

`power_to_weight` is a design assumption whose unit is declared once, in the
assumption catalogue:

- `app/schemas/design_assumption.py:58` — `PARAMETER_UNITS["power_to_weight"] = "W/kg"`
- `app/schemas/design_assumption.py:78-86` — `PARAMETER_DEFAULTS["power_to_weight"] = 220.0`,
  documented in-place with a mission band chart
  (160–200 trainer/slow aerobatic · 200–240 sport aerobatic/scale · 240–290
  advanced aerobatic · 290–330 light 3D/EDF · 330–440 unlimited 3D · 0 = glider).

Two shipped presets already respect that unit and are pinned by tests:

- `motor_glider` → `power_to_weight = 100.0`
  (`app/tests/test_mission_preset_seed.py:52`, `:78`; gh-580)
- `flying_wing` → `power_to_weight = 100.0`
  (`app/tests/test_mission_preset_seed.py:109`, `:206`; gh-581)

The consumer confirms the unit: `_max_level_speed()` in
`app/services/assumption_compute_service.py:1868-1910` forms
`p_eta = power_to_weight * mass_kg * prop_eta` — i.e. an absolute power in
watts. A dimensionless thrust-to-weight number substituted there yields a
power of order 1 W for a 1 kg model, and `_max_level_speed` then returns a
meaningless V_max. The same expression also drives `is_glider = P/W <= 0`.

**T/W and W/kg are not inter-convertible.** P = T·V/η_prop, so a conversion
needs both an airspeed and a propeller efficiency, neither of which is a
property of the preset. The affected presets therefore have to be
**re-authored from mission knowledge**, not rescaled.

### Convention caveat (flagged, not resolved here)

The community "watts per kilo" charts — including the one quoted in
`design_assumption.py` — are **electrical input power** at full throttle (the
number a wattmeter reads). `_max_level_speed` multiplies `power_to_weight` by
`prop_efficiency` only, never by `propulsion_eta_motor` (0.85) or
`propulsion_eta_esc` (0.94), which exist as separate assumptions. Strictly
read, the code therefore treats the value as **shaft** power, which is
≈ 0.80 × the electrical chart value. All numbers below stay on the
**electrical-input convention**, because that is the convention the shipped
default of 220.0 W/kg was drawn from — changing the convention would silently
move the catalogue default too. This inconsistency deserves its own ticket.

## 2. Actual preset inventory

The presets live in `app/services/mission_preset_seed.py` (`SEED_PRESETS`).
There are **nine**, and the ids differ from the ones named in the task brief:
there is **no `glider` preset** — the unpowered missions are **`sailplane`**
and **`slope_soarer`**. There is also no `scale`/`warbird` preset. The real
ids are:

`trainer`, `sport`, `sailplane`, `wing_racer`, `acro_3d`, `stol_bush`,
`slope_soarer`, `motor_glider`, `flying_wing`.

Seven of the nine carry values in 0.0–1.4. Of those, **`sailplane` (0.0) and
`slope_soarer` (0.0) are already correct** — 0 is the same number in either
unit and is the intended "unpowered" sentinel. Only **five presets carry
genuinely T/W-shaped values** and need re-authoring.

## 3. Sources used

| Tag | Source |
|---|---|
| **[R]** | Roxxy/MULTIPLEX *Motoren-Fibel*, Ch. 1 pp. 8–9 — vault concepts `[[roxxy-angle-of-attack-stall-thrust]]`, `[[roxxy-pitch-diameter-ratio-by-aircraft-type]]` (thrust-to-weight targets per mission) |
| **[A]** | Same Fibel, worked AcroMaster example — vault `[[roxxy-power-voltage-current-mechanical]]` (12.6 V × 40 A ≈ 500 W) + `[[roxxy-propeller-power-calculation]]` (m = 1.4 kg) ⇒ **357 W/kg electrical** on a real aerobatic model |
| **[L]** | Andy Lennon, *Basics of R/C Model Aircraft Design*, Ch. 26 — vault `[[lennon-design-point-power-loading]]` (glow power loading in oz/cid: sport 210–260, powered glider 367 ⇒ a powered glider gets ≈ 0.6 × the sport power per unit weight) |
| **[C]** | The project's own in-code band chart, `app/schemas/design_assumption.py:78-85` |
| **[W]** | General RC-community rule of thumb "watts per pound" (50–70 W/lb trainer, ~100 W/lb sport aerobatic, ~150 W/lb 3D, 200+ W/lb unlimited; 1 W/lb = 2.205 W/kg). Widely used, no single citable page in the vault — treat as world knowledge. |

Confidence legend used in the table:

- **[ref]** — a number that appears in a source, essentially unchanged.
- **[der]** — derived from a source by an explicit calculation stated below.
- **[inf]** — my engineering inference; no source states this value.

## 4. Recommendation table

| preset id | current value | current unit | proposed W/kg default | typical range | rationale (source · confidence) |
|---|---|---|---|---|---|
| `trainer` | 0.5 | **T/W-shaped** | **160** | 120–200 | Bottom of the project's own trainer band [C]; the classic 50–70 W/lb rule puts a docile trainer at 110–155 W/kg [W], so 160 is the conservative overlap and the range reaches down to a light park-flyer trainer. Corresponds to T/W ≈ 0.6–0.8 with a large, slow prop. **[der]** |
| `sport` | 0.7 | **T/W-shaped** | **220** | 180–260 | Exactly the catalogue default [C] and the classic ~100 W/lb sport-aerobatic figure [W]. Keeping `sport` == the global default is deliberate: the "all-rounder" preset should not move the aircraft off the catalogue's own centre of gravity. **[ref]** |
| `sailplane` | 0.0 | W/kg (valid) | **0.0** (unchanged) | — | Unpowered. 0 is the `is_glider` sentinel (`P/W <= 0`, `assumption_compute_service.py:1892`). **[ref]** |
| `wing_racer` | 1.0 | **T/W-shaped** | **400** | 320–600 | Pylon / FPV racer: power buys speed, not static thrust. Level-flight check at the preset's own axes (m ≈ 1.5 kg, wing loading ≈ 200 g/dm² ⇒ S ≈ 0.075 m², CD0 ≈ 0.03, η_prop 0.65): V = 50 m/s needs ≈ 280 W/kg, V = 65 m/s ≈ 480 W/kg. 400 W/kg targets ≈ 58 m/s, mid-to-upper on the preset's 30–80 m/s cruise axis. Sits at/above the top catalogue band [C]. **[der]** |
| `acro_3d` | 1.4 | **T/W-shaped** | **350** | 290–450 | The Fibel requires T/W ≥ 1.5:1 to recover from a botched 3D attitude and 2:1 for "climbs as fast as it free-falls" [R]. At the 6–9 g/W static-thrust efficiency of a big low-pitch 3D prop, T/W = 2.0 ⇒ 2000 g/kg ÷ 6–9 g/W ⇒ **220–330 W/kg**; the Fibel's own AcroMaster runs **357 W/kg** [A]. 350 sits in the catalogue's "light 3D → unlimited 3D" bands [C]. **[der]** |
| `stol_bush` | 0.8 | **T/W-shaped** | **200** | 150–280 | STOL wants static thrust and a steep climb-out, not speed; a large slow prop delivers 8–12 g/W, so T/W ≈ 1.5 costs only 1500 g/kg ÷ 8–10 g/W ≈ **150–190 W/kg** [R-style reasoning]. 200 W/kg buys T/W ≈ 1.6–2.0 — enough for the preset's `field_friendliness = 1.0` and `climb = 0.6` targets. Bottom of the catalogue's sport/scale band [C]. **[der]** |
| `slope_soarer` | 0.0 | W/kg (valid) | **0.0** (unchanged) | — | Unpowered ridge-lift model; pinned by `test_mission_preset_seed.py:83` and `test_mission_objective_service.py:189` (gh-582). **[ref]** |
| `motor_glider` | 100.0 | W/kg (valid) | **100.0** (unchanged) | 80–150 | Already correct and test-pinned (gh-580). Independently corroborated: the Fibel gives T/W 0.7–1:1 for "kräftiger Steigflug" with a folding prop [R]; at the 10–13 g/W of a large, efficient folding prop that is 700–1000 g/kg ÷ 10–13 g/W ⇒ **60–100 W/kg**. Lennon's glow data agrees on the ratio: a powered glider gets ≈ 0.6 × the sport power loading [L] ⇒ 0.6 × 220 ≈ 130 W/kg upper bound. **[der — confirms the existing [ref] value]** |
| `flying_wing` | 100.0 | W/kg (valid) | **100.0** (keep — see §5) | 100–400 | Already in the right unit and pinned by gh-581 (`test_mission_preset_seed.py:109`). The number is defensible only for the slow / motor-assisted end of the class; genuinely mission-dependent, see below. **[inf]** |

Compact form (id → proposed W/kg): `trainer 160` · `sport 220` ·
`sailplane 0` · `wing_racer 400` · `acro_3d 350` · `stol_bush 200` ·
`slope_soarer 0` · `motor_glider 100` · `flying_wing 100`.

## 5. Presets where one number is genuinely not enough

**`flying_wing` — the widest spread of any preset.** "RC flying wing" covers a
slope-soaring floater (≈ 0–120 W/kg), an FPV cruising wing (≈ 180–280 W/kg),
and a 70 mm EDF or speed wing (≈ 400–600 W/kg). The shipped 100.0 W/kg sits at
the bottom of that spread — it satisfies the design intent recorded in the
gh-581 test ("defaults to powered so `is_glider` returns False") but under-powers
the FPV-wing case, which is arguably the most common modern build.

**Recommendation: leave `flying_wing` at 100.0 in this change set.** It is a
valid W/kg value, it is test-pinned, and raising it is a product decision about
which flying wing the preset represents — not a unit bug. If the value is later
raised (I would propose 200 W/kg), `test_flying_wing_preset_defaults`
(`app/tests/test_mission_preset_seed.py:109`) and
`test_mission_objectives_endpoint.py:112` must be updated with it. Worth its own
ticket.

**`wing_racer` — tension with its own axis ranges.** The preset's cruise axis
tops out at 80 m/s with `cruise` target = 1.0, i.e. the polygon asks for the top
of that range. At 80 m/s the same level-flight balance needs ≈ **700–800 W/kg**,
roughly twice the proposed default. Either the default is understood as "a fast
sport racer, not an F3D record attempt" (my reading, and the reason for 400) or
the cruise axis top should come down. Flagging, not resolving.

**`stol_bush`** is the preset most sensitive to the electrical-vs-shaft
convention of §1, because it is the one whose mission is defined by *static
thrust*, where the propeller efficiency term in `_max_level_speed` is least
meaningful.

## 6. Migration notes

Rows that change — **five**:

| id | change | factor |
|---|---|---|
| `trainer` | 0.5 → **160.0** | 320× |
| `sport` | 0.7 → **220.0** | 314× |
| `wing_racer` | 1.0 → **400.0** | 400× |
| `acro_3d` | 1.4 → **350.0** | 250× |
| `stol_bush` | 0.8 → **200.0** | 250× |

Rows that stay unchanged — **four**: `sailplane` (0.0), `slope_soarer` (0.0),
`motor_glider` (100.0), `flying_wing` (100.0).

Notes for whoever implements this:

1. **`sailplane` and `slope_soarer` must stay exactly 0.0.** They are not
   "unconverted T/W values"; 0 is the sentinel that makes
   `is_glider = power_to_weight <= 0` true
   (`app/services/assumption_compute_service.py:1892`). Any positive value
   would switch a glider to the powered V_max path and enable powered-only UI
   chips. Guarded by `test_mission_preset_seed.py:29`, `:82-83`,
   `test_mission_objective_service.py:115`, `:189`,
   `test_mission_objectives_endpoint.py:78`.
2. `SEED_PRESETS` is consumed by an Alembic **data** migration
   (`alembic/versions/7fd2cf7284ce_mission_tables_presets_objectives.py` and the
   per-preset follow-ups). Editing the seed module alone does not update an
   already-migrated database — a new data migration that UPDATEs the five rows
   is required, and existing aeroplanes that already applied a preset carry
   their own `design_assumptions` rows which the migration will not touch.
   Decide explicitly whether existing aircraft are re-stamped or left alone.
3. Two tests hard-code an old-shape value and will need review:
   `app/tests/test_mission_objective_schema.py:78` (`power_to_weight=0.5` — a
   schema-construction fixture, probably harmless but now misleading) and
   `app/tests/test_epic_485_acceptance.py:469` (`200.0` for powered aircraft —
   consistent with this proposal).
4. After the change, every preset value lies inside a documented band of the
   catalogue chart at `app/schemas/design_assumption.py:78-85`, so the chart
   and the presets stop contradicting each other. That mutual consistency is
   the main acceptance criterion — more than any individual number.

## 7. What is *not* backed by a hard reference

Stated plainly, so nobody reads more precision into this than exists:

- The vault (rcplanedesigner.com, Lennon, RC-Network wiki, Roxxy Motoren-Fibel)
  contains **no W/kg-per-mission table**. Its power-sizing guidance is expressed
  as **thrust-to-weight** [R] and, for glow engines, as **oz/cid** [L].
- The only measured W/kg data point in the vault is the AcroMaster at
  **357 W/kg** [A] — one aircraft, one class.
- Every other number above is a **derivation** from those T/W figures via an
  assumed static-thrust efficiency (6–13 g/W depending on prop size and pitch),
  or a **level-flight power balance** using the preset's own axis ranges, or the
  project's own band chart [C]. The static-thrust efficiencies are my inference
  **[inf]** from general RC practice, not vault values.
- Ranges are deliberately wide (±25–50 %). A preset default is a starting
  estimate that the powertrain compute is meant to replace — `power_to_weight`
  is explicitly *not* in `DESIGN_CHOICE_PARAMS`
  (`app/schemas/design_assumption.py:34-36`), i.e. it is expected to be
  superseded by a calculated value later.
