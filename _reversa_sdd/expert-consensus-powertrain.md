# Expert Consensus — Powertrain / Propulsion Open Questions

**Scope of judgement.** Every answer below is judged for a design tool serving
**hobby RC and UAV aircraft**: roughly 0.5–15 kg all-up mass, electric
propulsion (brushless outrunner + ESC + LiPo + fixed or folding propeller),
one private pilot, typical operating altitude 0–1000 m. Methods that are
correct for transport-category aircraft but invalid at this scale are called
out as such and rejected.

**Authority hierarchy applied** (per project `CLAUDE.md`):

1. `aircraft-design-scholz` — lead authority (Scholz HAW Hamburg / Sadraey,
   *Aircraft Design: A Systems Engineering Approach*, Wiley 2013)
2. `aerodynamics-expert` — physics ground truth (Anderson, *Fundamentals of
   Aerodynamics* 6e)
3. `aerosandbox-expert`, `avl-advisor` — implementation tools
4. `rc-aircraft-designer` — RC practice, **lower authority**
   (rcplanedesigner.com, Lennon 1996, RC-Network Wiki, ROXXY *Motoren-Fibel*,
   plus vaulted Drela `motor1`/`QPROP` theory and Coates 2019 UAV propulsion
   system-ID)

Source labels used throughout: **[academic]**, **[physics]**,
**[RC practice]**, **[tool]**, **[repo data]** (measured from the 454-propeller
APC dataset and the 41-motor / 19-ESC D-Power catalogue shipped in this repo),
**[derived]** (my own calculation from the above).

---

## Q-PT-1 — ESC selection criterion

### Question

`_find_matching_esc` must return a single, reproducible ESC. On what criterion?
Continuous-current headroom over which load case, what burst rule, what
voltage/cell-count limit, what BEC requirement — with concrete margins.

### What the code does today

`app/services/powertrain_sizing_service.py:104-113` returns the **first** ESC in
unordered query order whose `continuous_current_a` ≥ the caller's
`min_current_a`; the call site (`:259`) passes **`cruise_current_a`**, i.e. the
battery current in level cruise at *nominal* pack voltage. No burst check, no
cell-count check, no BEC check, no ordering. The parallel solution-space
endpoint uses a different rule entirely: `esc_min = i_peak × esc_margin` with
`esc_margin` defaulting to **1.4** and `i_peak` taken at *sag* voltage
(`app/schemas/powertrain_solution_space.py:59-63`).

### Scholz / analytical view — [academic]

Sadraey treats propulsion-system component selection as a **constraint
satisfaction over the whole flight envelope**, not over the cruise point: the
sizing load case for any propulsion component is the most demanding segment
(take-off / climb), because that is where shaft power and hence current peak
(Sadraey ch. 8, propulsion system design procedure). Nothing in the academic
corpus endorses sizing a current-carrying component to cruise current. The
vault has **no ESC-specific content** — the ESC is below the granularity of
conceptual aircraft design — so the lead authority decides the *load case* but
delegates the *margins* to RC practice.

### RC practice view — [RC practice], with catalogue evidence

RC-Network Wiki, *Motorsteller*: the continuous-current rating is "the most
important specification"; manufacturers rate it under a stated cooling
assumption and "cheap imports sometimes advertise peak (pulse) capacity, which
is substantially higher than continuous rating" — so continuous and burst are
**separate gates**, and burst must never substitute for continuous. Maximum
voltage is specified as "the **maximum unloaded** battery terminal voltage",
i.e. the cell-count check must use **4.2 V/cell**, not 3.7 V nominal. BEC
output current "is a critical specification for selecting an appropriately-sized
controller".

The shipped catalogue makes three traps concrete **[repo data]**:

| ESC | cont. A | burst A | cells | BEC | mass |
|---|---|---|---|---|---|
| Antares 6A BEC | 6 | 8 | 2–3S | 1.0 A | 6 g |
| Antares 25A BEC | 25 | 35 | 2–4S | 2.0 A | 19 g |
| **Antares 85A OPTO** | 85 | 100 | 2–6S | **none** | **47 g** |
| **Antares 85A SBEC 5A** | 85 | 100 | 2–6S | 5.0 A | 57 g |
| **AVICON PRO 65A HV** | 65 | 80 | **6–14S** | 8.0 A | 120 g |
| AVICON 100A | 100 | 120 | 2–6S | 8.0 A | 80 g |

- Burst/continuous across the catalogue is **1.18–1.50** — so burst headroom is
  *not* free and must be checked explicitly.
- `Antares 85A OPTO` is **10 g lighter** than the SBEC at identical current. A
  naive "pick the lightest" rule selects an ESC that **cannot power the
  receiver**.
- `AVICON PRO 65A HV` has `cells_lipo_min = 6`. The cell window is **two-sided**;
  a one-sided "≤ max" check hands a 3S design an ESC that will not run.

ESC mass scales tightly with rating (6 A → 6 g … 100 A → 80 g), so "lightest"
and "smallest sufficient" almost always coincide — which is exactly why the
tie-break has to be written down rather than left to query order.

### Physics note

The ESC is a thermal device: loss ≈ I²·R_ds(on) + switching loss. Both the
sizing quantity (I) and the failure mode (junction temperature) are driven by
the **peak sustained** current, and thermal time constants for a 30–100 g ESC
are tens of seconds — far longer than a full-throttle climb. Cruise current is
therefore the wrong load case by construction, not merely by convention.

### CONSENSUS

Replace the first-match rule with an **all-of gate plus a deterministic sort**.

**Design current** `I_design` = the largest sustained battery current in the
mission, evaluated at **sag voltage (3.5 V/cell)**, not nominal. Where the
sizing path has no throttle sweep, use the motor as the limiter:
`I_design = max(I_peak_computed, motor.max_current_a)`.

**Gates (all must pass):**

1. `esc.continuous_current_a ≥ 1.4 × I_design`
   — 1.4 matches `esc_margin` already defaulted in the solution space; unify on
   it (this also closes half of Q-PT-8). **1.2 is the absolute floor** for a
   well-cooled, uncowled installation; 1.4 is the default; expose it as a
   user-editable assumption.
2. `esc.max_current_a ≥ 1.0 × I_design_burst`, where `I_design_burst =
   motor.max_current_a`. If `max_current_a` is NULL, treat burst as **equal to
   continuous** — never assume the catalogue-typical 1.3×.
3. `esc.cells_lipo_min ≤ S ≤ esc.cells_lipo_max` — **two-sided**, and verify
   `S × 4.2 V ≤ esc.max_voltage_v` when that field exists.
4. **BEC gate**, conditional on the design declaring servo power from the ESC:
   `bec_current_a ≥ 0.3 A × n_servos` continuous, and the required BEC voltage
   (5 V / 6 V flags) offered. An OPTO ESC (`bec_current_a` NULL) is admissible
   **only** when the design declares a separate receiver supply. This gate must
   run **before** the sort — otherwise the mass sort picks the OPTO.

**Sort among survivors:** `mass_g` ascending → `continuous_current_a` ascending
→ `id` ascending. Fully deterministic, and mass feeds the same wing-loading /
stall chain as Q-PT-2. Cheapest is not selectable — there is no price column.

**Null handling:** `esc_id = null` must carry a reason
(`no_esc_required` vs `no_esc_fits`, with the binding gate named). Today the UI
cannot tell the two apart; that is a contract defect, not a cosmetic one.

### Disagreement

None on substance. The only tension is the *margin value*: RC practice has no
single number (vendors quote 1.2–2.0), while the repo's own solution space
already committed to 1.4. Scholz decides the **load case** (peak, not cruise);
RC practice supplies the **margin**; the repo's existing 1.4 breaks the tie in
favour of internal consistency.

### Confidence — **high**

Load case and gate structure are decided by first principles and confirmed by
the catalogue. Only the 1.4 multiplier is a convention rather than a derivation.

---

## Q-PT-2 — Propeller mass in the sizing total

### Question

Should the chosen propeller's mass enter `total_mass`? And should a NULL
`mass_g` on any component reject the candidate?

### What the code does today

`powertrain_sizing_service.py:233` — `total_mass = request.airframe_mass_kg +
motor_mass_kg + battery_mass_kg`. Propeller mass is absent although
`propeller_polars.weight_g` now carries real masses (gh-1000/1017). Lines
212–213 use `(motor.mass_g or 0) / 1000.0`, so a NULL mass **silently
contributes zero**.

### Scholz / analytical view — [academic]

Unambiguous. Sadraey eq. (10.9) defines the installed engine weight as
"the weight of the engine itself plus all installation hardware — firewall,
mount, cowl, nacelle, pylon, inlet, starting system, **and propeller(s) for
prop-driven aircraft**", and states explicitly: *"For propeller-driven
aircraft, the equation also includes propeller weight in the installed engine
total."* The propulsion group mass is a first-class term in the empty-weight
buildup that feeds W/S and the cg calculation.

**But the equation does not transfer to this scale [derived].** Applying
eq. (10.9) — `W_E_ins = K_E · (N_E · W_E)^0.9`, `K_E = 3` in SI — to an 80 g RC
outrunner (W_E = 0.785 N) yields `3 × 0.785^0.9 = 2.41 N ≈ 246 g`, i.e. **3.1×
the bare motor mass**. `K_E` is dimensional and calibrated on GA-size engines;
the regression is far outside its validity range. Take the **principle**
(propeller mass belongs to the propulsion group), reject the **formula**.

### RC practice view — [RC practice] + [repo data]

RC builders weigh the propeller. Measured medians from the shipped APC dataset:

| Diameter | median mass |
|---|---|
| 4–6 in | 4.2 g |
| 6–8 in | 9.9 g |
| 8–10 in | 21.2 g |
| 10–12 in | 29.5 g |
| 12–14 in | 44.3 g |
| 14–17 in | 70.3 g |
| 17–30 in | 133.1 g |

Effect on the quantities the total feeds **[derived]**:

| Case | prop | % of AUM | Δ wing loading | Δ stall speed |
|---|---|---|---|---|
| 0.8 kg park flyer, 8×4 | 21 g | 2.6 % | +2.6 % | +1.3 % |
| 1.5 kg sport, 10×5 | 30 g | 2.0 % | +2.0 % | +1.0 % |
| 3 kg e-glider, 12×6 | 44 g | 1.5 % | +1.5 % | +0.7 % |
| 5 kg UAV, 16×8 | 70 g | 1.4 % | +1.4 % | +0.7 % |

1–3 % of AUM. Small — but it is **one-signed**: omitting it always
under-predicts mass, wing loading and stall speed. A systematic optimistic bias
in a stall-speed number shown to a hobbyist is the wrong direction to be wrong
in. Note also that `weight_g` is the **bare blade** mass; spinner, adapter and
bolts are extra and are not in the dataset.

### Physics note

`V_stall ∝ √(m)`, so the stall-speed error is half the mass error — the table
above is the exact propagation, not an estimate.

### CONSENSUS

**Yes — include propeller mass.** Add `prop_mass_kg` to `total_mass`, sourced
from `propeller_polars.weight_g` for the selected propeller. Report it as a
separate line item in the response so the user can see the four terms
(airframe / motor / battery / propeller).

**Do not** apply Sadraey's installation factor. Instead expose an optional
`prop_installation_mass_g` assumption (spinner + adapter), **default 0**, and
document that `weight_g` is the bare blade. Inventing a scaled-down `K_E` would
be a fabricated number.

**NULL mass must never contribute zero.** Replace `(x.mass_g or 0)` with an
explicit policy:

- Emit an **`error`-severity `DesignWarning`** naming the component and field
  (the warning policy already exists — reuse it).
- **Exclude the candidate from the ranked list**, and return it in an
  `excluded` array with the reason. Dropping it silently and returning a
  confident flight time computed from a wrong mass is worse than returning
  nothing.

Note this creates a dependency: sizing currently selects motor + battery + ESC
but not a propeller. Either (a) select a propeller in the same pass — which
Q-PT-3 needs anyway — or (b) accept a user-supplied `prop_mass_kg` and warn when
it is absent. **(a) is preferred**; the two questions share the same fix.

### Disagreement

None. Scholz and RC practice agree; they differ only on whether an installation
factor applies, and the scale argument settles that against the factor.

### Confidence — **high**

Inclusion is decided by the lead authority and the magnitudes are measured from
the shipped data. Only the spinner/adapter allowance is left open, deliberately.

---

## Q-PT-3 — Kv from the APC polar database

### Question

`_PHASE1_PROP_DIAMETER_M = 0.30` was a placeholder awaiting #615, which has
shipped. Should the solution-space Kv now be derived from the polar database,
and what is the physically correct way to pair Kv with a propeller at this
scale?

### What the code does today

`powertrain_solution_space_service.py:157-159`:

```
prop_d     = 0.30                                   # fixed, all aircraft
rpm_target = (v_top_mps / (prop_d * prop_pd)) * 60
kv_approx  = rpm_target / (v_nom * load_rpm_factor) # load_rpm_factor = 0.85
```

Setting `n = V / (D · P/D)` is identical to asserting **J = P/D** at top speed.
`prop_pd` defaults to 0.65.

### Scholz / analytical view — [academic]

Two constraints bound the answer:

1. **Diameter follows from power, not from a constant.** Sadraey eq. (8.13):
   `D_P = K_np · √( 2·P·η_P·AR_P / (ρ·V_av²·C_LP·V_C) )`. Diameter is an output
   of the power and speed requirement. A single fixed 0.30 m across a 0.5–15 kg
   range has no basis.
2. **Tip speed is the binding constraint on RPM**, hence on Kv.
   `V_tip,cruise = √(V_tip,static² + V_C²)`, and Sadraey's tip-speed table gives
   **150 m/s for "plastic prop for RC model aircraft"** — the single most
   directly applicable academic number in the corpus for this tool. Any Kv
   recommendation that implies a tip speed above it is invalid regardless of how
   it was derived.

Sadraey's own worked method matches the propeller to the engine via a **gearbox
ratio** (eq. 8.14). Direct-drive electric has no gearbox — **Kv is the gear
ratio**. That is the correct conceptual mapping.

### RC practice view — [RC practice]

ROXXY *Motoren-Fibel*: `no-load RPM = Kv × V`; under realistic model-flight
loading brushless motors run at **≈ 85 % of no-load RPM** — this is exactly the
existing `load_rpm_factor = 0.85`, and it is correct. High-Kv motors pair with
small propellers, low-Kv with large; for a fixed frame size, turns × Kv ≈
const, so cell count and Kv trade against each other at constant power.

Practical tip-Mach target **Ma ≈ 0.4–0.6** (≈ 130–200 m/s), with efficiency
collapsing above Ma ≈ 0.6–0.7.

P/D by mission: 3D ≈ 0.5, scale ≈ 0.6–0.7, glider/e-sailplane ≈ 0.7–0.9. The
code's default 0.65 is well placed for "trainer/scale".

### Physics note + [repo data] — where the real error is

I measured the actual relation between the geometric pitch ratio and the
operating advance ratio across all 454 shipped APC propellers:

| relation | p10 | median | p90 |
|---|---|---|---|
| `J` at max efficiency ÷ (pitch/diameter) | 0.900 | **0.951** | 1.035 |
| `J` at zero thrust ÷ (pitch/diameter) | 1.138 | 1.238 | 1.393 |
| max propulsive efficiency `Pe` | 0.655 | **0.786** | 0.846 |

So the code's implicit `J = P/D` is only **~5 % off** the best-efficiency point —
the *pitch* model is fine. (APC's geometric pitch is defined near 75 % radius,
which is why it lands close to the effective pitch.) Zero thrust sits at
J ≈ 1.24 × P/D, comfortably clear.

**The error is entirely in the fixed diameter.** Since `J = V/(nD)`, holding
D at 0.30 m scales the RPM — and therefore Kv — by `0.30 / (0.95 · D_true)`:

| true prop | Kv error of the Phase-1 estimate |
|---|---|
| 6 in (0.152 m) | **−108 %** (true Kv ≈ 2.1× the estimate) |
| 8 in (0.203 m) | −56 % |
| 10 in (0.254 m) | −24 % |
| 12 in (0.305 m) | −4 % (the placeholder's design point) |
| 16 in (0.406 m) | +28 % (estimate too high) |

The placeholder is accurate only for ~12 in props and is off by a factor of two
at the small-model end of the target range.

Separately: `DEFAULT_ETA_PROP = 0.65` (`endurance_service.py:53`) equals the
**p10** of the measured APC maximum efficiencies, i.e. the worst propeller's
best point. The median is 0.786 — squarely inside Sadraey's η_P = 0.75–0.85
band for full-scale props.

### CONSENSUS

**Yes — derive Kv from the polar database. The blocker is resolved and the
placeholder is wrong by up to 2× at the small end.**

Correct chain (all quantities already available):

1. **Size the diameter from the power requirement**, not from a constant. Either
   Sadraey eq. (8.13), or — better, since the data is one table away — select the
   propeller from `propeller_polars` whose polar delivers the required thrust at
   the design speed within the disk-loading and tip-speed limits.
2. **Get the operating advance ratio from that propeller's own polar**: take
   `J` at the maximum `Pe` row nearest the design RPM band. Fall back to
   `J = 0.95 × (pitch/diameter)` when a polar is missing — a measured
   relation, not a guess.
3. `n = V_design / (J · D)`; check the tip speed:
   `V_tip = √((π·D·n)² + V²) ≤ 150 m/s` **[Sadraey, RC plastic prop]**. Reject
   or re-select if violated.
4. `Kv = n_rpm / (V_nom × 0.85)` — keep `load_rpm_factor = 0.85`
   **[RC practice, confirmed]**.
5. Use the selected propeller's **`Pe` at that `J`** as `eta_prop` instead of
   the constant 0.65, and its **`weight_g`** for Q-PT-2.

Report the selected propeller (name, D, P, mass) alongside the Kv so the
recommendation is inspectable, and drop the "Phase 1 / approximate" caveat from
the schema description once the polar path is live. Keep the fixed-diameter
formula only as a documented fallback for the case of an empty polar table.

### Disagreement

Mild, on the tip-speed ceiling: Sadraey says **150 m/s** for RC plastic props;
ROXXY practice says Ma ≈ 0.4–0.6, i.e. **130–200 m/s**. The hierarchy resolves
it: **Scholz wins → cap at 150 m/s** (≈ Ma 0.44), which sits inside the RC band
anyway. Use the RC upper end only as a "you are past the recommended limit"
warning threshold, not as the gate.

### Confidence — **high**

The 0.951 and 1.238 ratios are measured across the full shipped dataset with
tight spread, and the diameter-error table follows algebraically.

---

## Q-PT-6 — Winding resistance (Rm) for the QPROP motor model

### Question

`rm_ohm` is absent from every seeded D-Power motor, so the QPROP 3-parameter
model is dormant catalogue-wide. Is a data source needed, and what is the
accepted way to obtain or estimate Rm for hobby brushless motors?

### What the code does today

`powertrain_performance.py:104-122` — `rm_ohm` is optional;
`uses_qprop_model` is True only when `rm_ohm > 0`. All 41 seeded motors have
`rm_ohm` NULL **[repo data]**, so every production curve runs the fixed-RPM
approximation, and the response note advertises the missing refinement
(`:795`). The other two of the three parameters **are** present: the catalogue
carries `kv_rpm_per_volt` and `io_no_load_a` (0.4–0.7 A across the AL series).
Rm is the only gap.

### Scholz / analytical view — [academic]

Out of scope. Electric motor internal parameters are below the granularity of
conceptual aircraft design; Sadraey's only remark on electric propulsion is that
"the weight of the battery and fuel cells is determined separately and added to
the engine weight". No conflict — the lead authority simply does not speak here,
which pushes the decision down the hierarchy to the tool/practice layers.

### RC practice view — [RC practice], Drela + Coates

This is Drela's canonical model, and the vault carries the theory directly.

*Drela `motor1` §1.1* — the three-parameter model:
`V = i·R + Ω/Kv`, `Q_m = (i − i₀)/K_Q`, with `K_Q = K_v` in the ideal case.
Described as "the workhorse of RC electric propulsion analysis" and valid
"across typical RC operating speeds and currents". i₀ is "typically 0.5–2 A for
small RC motors" — consistent with the 0.4–0.7 A in the shipped catalogue.

*Drela `motor1` §2, measurement protocol* — the accepted way to obtain R:

1. **Milliohmmeter** across the terminals, or
2. **Locked-rotor V–i**: hold the shaft, sweep terminal voltage, `R = v/i`,
   averaged over shaft positions.

Critical caveat carried in the same source: **cold resistance under-predicts
hot resistance** (copper has a positive temperature coefficient). "For accurate
motor modeling under load, hot resistance should be used."

*Coates 2019 (UAV propulsion system ID)* — R and k_E can be fitted **in situ**
from telemetry with no datasheet at all, via the voltage balance
`U_dd·δ_t = R·I_a + k_E·ω`, solved as a two-parameter linear least squares over
(ω, I_a) samples. Validated on a **Hacker A40-12S V2** (spec Kv = 610 rpm/V,
spec R = 0.031 Ω): fitted k_E → Kv = 712.6 rpm/V, fitted **R = 0.0587 Ω**,
R² = 0.9971. The fitted R is ~1.9× the motor spec because **it includes ESC and
cable resistance** — the source notes the result is "typically a few percent
higher than the motor datasheet value"; in this validation it was far more.
Samples should be weighted by `I_a²` because unmodelled ESC switching and eddy
losses degrade the fit at light load.

### Physics note — how much does R actually change? [derived]

Copper loss is `I²R`. For a 3S (11.1 V) motor:

| current | R = 0.05 Ω | R = 0.10 Ω |
|---|---|---|
| 5 A (55 W) | 1.3 W = 2 % | 2.5 W = 5 % |
| 20 A (222 W) | 20 W = **9 %** | 40 W = **18 %** |

An Rm uncertainty of ±0.05 Ω moves motor efficiency by ~9 points at 20 A and
~3 points at 5 A. So Rm matters, and it matters **most exactly where the sizing
constraints bind** (climb, full throttle). It is not a cosmetic refinement.

Note also that the i₀ loss is `i₀·V` ≈ 0.7 A × 11 V ≈ 7.7 W — for a 122 W
input that is 6 %, comparable to copper loss at moderate current. Having i₀
without R gives you the model's *smaller* term only.

### CONSENSUS

**Yes, a data source is needed — and Rm should be sourced, not synthesised.**
Ranked, adopt in this order:

1. **Publish-side sourcing (preferred).** Many hobby vendors publish internal
   resistance (Hacker, Kontronik, AXi, Scorpion, T-Motor commonly list `Ri`
   in mΩ). D-Power does not. Add `rm_ohm` to the importer's spec vocabulary and
   populate it wherever the source has it. This is a data-coverage task, not a
   modelling task.
2. **Fit from a published bench table.** Where a vendor publishes ≥ 2 operating
   points with (voltage, current, RPM) — as static-thrust tables often do — run
   the Coates voltage-balance regression. Two rows suffice for the two-parameter
   fit. Store the result with `rm_source = "fitted"`.
3. **Locked-rotor measurement** for motors the user physically owns. If the tool
   ever grows a "measure my motor" input, Drela's §2 protocol is the recipe:
   R by locked-rotor V–i averaged over shaft positions, i₀ at representative
   RPM free-spinning, Kv from `Ω/(v − i₀R)`.
4. **Do not estimate Rm from Kv and i₀ alone.** The three parameters are
   independent; there is no derivation from the other two. The physically
   motivated scaling `R ∝ 1/(Kv²·m_motor)` (turns N: `Kv ∝ 1/N`, `R ∝ N²`) is
   real but needs a per-frame-family calibration constant that the repo does not
   have — a single anchor point cannot establish it. **If** a fallback is ever
   shipped, it must be marked `rm_source = "estimated"` and surfaced as a
   `DesignWarning`, never silently.

**Two clarifications that change what "Rm" means in this code:**

- The parameter QPROP wants for an ESC-driven system is the **circuit**
  resistance (winding + ESC + cable), not the motor-only datasheet value. The
  Coates validation showed 0.031 Ω (motor) vs 0.0587 Ω (circuit) — a ~90 %
  difference that dwarfs the modelling gain of switching from the fixed-RPM
  approximation to QPROP. Name the field's meaning explicitly and, if the value
  came from a motor datasheet, either add the ESC/cable term or document that
  the model runs optimistic.
- Datasheet R is **cold**. Under a full-throttle climb the winding runs
  50–80 K hotter, and copper's temperature coefficient (~0.0039 /K) raises R by
  **20–30 %**. Either accept the optimism and document it, or apply a hot-resistance
  correction as an explicit, user-visible assumption.

**Interim behaviour is acceptable.** The fixed-RPM approximation is not wrong,
it is coarse; keeping it as the fallback with the existing honest note
(`:795`) is the right posture until coverage exists. What is *not* acceptable is
having the note claim a follow-up ticket that never lands.

### Disagreement

None between the sources. The only tension is internal to RC practice: Drela's
protocol yields the **motor** resistance, Coates' fit yields the **circuit**
resistance, and the code has one field. Since the code models a full electric
drivetrain, **the circuit interpretation is the correct one** — but it must be
labelled, because the two differ by ~2× in the one validated case available.

### Confidence — **high** on the method and the ranking;
**medium** on whether item 1 (vendor coverage) is achievable across the
catalogue — that is a data-availability question this analysis cannot settle.

---

## Q-PT-9 — ISA atmosphere in the powertrain

### Question

`_air_density = 1.225·exp(−h/8500)` is duplicated in `powertrain_performance`
and `powertrain_sizing_service`, while the aero stack uses `asb.Atmosphere`
(ISA). At RC/UAV altitudes (0–1000 m), what actually matters — is ISA overkill
or correct?

### What the code does today

`powertrain_performance.py:346-348` and a duplicate in
`powertrain_sizing_service` implement an exponential (isothermal) atmosphere
with an 8500 m scale height. `RHO_DEFAULT = 1.225` is also hard-coded in the
solution space (`:65`). Three places, two models.

### Scholz / analytical view — [academic]

Sizing and performance methods in the corpus are written against the **ISA**
throughout (matching chart, field length, ceiling, Breguet), and the density
ratio σ = ρ/ρ₀ is the standard carrier of altitude effects. There is no
academic endorsement of an exponential approximation at any scale — it is a
convenience, not a method.

### Physics note — how big is the error? [derived]

Exponential (scale height 8500 m) vs ISA barometric:

| altitude | ρ exponential | ρ ISA | error |
|---|---|---|---|
| 0 m | 1.2250 | 1.2250 | 0 % |
| 200 m | 1.1965 | 1.2017 | **−0.43 %** |
| 500 m | 1.1550 | 1.1673 | **−1.05 %** |
| 1000 m | 1.0890 | 1.1116 | **−2.03 %** |
| 2000 m | 0.9682 | 1.0065 | −3.81 % |
| 3000 m | 0.8607 | 0.9091 | −5.33 % |

Now the term the code ignores entirely — **temperature**:

| condition (sea level) | ρ | deviation | equivalent density altitude |
|---|---|---|---|
| ISA +10 K (25 °C) | 1.1839 | −3.4 % | **354 m** |
| ISA +15 K (30 °C) | 1.1644 | −4.9 % | **526 m** |
| ISA +20 K (35 °C) | 1.1455 | −6.5 % | **694 m** |
| ISA +30 K (45 °C) | 1.1095 | −9.4 % | **1020 m** |

**A warm summer afternoon at sea level is worth more density altitude than the
entire 0–1000 m geometric band.** The exponential-vs-ISA error at 500 m is
1.0 %; the hot-day error at the same field is 5–6 %. The tool is currently
precise about the small term and silent about the large one.

### RC practice view — [RC practice]

Density altitude is standard hobby knowledge for anyone flying from a summer
field or at elevation ("hot and high" hurts electric climb noticeably). The
vault has no quantitative RC treatment — it is a physics/tool question, not a
practice question.

### Tool view — [tool]

`asb.Atmosphere` is already a dependency and already used by the aero stack.
Verified against the installed AeroSandbox **4.2.9**:

```
Atmosphere(altitude: float = 0.0,
           method: Literal['differentiable','isa'] = 'differentiable',
           temperature_deviation: float = 0.0)
```

and it exposes `.density()`, `.temperature()`, `.speed_of_sound()`,
`.dynamic_viscosity()` and `.density_altitude()`. Measured:
ρ(0) = 1.22500, ρ(200) = 1.20149, ρ(500) = 1.16685, ρ(1000) = 1.11077 — i.e. the
ISA column above. Everything needed is already installed, including the
`temperature_deviation` knob and a `density_altitude()` reporter.

**One constraint:** `aerosandbox` is excluded on `linux/aarch64` by pyproject
environment markers (root `CLAUDE.md`, `app/CLAUDE.md`). The powertrain module
must not acquire a hard `import aerosandbox`.

### CONSENSUS

**Use ISA — but the reason is consistency and the temperature hook, not
accuracy at 500 m.**

1. **Delete both copies of the exponential** and the third hard-coded
   `RHO_DEFAULT`. Two atmosphere models in one aircraft's calculation is a
   defect regardless of the size of the discrepancy, and it will surface as an
   unexplainable few-percent mismatch between the aero page and the powertrain
   page for the same aircraft.
2. **Introduce one shared helper**, e.g. `app/services/atmosphere.py`, exposing
   `density(altitude_m, temperature_deviation_k=0.0)`. Implement it as
   `asb.Atmosphere(altitude=h, temperature_deviation=dT).density()` when
   AeroSandbox imports, with a **closed-form ISA barometric fallback**
   (`ρ = 1.225·(1 − 2.25577e-5·h)^4.2559`, corrected for ΔT via the ideal gas
   law) when it does not. Four lines, no new dependency, honours the aarch64
   platform guard, and removes the second model.
3. **Expose `temperature_deviation_k` as a design assumption**, default 0.
   This is the change that actually improves answers at RC scale — it is 3–6×
   larger than the model error it replaces.
4. **Report density altitude** in the powertrain response
   (`atmo.density_altitude()`). It is the number an RC/UAV pilot can act on,
   and it makes the temperature assumption visible rather than buried.

**Is ISA overkill?** No — it costs nothing (already a dependency, already
computed elsewhere) and removes a duplicate model. But it is also **not where
the accuracy is**: shipping ISA without the temperature knob would be precision
theatre. Ship both or the change is not worth making.

### Disagreement

None. Scholz, physics and the tool all point the same way; RC practice is
silent on the model and loud on density altitude, which is exactly the emphasis
the consensus adopts.

### Confidence — **high**

The error magnitudes are computed, and the AeroSandbox API was verified against
the installed version rather than assumed.

---

## Q-PT-10 — Windmilling / stopped-propeller drag

### Question

`Ct` is clamped at 0, so a power-off or descent point reports **zero propeller
drag**. Is that acceptable for the RC/UAV mission set? For a glider or
motor-glider with a folding vs fixed prop, how large is the effect, and does it
belong in the drag budget?

### What the code does today

`powertrain_performance.py:328-332` — `Ct_interp = max(Ct_interp, 0.0)`,
documented as discarding "the slightly-negative tail past zero-thrust"
(UAT note, gh-615 #4). Thrust is likewise clamped at `:748`. So `T ≥ 0` always,
and glide performance on a powered aircraft is optimistic by the full
propeller-drag term.

### Scholz / analytical view — [academic]

The Scholz/Sadraey vault is **thin here** — a single mention, that an
inoperative engine causes "increased drag from the windmilling or feathered dead
engine" in the multi-engine safety context. That is a real gap in the corpus for
this question, and I flag it rather than paper over it.

What the corpus **does** decide: Sadraey lists **folding propellers** as one of
the five propeller families, defined by their purpose — *"used on motor gliders
to reduce drag in engine-off flight"*. The lead authority therefore recognises
power-off propeller drag as a **first-order design driver** — significant enough
that an entire propeller family exists to eliminate it. A drag budget that
reports it as exactly zero contradicts the reason the hardware exists.

Sadraey's drag decomposition is additive and component-based
(`C_D,P = C_D,0 + ΔC_D,flap + ΔC_D,slat + ΔC_D,gear`), with the landing-gear
increment ΔC_D,gear = 0.015 — "equal to the entire clean C_D,0 for some
aircraft". The correct *shape* of the fix is therefore a **ΔC_D increment on the
aircraft polar**, exactly like the gear term — not a change to the propeller
thrust model.

### Physics note — [physics] + Drela QPROP theory

The clamp is physically false at the model level. Drela's QPROP formulation,
which this code implements, treats the windmill branch as a first-class regime:
*"For a **windmill** with negative thrust and torque: v_a and v_t are
negative."* Negative `Ct` past the zero-thrust advance ratio is the physics, not
numerical noise. (Coates 2019 likewise **pre-filters windmilling regions** out
of identification data precisely because they are a distinct, real regime.)

Magnitude bounds:

- **Freewheeling (zero shaft torque) propeller** — actuator-disk theory gives
  the ceiling. Drela QPROP §5.3: the maximum extractable windmill power is
  `P_max = (8/27)·ρ·V³·πR²`, which occurs at induction factor a = 1/3, where
  `T = (4/9)·ρ·A·V²`. Referred to disk area and `q = ½ρV²`, that is
  **C_D,disk = 8/9 ≈ 0.89** — the hard theoretical ceiling **[derived from the
  vaulted relation]**. A fine-pitch RC prop freewheeling at low torque sits far
  below it, realistically **C_D,disk ≈ 0.05–0.2**.
- **Stopped propeller** — bluff-body drag on the blade planform. Anderson gives
  C_D ≈ **2.0** for a flat plate normal to the flow and **1.2** for a circular
  cylinder; a stopped blade broadside sits in that bracket, referenced to
  **blade** area (~0.0065 m² for a 2-blade 12 in prop), not disk area.
- **Folded / feathered** — effectively zero; this is the case the current clamp
  accidentally models correctly.

Worked example, 3 kg electric glider, S = 0.6 m², V = 12 m/s, clean L/D = 20,
12 in propeller (disk area 0.073 m² = 12 % of wing area), clean drag 1.47 N
**[derived]**:

| propeller state | drag | as % of clean drag | resulting L/D |
|---|---|---|---|
| folded | ≈ 0 | ≈ 0 % | 20.0 |
| freewheeling, C_D,disk = 0.05 | 0.32 N | 22 % | **16.4** |
| freewheeling, C_D,disk = 0.10 | 0.64 N | 44 % | **13.9** |
| freewheeling, C_D,disk = 0.20 | 1.29 N | 88 % | **10.7** |
| stopped broadside, C_D = 1.2 on blade area | 0.69 N | 47 % | 13.6 |
| theoretical ceiling, C_D,disk = 8/9 | 5.72 N | 389 % | 4.1 |

**A windmilling propeller costs 20–45 % of the glide ratio on a typical RC
electric glider.** That is not a rounding error — it is the difference between
a 20:1 and a 14:1 sailplane, and it is exactly why folding props exist.

### RC practice view — [RC practice]

RC-Network Wiki, *Luftschraube*: *"Folding propellers are particularly common
on sailplane engines. After the powered climb phase, the blades fold streamlined
against the fuselage or motor pylon … to reduce drag when not in use."* And
*Motorsteller*: ESC **motor braking** exists specifically so that "when using
folding propellers, undesired motor spin-down is prevented" — the whole
brake-then-fold sequence is standard RC equipment built to avoid the windmilling
state. Fixed props are chosen "where the motor runs continuously in flight and
streamlining through blade folding is not required".

RC practice thus confirms the three-state model (folded / stopped / windmilling)
as the real operational taxonomy, but supplies **no measured coefficients** —
that gap is real and I flag it rather than invent numbers.

### CONSENSUS

**Not deliberately out of scope — it is a genuine gap, and it matters for
exactly the mission the tool targets (motor-gliders and e-sailplanes). But do
not fix it by unclamping `Ct`.**

1. **Keep `max(Ct, 0)` in the propeller performance path.** The clamp is
   defensible there: the APC polars' negative tail is sparse and low-precision,
   and the powered performance curve does not need it. Removing it would let
   low-quality extrapolated data leak into thrust numbers.
2. **Add an explicit propeller-state drag increment on the aircraft drag
   polar**, in the shape of Sadraey's ΔC_D,gear term:
   `ΔC_D0,prop = k_prop · (A_disk / S_ref)`, with a `prop_state` enum:

   | `prop_state` | `k_prop` (on disk area) | note |
   |---|---|---|
   | `running` | 0 | thrust model already covers it |
   | `folded` / `feathered` | **0.00–0.01** | current behaviour, correct |
   | `stopped_braked` | **0.02–0.05** | blades edge-on / behind fuselage |
   | `windmilling` | **0.05–0.20**, default **0.10** | free-spinning fixed prop |

   Hard physical ceiling `k_prop ≤ 8/9` — reject any user override above it.
   Ranges are **[physics-derived brackets, not measurements]** and must be
   labelled as such in the UI, with the value user-overridable.
3. **Default `prop_state` by propeller type**: a folding propeller in the
   catalogue → `folded`; a fixed propeller on a design with a glide/L-D
   requirement → `windmilling`; otherwise `stopped_braked`.
4. **Scope it to the glide/power-off analyses.** Cruise, climb and top-speed
   points are unaffected — the propeller is producing thrust there. This is a
   drag-budget and glide-ratio feature, not a performance-curve feature.
5. **Make it a design lever, not just a correction.** The single most valuable
   output is the comparison in the table above: "folding prop buys you +6 points
   of L/D on this airframe". That is a real design decision the tool can now
   support, and it is the payoff that justifies the work.

### Disagreement

**Scholz vs the current code** — Sadraey defines a whole propeller family by
the need to eliminate this drag; the code reports it as zero. Scholz wins.
**RC practice vs physics** on magnitude — RC practice has the taxonomy but no
numbers; physics supplies the bounds. No contradiction, only a coverage gap,
which is why the recommended coefficients are given as ranges with a derived
ceiling rather than as point values.

### Confidence

**High** that windmilling drag belongs in the drag budget for glider/motor-glider
work, and that the clamp should stay in the thrust path.
**Medium** on the specific `k_prop` values — they are bracketed by actuator-disk
theory and bluff-body data, but no measured RC propeller drag data exists in any
consulted source. Treat them as defaults to be calibrated, and say so in the UI.

---

## Q-PT-12 — Propeller-polar data integrity

### Question

Two items in the bundle, in order of the brief: (a) is an `inertia_kg_m2`
plausibility guard sensible, and what range should it check for 5–20 in hobby
propellers? (b) should a content hash replace `source_version` as the freshness
proxy?

### What the code does today

`prop_polar_enrich.py:29,88-100` — `weight_g` has a guard
(`MIN_PLAUSIBLE_WEIGHT_G = 1.0`, below which the value is rejected as a
suspected unit error); `inertia_kg_m2` is written straight through with **no
guard at all**, from the same PE0 parse. `prop_polar_import.py:68-79` —
`_records_equal` compares `source_version` and skips the record when it matches;
the docstring already concedes that "if APC corrects polar data WITHOUT bumping
source_version, the correction is silently skipped".

### (a) Inertia plausibility guard

#### Physics note — the guard writes itself [physics]

For any rigid body, `I = m·r_g²`, so the dimensionless group

```
k = I / (m · D²) = (r_g / D)²
```

has an **exact physical ceiling**: the radius of gyration of a propeller cannot
exceed the tip radius, `r_g ≤ R = D/2`, hence

```
0 < k ≤ 0.25    (k = 0.25 ⟺ all mass concentrated at the blade tips)
```

This is not a heuristic — it is a hard bound that any correct
(mass, diameter, inertia) triple must satisfy. A guard can therefore be written
without reference to any dataset.

#### Measured range — [repo data]

Across all 453 shipped APC propellers that carry both mass and inertia:

| statistic | `k = I/(m·D²)` |
|---|---|
| min | 0.0204 |
| p1 | 0.0246 |
| p5 | 0.0257 |
| **median** | **0.0404** |
| p95 | 0.0578 |
| max | 0.0676 |

i.e. `r_g/D ∈ [0.14, 0.26]`, or `r_g` between **0.29 R and 0.52 R** — exactly
what a tapered blade with a solid hub should give. The band is remarkably tight
across a 5× diameter range, which is what makes it a good validator.

Absolute values by size band **[repo data]**:

| diameter | I min | I median | I max | mass median |
|---|---|---|---|---|
| 4–6 in | 1.0e-6 | 3.0e-6 | 6.0e-6 | 4.2 g |
| 6–8 in | 3.0e-6 | 1.0e-5 | 2.8e-5 | 9.9 g |
| 8–10 in | 9.0e-6 | 3.1e-5 | 6.2e-5 | 21.2 g |
| 10–12 in | 2.3e-5 | 8.0e-5 | 1.7e-4 | 29.5 g |
| 12–14 in | 6.7e-5 | 1.67e-4 | 2.96e-4 | 44.3 g |
| 14–17 in | 1.92e-4 | 3.85e-4 | 8.78e-4 | 70.3 g |
| 17–30 in | 5.22e-4 | 1.244e-3 | 8.539e-3 | 133.1 g |

Fitted scaling: **I ≈ 0.0317 · D^4.58** (D in m, I in kg·m²), residual spread
p1–p99 = 0.40×–2.39× (full range 0.35×–2.61×). The near-D⁵ exponent is the
expected combination of `m ∝ D³` and `r_g² ∝ D²` plus a mild solidity trend.

#### CONSENSUS (a)

**Yes, add the guard — and make it a two-tier check, mirroring the `weight_g`
guard rather than inventing a new pattern.**

**Tier 1 — absolute sanity (always applicable, catches unit errors):**

```
1e-7 kg·m²  ≤  inertia_kg_m2  ≤  1e-2 kg·m²
```

For the 5–20 in target band the observed data spans **1e-6 … 3e-3**; the limits
above give roughly a decade of headroom either side, which is enough to admit
anything real and still catch the classic failure — a value parsed in g·cm²
(off by 1e-7), oz·in² (off by ~1.8e-5) or lb·ft² (off by ~0.042). Those are the
errors that actually occur in a PE0 text parse, and every one of them lands
outside this window.

**Tier 2 — dimensionless consistency (when mass and diameter are both known):**

```
0.010  ≤  I / (m · D²)  ≤  0.10        (reject outside)
0.018  ≤  I / (m · D²)  ≤  0.075       (warn outside)
```

The reject band is ~2× wider than the observed 0.0204–0.0676 on both sides and
still sits well inside the hard physical bound of 0.25. The warn band brackets
the observed p1/p99 with a small allowance. Tier 2 is the stronger test: it
catches an inertia that is internally inconsistent with its own mass and
diameter even when both are individually plausible — which Tier 1 cannot do.

**Failure policy — match the existing `weight_g` behaviour exactly:** log with
the propeller name and the offending value, **drop the field** (leave
`inertia_kg_m2` NULL) rather than importing a wrong number, and **count it in a
per-file skip tally** (see below). Do not reject the whole record — the polar
samples are still good.

**Also add the missing symmetric check on the mass side:** `MIN_PLAUSIBLE_WEIGHT_G
= 1.0` has no upper bound. The largest shipped propeller is 133 g median in the
17–30 in band; a `MAX_PLAUSIBLE_WEIGHT_G` of ~2000 g would catch a kg/g unit
inversion at negligible risk. The asymmetry looks like an oversight rather than
a decision.

### (b) Content hash vs `source_version`

#### CONSENSUS (b)

**Add a content hash; keep `source_version`. They answer different questions and
neither substitutes for the other.**

- `source_version` is a **claim by the publisher** about provenance. It is the
  right thing to display to a user ("APC data, PER3 rev X"), to record in an
  audit trail, and to reason about when deciding whether a dataset is
  *supported*. It is **not** evidence about the bytes.
- A content hash is a **fact about the bytes**. It is the only thing that can
  correctly answer "did this record change?" — which is precisely the question
  `_records_equal` is asking. The docstring already documents the failure mode
  (a silent APC correction without a version bump); a hash closes it by
  construction.

**Concretely:**

1. Store a `content_hash` per propeller record — SHA-256 over the canonical
   serialisation of the fields that matter (the sample rows plus the enriched
   `weight_g` / `inertia_kg_m2` / geometry), with stable key ordering and fixed
   float formatting so the hash is reproducible across Python versions.
2. `_records_equal` decides on the **hash**. `source_version` becomes a stored,
   displayed attribute — updated whenever the record is, never a gate.
3. Store a **snapshot-level hash** of `apc_props.json.gz` too. The bundle's
   second bullet is correct that the snapshot is currently the only integrity
   boundary and nothing checksums it: a hand-edited archive imports without
   complaint. A single file-level digest, committed alongside the snapshot and
   verified at import, fixes that for the cost of three lines.
4. Keep `force` as the manual override; the hash makes it needed far less often.

**Cost note:** hashing 454 records × ~50 sample rows is milliseconds. There is
no performance argument for the version proxy.

### On the remaining three bullets (brief mention, as scoped)

- **Skipped records counted but not enumerated** — confirmed defect. An import
  that silently misses a corrected dataset must leave an auditable trace. Emit a
  structured per-file report (`file`, `skip_reason`, `record_id`), and add the
  missing **per-file counter for short/malformed rows** so a systematically
  broken source file reads as an error rather than as a smaller propeller. This
  is the same failure class as the NULL-mass issue in Q-PT-2: silence where a
  warning belongs.
- **`Torque_Nm` / `Thrust_N` stored and never used** — confirmed hazard. They
  are the low-precision columns the Ct/Cp physics deliberately avoids, and their
  presence invites a future consumer to read exactly the wrong thing. Either
  drop them, or rename with an explicit `_raw_lowprec` suffix and document that
  the dimensional path is `T = Ct·ρ·n²·D⁴`. A comment in the model is not
  enough — the column name is the API.

### Disagreement

None. This question has no academic/practice axis; it is decided by physics
(the `r_g ≤ R` bound), by the shipped data, and by ordinary data-integrity
engineering.

### Confidence — **high**

Both the physical bound and the empirical band are derived from the actual
shipped dataset, and the hash recommendation follows from the failure mode the
code's own docstring already documents.

---

## Summary table

| Q-id | Recommendation in one line | Confidence |
|---|---|---|
| **Q-PT-1** | Gate on peak (not cruise) current at sag voltage: `cont ≥ 1.4 × I_design`, `burst ≥ motor.max_current_a`, two-sided cell window at 4.2 V/cell, BEC gate **before** the sort; then sort lightest → smallest → id, and return a *reason* when `esc_id` is null. | high |
| **Q-PT-2** | Yes — add propeller `weight_g` to `total_mass` (1–3 % of AUM, always one-signed on stall speed); do **not** apply Sadraey's GA installation factor at this scale; a NULL mass must raise an error-severity warning and exclude the candidate, never contribute zero. | high |
| **Q-PT-3** | Yes — the fixed 0.30 m placeholder is up to 2× wrong at 6–8 in; size D from power, take `J` from the selected propeller's polar (fallback `J = 0.95 × P/D`, measured), cap tip speed at 150 m/s, keep `load_rpm_factor = 0.85`, and take `eta_prop` and `weight_g` from the same propeller. | high |
| **Q-PT-6** | Rm must be **sourced, not synthesised**: vendor `Ri` where published → Coates voltage-balance fit from bench tables → locked-rotor measurement; never derive it from Kv and i₀. Model the **circuit** (motor+ESC+cable, ~2× motor-only) and note that datasheet R is cold (+20–30 % hot). Keep the fixed-RPM fallback with its honest note meanwhile. | high (method) / medium (coverage) |
| **Q-PT-9** | Yes to ISA — one shared helper wrapping `asb.Atmosphere` with a closed-form ISA fallback (aarch64 guard), deleting all three duplicate density paths — **but ship `temperature_deviation` and `density_altitude()` with it**: a hot day is worth 350–1000 m of density altitude, 3–6× the model error being fixed. | high |
| **Q-PT-10** | Not deliberately out of scope — a windmilling prop costs **20–45 % of glide ratio** on a typical RC e-glider. Keep `max(Ct,0)` in the thrust path; add a `prop_state` drag increment on the aircraft polar (`k_prop` on disk area: folded 0–0.01, stopped 0.02–0.05, windmilling 0.05–0.20 default 0.10, hard ceiling 8/9). | high (belongs in budget) / medium (coefficients) |
| **Q-PT-12** | Yes to the inertia guard, two-tier: absolute `1e-7 … 1e-2 kg·m²`, plus dimensionless `0.010 ≤ I/(m·D²) ≤ 0.10` (observed 0.0204–0.0676; hard physical ceiling 0.25) — drop the field and count the skip on failure. Add a **content hash** for the freshness decision and keep `source_version` for provenance; checksum the snapshot too. | high |

---

### Sources consulted

**Academic (lead authority)** — `aircraft-design-scholz`: Sadraey,
*Aircraft Design: A Systems Engineering Approach* §8.7 (propeller aerodynamics,
sizing eq. 8.2–8.14, tip-speed limit table incl. 150 m/s for RC plastic props,
propeller families incl. folding), §10 (installed engine weight eq. 10.9,
propeller mass in the propulsion group), §5.4 / Loftin (additive drag buildup,
ΔC_D,gear precedent).

**Physics ground truth** — `aerodynamics-expert`: Anderson, *Fundamentals of
Aerodynamics* 6e — bluff-body drag coefficients (flat plate normal C_D ≈ 2.0,
cylinder ≈ 1.2, streamlined ≈ 0.12), hydrostatic equation, low-Re airfoil flow.
**Noted gap:** Anderson does not cover propeller/actuator-disk theory; that
material came from the vaulted Drela QPROP theory in the RC skill.

**RC practice (lower authority)** — `rc-aircraft-designer`: RC-Network Wiki
(*Motorsteller*, *BEC*, *Luftschraube*, *Klapptriebwerk*); ROXXY
*Motoren-Fibel* ch. 1 (Kv/RPM/voltage, 85 % load RPM factor, tip Mach ≈ 0.5,
P/D by mission); Lennon, *Basics of R/C Model Aircraft Design* ch. 18;
**Drela `motor1` theory §1.1, §2** (three-parameter model, benchtop measurement
protocol, hot-vs-cold resistance); **Drela QPROP theory §1.1, §5.3**
(velocity decomposition and the windmill sign convention; MTP / max windmill
power); **Coates 2019** UAV propulsion system identification §II.D, §V.A
(voltage-balance fit for R and k_E, Hacker A40-12S validation).

**Tool** — `aerosandbox-expert` + direct verification against the installed
AeroSandbox **4.2.9**: `asb.Atmosphere(altitude, method, temperature_deviation)`
and `.density_altitude()`.

**Repo data** — `db/test.db`: 453 APC propeller polars with mass and inertia,
454 with polar samples; 41 D-Power brushless motors (0 with `rm_ohm`, all with
`kv_rpm_per_volt` and `io_no_load_a`); 19 ESCs with continuous/burst current,
cell window, BEC current and mass. Code read at
`app/services/powertrain_sizing_service.py`,
`app/services/powertrain_solution_space_service.py`,
`app/services/powertrain_performance.py`,
`app/services/prop_polar_import.py`, `app/services/prop_polar_enrich.py`,
`app/services/endurance_service.py`,
`app/schemas/powertrain_solution_space.py`.
