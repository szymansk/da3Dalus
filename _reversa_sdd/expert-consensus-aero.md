# Expert consensus — aerodynamics & geometry accuracy

**Scope.** Nine open questions from `_reversa_sdd/questions.md`, ruled on for a
design tool serving **hobby RC and UAV** aircraft: ~0.5–15 kg, Re 50 000–500 000,
3D-printed or wood-built, one private pilot. Methods are judged on validity *at
that scale*, not on transport-category practice.

**Sources and authority.** The project's authority hierarchy is followed
throughout:

1. `aircraft-design-scholz` — lead authority (Scholz HAW Hamburg lectures;
   Sadraey, *Aircraft Design: A Systems Engineering Approach*, Wiley 2013).
2. `aerodynamics-expert` — physics ground truth (Anderson, *Fundamentals of
   Aerodynamics* 6e).
3. `aerosandbox-expert`, `avl-advisor` — implementation tooling.
4. `rc-aircraft-designer` — RC practice, lower authority (Lennon, *Basics of R/C
   Model Aircraft Design*; RC-Network Wiki; rcplanedesigner.com).

Every source is labelled inline as **[academic]**, **[tooling]** or
**[RC practice]**. Numbers I computed myself from repository data are labelled
**[computed here]** and are reproducible from the stated inputs.

**No code was changed.** This document is the only file written.

---

## Q-VI-8 — Camber loss on OpenVSP import (#791); VLM cost (#792)

### Question

Two benchmark findings. **#791**: the importer appears to lose airfoil camber —
a `C_L0` offset of ≈ 0.43 on the DG-101G but only 0.07 on the Titan Falcon.
How serious is this, what exactly does it do to `CL(α=0)` and `CM`, and is it
shippable? **#792**: x-section augmentation makes the ASB VLM intractable —
215 s per solve on a 31-xsec Cessna. Is the accuracy worth the runtime at this
scale?

### What the code does today

`openvsp_airfoil.import_airfoil_from_xsec` dispatches on XSec shape: analytical
NACA 4/5/6/16-series branches rebuild a `.dat` from the shape parms; every other
shape (including `XS_FILE_AIRFOIL`, which is what the DG-101G wing uses) goes
through `_export_selig` → `vsp.WriteSeligAirfoil(tmp, geom_id, u)`, a re-export
sampled off the **lofted surface** at parametric station `u`
(`app/converters/openvsp_airfoil.py:903-948`). Separately, the wing handler
hard-codes the root section's `twist=0.0`
(`app/converters/openvsp_wing_handler.py:916`) and applies the geom XForm
rotation **only to `xs.xyz_le`**, never folding it into `twist`
(`:1033-1036`).

### Physics / analytical view

Anderson's thin-airfoil theory for a cambered section **[academic]** gives the
three results that decide how serious this is (Anderson §4.8–4.9, via
`[[thin-airfoil-theory-cambered]]`, `[[aerodynamic-center-quarter-chord-point]]`):

```
α_L0 = −(1/π) ∫₀^π (dz/dx)(cos θ₀ − 1) dθ₀          (zero-lift angle)
c_l  = 2π (α − α_L0)                                 (lift curve)
A_n  = (2/π) ∫₀^π (dz/dx) cos(n θ₀) dθ₀              (camber Fourier coeffs)
c_m,c/4 = (π/4)(A₂ − A₁)                             (Anderson Eq. 4.64)
```

Read off the consequences:

- **`c_lα` = 2π regardless of camber.** Losing camber does **not** change the
  lift-curve slope.
- **`c_m,c/4` depends only on `A₁`, `A₂` — camber-line shape, independent of α.**
  So the aerodynamic centre stays at c/4, `dC_m/dα` is untouched, and therefore
  **the neutral point and the static margin are untouched.**
- Only **`α_L0`** (hence `C_L(α=0)`) and **`C_m0`** move.

**This is the triage that matters: a camber error is a pure offset error.**
Stability numbers survive it. Trim, cruise α, required wing incidence, and
`(L/D)` at a given α do not.

> ⚠️ **Source discrepancy.** The `aerodynamics-expert` vault page
> `[[thin-airfoil-theory-cambered]]` renders the moment result as
> `c_m,c/4 = −π(A₁/2)`. That does not reproduce measured data (it would give
> −0.47 for the FX 61-184 below, against a published ≈ −0.13). Anderson's
> Eq. (4.64), `c_m,c/4 = (π/4)(A₂ − A₁)`, is the correct form and is what I
> used. The vault page's *conclusion* — that `c_m,c/4` is α-independent and the
> ac is at c/4 — is right either way.

### Quantifying it on the actual DG-101G geometry **[computed here]**

The benchmark model's own source sections are stored verbatim inside
`components/aircraft/vsp/dg101g.vsp3` (`<FileAirfoil><UpperPnts>/<LowerPnts>`).
Evaluating the integrals above on those coordinates:

| Source section | max camber | t/c | `α_L0` | 2-D `c_l0` | `A₁` | `A₂` | `c_m,c/4` |
|---|---|---|---|---|---|---|---|
| FX 61-184 (inboard) | 3.09 %c @ 0.63c | 18.4 % | **−6.05°** | 0.664 | 0.2978 | 0.0877 | **−0.165** |
| FX 60-126 (outboard) | 3.56 %c | 12.6 % | **−4.68°** | 0.513 | 0.2400 | 0.0787 | **−0.127** |

Both codes agree on `C_Lα` to 1.7 % (0.102 vs 0.104 /deg), so the wing's true
inviscid `C_L0 = C_Lα · |α_L0|` must land in **0.48 … 0.63**, depending on where
the FX 60-126 blend starts. (A VLM sees only the camber line, so thin-airfoil
theory and VLM should agree closely on `α_L0` for the same section — this is a
like-for-like prediction, not a correction-laden one.)

Against the benchmark's measurements:

| | `C_L0` | implied `α_L0` | error vs geometry |
|---|---|---|---|
| Geometry (thin-airfoil / VLM-equivalent) | 0.48 – 0.63 | −4.7° … −6.1° | — |
| ASB VLM (importer's `.dat`) | 0.44 | −4.3° | **≈ 0.4–1.7° too little** |
| VSPAERO (native `.vsp3` section) | 0.87 | −8.4° | **≈ 2.3–3.7° too much** |

**This materially rewrites the ticket.** #791 frames VSPAERO as truth and
attributes the full ΔC_L0 = 0.43 to the importer. The geometry says otherwise:
the importer loses roughly **0.10–0.17 in `C_L0`** (≈ 1–1.7° of `α_L0`, i.e.
~20–28 % of the camber's zero-lift contribution), and **VSPAERO overshoots by
more than the importer undershoots**. The catalogue's claim that this "would make
every imported aircraft's lift curve wrong at α = 0" is directionally right but
over-stated by roughly 2.5×, and it is wrong to call the surviving discrepancy
entirely an importer defect.

### Where the loss most plausibly comes from

Two candidate mechanisms. I verified in code which one applies here.

**(a) Selig re-export off the lofted surface — the likely one for the DG-101G.**
`WriteSeligAirfoil(path, geom_id, u)` samples VSP's *skinned surface*, not the
source `XSecCurve`. The DG-101G's wing xsecs carry `BaseThickChord`,
`FitDegree`, `LE_Cap_*`, `LE_Close_*` and `TE_Close_*` parms — every one of which
edits the surface between the stored `FileAirfoil` points and what the exporter
reads back. A `ThickChord ≠ BaseThickChord` rescale in particular does not
preserve the camber line's contribution the way it preserves t/c. This is
consistent with a partial, geometry-specific loss (Titan Falcon 0.07, DG-101G
larger) rather than a uniform one. **Not confirmed by running OpenVSP** — this is
inference from the parm set present in the file.

**(b) Lost wing incidence — not the DG-101G's problem, but a latent bug with the
identical signature.** `x_secs[0]` is built with `twist=0.0` unconditionally
(`openvsp_wing_handler.py:916`) and `_apply_xform` transforms `xs.xyz_le` only
(`:1033-1036`). Setting wing incidence via the geom XForm `Y_Rotation` is the
standard OpenVSP idiom, and such a model would arrive at 0° incidence with its
LE points correctly rotated — producing a **pure `C_L0` offset with a correct
`C_Lα`**, i.e. exactly the fingerprint of "lost camber". I checked
`dg101g.vsp3` **[computed here]**: it has no `Y_Rotation` and no `Twist` parms
at all, so (b) is not the mechanism here. It will be misdiagnosed as camber loss
the first time someone imports a model that does use it.

### Tooling view — #792 VLM cost **[tooling]**

`asb.VortexLatticeMethod` defaults to `spanwise_resolution=10`,
`chordwise_resolution=10`, `cosspace` — **per wing section**
(`[[vlm-vortex-lattice-method-3d-overview]]`). 31 xsecs → 30 sections → 300
spanwise × 10 chordwise = **3 000 panels on the main wing alone**, plus tails.
The AIC build is O(N²) and the dense solve O(N³): ≈ 4 000 panels is 1.6 × 10⁷
matrix entries and ~6 × 10¹⁰ flops. 215 s is exactly the expected number, not an
anomaly.

Two further facts settle whether it is worth it:

- **VLM is not vectorised over operating points** — an α-sweep must loop —
  whereas **AeroBuildup is**, so a 15-α sweep is a single call
  (`[[vlm-aerobuildup-liftingline-glider-validation]]`). That is the entire
  0.4 s vs 54 min gap.
- **VLM is inviscid: it has no profile drag whatsoever.** For a tool whose
  headline outputs are `(L/D)max`, `CD0`, best-glide and sink rate, a VLM polar
  cannot produce them at all. VLM's unique value is Trefftz-plane induced drag /
  span efficiency and control-surface increments — not the drag polar.

### RC-scale note (Re 50 k – 500 k)

**#791**: A `C_L0` error of ~0.15 shifts the predicted trim α by ~1.5°. Sadraey
sets wing incidence directly from the airfoil's ideal-lift angle
(`i_w = α_{C_li}`, typically 2–5°) **[academic]**, so a 1.5° error is a
significant fraction of the quantity being designed. Lennon **[RC practice]**
notes pitching moment is "little affected by Rn", so the `C_m0` error does not
wash out at model Reynolds numbers either — it propagates straight into required
tail incidence.

**#792**: at Re 50 k–500 k the profile drag VLM omits is the majority of total
`CD` at cruise for a 1–3 m model (Lennon: profile drag "nearly doubles" at low
Rn). So VLM at RC scale is not merely slow — it answers a different question.

### CONSENSUS

**#791 — fix, but ship now with a labelled warning. Retitle the ticket.**

1. **Retitle from "camber loss" to "zero-lift-angle (`α_L0`) fidelity on
   import".** The measured discrepancy is not all importer error, and "camber"
   names only one of two mechanisms.
2. **Ship.** The defect is a pure offset: `C_Lα`, the aerodynamic centre,
   `dC_m/dα`, the neutral point and the static margin are all provably
   unaffected. Every stability claim the tool makes stands. Scope the *accuracy*
   claim: the UI may not present imported `C_L0`, cruise α or required incidence
   as verified.
3. **Add a cheap runtime check and a `DesignWarning` (ADR 0012 / P-WARN-0).**
   Recompute `α_L0` from the written `.dat` with the integral above (~1 ms) and
   compare against the source. Acceptance band:
   - **|Δα_L0| ≤ 0.5°** (≈ |ΔC_L0| ≤ 0.05 at `C_Lα` ≈ 0.1/deg) → silent. This
     sits inside the Re-driven scatter at RC scale.
   - **0.5° < |Δα_L0| ≤ 1.0°** → `severity="info"`.
   - **> 1.0°** → `severity="warning"`, naming the section.
4. **Fix mechanism (b) regardless** — fold the geom XForm `Y_Rotation` into the
   section twist, and read the root section's twist instead of hard-coding 0.0.
   It is a latent, larger, and easier-to-fix version of the same error.
5. **Regression test**: the NACA branches have analytically known `α_L0`; assert
   the written `.dat` reproduces it to 0.2°.

**#792 — accept as a perf item. Do not chase VLM fidelity.**

- Keep **AeroBuildup the default**; it is the only solver in the stack that
  produces a usable RC-scale drag polar, and it validated well (max L/D 39 vs
  Akaflieg's measured 38.3).
- Scale resolution so **panel count**, not section count, is the knob:
  `spanwise_resolution = max(1, round(120 / n_sections))` (≈ 120 spanwise strips
  regardless of augmentation) with `chordwise_resolution = 8`. ≈ 1 000 panels
  → 2–4 s/solve, a ~50–100× improvement.
- Set `run_symmetric_if_possible=True` for a further ~2× on symmetric aircraft.
- Offer VLM only for what it is uniquely good at (span efficiency, control
  derivatives), never as the polar engine.

### Disagreement + hierarchy resolution

`rc-aircraft-designer` **[RC practice]** would tolerate the `C_L0` offset: a
builder absorbs 1.5° of trim error with a couple of clicks of elevator on the
first flight, and level-flight `C_L` of 0.2–0.3 is deep in the linear range.
`aircraft-design-scholz` **[academic]** does not: incidence is *set* from the
airfoil's ideal-lift angle, so the offset corrupts a design decision rather than
a flight adjustment. **Scholz wins — fix it.** The two agree on shipping meanwhile,
because neither the stability chain nor the RC first-flight workflow is broken.

### Confidence

**High** on the physics, on the `C_L0`/`C_m0`-only conclusion, on the numeric
re-attribution of #791, and on the VLM cost model.
**Medium** on the specific root-cause attribution — mechanism (b) is confirmed
present in code and confirmed *not* the DG-101G's cause; mechanism (a) is
inferred from the parm set without running OpenVSP.

---

## Q-CO-7 — `RemoveXsec`: sum or weighted average?

### Question

`copilot_apply_service.py` merges two segments with
`seg_before["sweep"] + seg_after["sweep"]` directly under a comment reading
"sweep = weighted avg". Which is geometrically correct so the remaining planform
is unchanged? Derive it, given that sweep is stored as a **distance** offset per
segment, not an angle.

### What the code does today

`app/services/copilot_apply_service.py:574-582` — comment says weighted average,
code sums:

```python
# length = seg[i-1].length + seg[i].length, sweep = weighted avg.
merged_length = seg_before.get("length", 0) + seg_after.get("length", 0)
merged_sweep  = seg_before.get("sweep", 0)  + seg_after.get("sweep", 0)
```

### Derivation

**Establish the representation.** Sweep is a distance, pinned independently in
two places:

- `app/schemas/wing.py:200-202` — *"Sweep in millimeters, representing the
  backward translation of the segment's tip cross section relative to the
  segment's root cross section."*
- `cad_designer/cq_plugins/wing/wing_segment.py:25-29` — an angle input is
  **converted to a distance first**, then applied as a translation:

```python
if sweep_mode == "angle":
    e = length
    b = e / math.cos(math.radians(sweep))
    sweep = math.sqrt(b*b - e*e)          # angle → distance
tip_origin = root_plane.origin + root_plane.xDir * sweep
```

**Set up the geometry.** Let station *k* have leading-edge position `P_k`.
Segment *i* runs station *i−1* → *i* and carries `(length_i, sweep_i, dihedral_i)`.
The tip plane is built by translating the root origin by `sweep_i` along `xDir`,
stepping `length_i` along the plane normal, then rotating by `tip_dihedral`
(`wing_segment.py:29-32`). The dihedral rotation is **about the local x axis**
(`.plane.rotated((tip_dihedral, 0, -tip_incidence))`), so `xDir` is invariant
under it: **every segment's sweep offset points along the same global chordwise
direction x̂.** Sweep offsets are therefore collinear and simply add.

**The invariant.** In the x (chordwise) component:

```
x_k = x_0 + Σ_{i=1..k} sweep_i                                        (1)
```

Deleting interior station *j* merges segments *j* and *j+1*. Every surviving
station must stay where it was; in particular the outboard neighbour must satisfy,
directly from (1):

```
x_{j+1} − x_{j−1} = sweep_j + sweep_{j+1}                             (2)
```

The merged segment has exactly one sweep parameter and must reproduce (2):

```
sweep_merged = sweep_before + sweep_after            ∎
```

**The code is correct. The comment is wrong.**

**Why the comment is wrong twice.** If `sweep` *were* an angle Λ, the invariant
would sit on the tangent, not the angle:

```
x_{j+1} − x_{j−1} = L_j tan Λ_j + L_{j+1} tan Λ_{j+1}
                  = (L_j + L_{j+1}) tan Λ_merged
⇒ tan Λ_merged = (L_j tan Λ_j + L_{j+1} tan Λ_{j+1}) / (L_j + L_{j+1})
```

— the length-weighted average of **tan Λ**, which equals the weighted average of
Λ only to first order in small angles. So "weighted average" is the right *shape*
of answer for an angle representation and the wrong answer for a distance
representation. The comment is a fossil from an angle-valued design.

**Numeric sanity check [computed here].** Two segments, each 300 mm long, sweeps
40 mm and 80 mm. True root→tip x-offset = 120 mm.

| rule | result | verdict |
|---|---|---|
| sum (code) | 40 + 80 = **120 mm** | ✅ exact |
| length-weighted average (comment) | (40·300 + 80·300)/600 = **60 mm** | ❌ half the sweep |
| simple average | **60 mm** | ❌ |

The error equals the sweep itself — this is not a rounding-level divergence.

### A residual defect the sum does *not* cover: `length`

`merged_length = length_before + length_after` is exact only when the two
segments share the same dihedral. `length` is measured **in the segment's own
(dihedral-rotated) plane**, so two segments with different dihedral form a
dogleg. The merged straight segment's true length is the chord of that dogleg:

```
L_merged = √(L_a² + L_b² + 2 L_a L_b cos Δφ)  <  L_a + L_b   for Δφ ≠ 0
```

| Δφ (dihedral break) | L_a = L_b = 300 mm | true L_merged | summed | span error |
|---|---|---|---|---|
| 5° (typical polyhedral) | | 599.4 mm | 600 mm | 0.1 % — negligible |
| 30° (winglet junction) | | 579.6 mm | 600 mm | **3.4 %** |

And the tip's z-position is wrong regardless, because one merged segment can
carry only one dihedral.

### Tooling / RC-scale note

None material — this is pure geometry, identical at every scale and Reynolds
number. The only RC-specific angle: polyhedral breaks of 3–8° are extremely
common on RC gliders **[RC practice]**, and at those angles the length-sum
approximation is genuinely negligible (≤ 0.3 %).

### CONSENSUS

1. **Keep the sum. Fix the comment** to *"sweep offsets are chordwise distances
   and therefore add; the merged segment must span station j−1 → j+1."*
2. **Add the regression test** with the 40 + 80 = 120 mm case above, so the sum
   can never be "corrected" back to an average by someone reading the old
   comment.
3. **Warn on dihedral loss.** When the two merged segments' dihedrals differ by
   **> 2°**, emit a `DesignWarning` (`geometry_simplified`): removing that station
   destroys a dihedral break, and no single-segment merge can preserve it.
   Escalate to `severity="warning"` when the resulting span error exceeds
   **0.5 %** (Δφ ≳ 11.5° for equal-length segments).
4. **Document the length approximation** in the same comment.

### Disagreement + hierarchy resolution

None. The derivation is exact and the representation is pinned by two
independent places in the codebase; no expert source is needed to override
another.

### Confidence

**High.**

---

## Q-CO-13 — Should the copilot's polar sweep follow cruise speed?

### Question

The sweep is hard-coded α ∈ [−10°, +15°], 26 points, V = 20 m/s, h = 0. A 30 m/s
cruise aircraft is still polared at 20 m/s. Should it read the mission's cruise
condition, and what sweep is physically meaningful for an arbitrary RC/UAV model?

### What the code does today

`app/services/copilot_tools.py:336-342`:

```python
sweep_request = AlphaSweepRequest(
    altitude=0.0, velocity=20.0, alpha_start=-10.0, alpha_end=15.0, alpha_num=26,
)
```

Its sibling `_run_stability_async` in the **same file** already does the right
thing (`:424-428`): it reads `ctx["v_cruise_mps"]` from
`assumption_computation_context` with a 20.0 fallback, with a gh-924 comment
explaining why the design point must be consistent. The precedent exists; the
polar tool just never adopted it.

### Physics / analytical view

In strictly inviscid, incompressible flow `C_L(α)` and induced `C_Di` are
**independent of V** — the polar is a pure function of geometry. Velocity enters
only through:

1. **Reynolds number** → viscous drag and stall. Anderson **[academic]**:
   `C_f,lam = 1.328/√Re_c`, `C_f,turb = 0.074/Re_c^{1/5}`, and the transition
   point `x_cr = μ Re_{x,cr} / (ρ V)` moves forward with V
   (`[[airfoil-drag-skin-friction]]`).
2. **Mach number** → irrelevant below M ≈ 0.3, i.e. always at this scale.

So the polar *is* speed-dependent, entirely through Re. Doubling V from 15 to
30 m/s reduces laminar `C_f` by 29 % and turbulent `C_f` by 13 % **before** any
transition or separation-bubble effects.

Scholz **[academic]** backs the same conclusion structurally: the aircraft polar
is computed *"for all critical flight phases"* — cruise, take-off, landing —
never once at an arbitrary speed (`[[aircraft-polar-performance]]`, Step 13 of
the conceptual design process).

### RC-scale note — this is where it stops being academic

RC-Network's working formula **[RC practice]** (`[[rcn-re-zahl]]`):

```
Re = v [m/s] · t [mm] · 70
```

For a 200 mm chord:

| V | Re |
|---|---|
| 12 m/s (park flyer) | 168 000 |
| 20 m/s (hard-coded) | 280 000 |
| 30 m/s (fast sport) | 420 000 |

All three sit at or below the critical Reynolds number where model wings live.
RC-Network is explicit: *"Model aircraft often operate near or around the
critical Reynolds number. Consequently, flow conditions on wings and tail
surfaces can change dramatically with relatively small changes in airspeed and
angle of attack. Moreover, in the Reynolds number range typical of model flight,
even in supercritical flow regions, lift and drag coefficients change
significantly with Reynolds number."*

Lennon quantifies it **[RC practice]** (`[[lennon-reynolds-number]]`): across the
model Re band a NACA 0012's `C_Lmax` falls from 1.55 to 0.83 (**−54 %**), stall α
from 17° to 10°, and **profile drag nearly doubles**.

**So evaluating a 12 m/s park flyer's polar at 20 m/s is not a small offset: it
can flatter `CD0` by up to ~2× and overstate `C_Lmax` by up to 50 %. That is a
larger error than the camber issue in Q-VI-8.**

### Tooling view **[tooling]**

`AeroBuildup` obtains sectional aerodynamics from **NeuralFoil**, whose training
distribution covers Re ∈ [1.87 k, 262 M] at 95 %
(`[[phd-neuralfoil-training-data-generation]]`) — 50 k–500 k is squarely inside
it, so the solver *will* respond correctly to whatever velocity it is given.
AeroBuildup is vectorised over operating points, so the corrected sweep is still
a single call: **the fix costs nothing in runtime.**

### CONSENSUS

1. **Read the cruise speed from the assumption context.** Use
   `ctx["v_cruise_mps"]` with the same 20.0 fallback that
   `_run_stability_async` already uses (`copilot_tools.py:424-428`) — one
   design point, one polar, consistent with gh-924 / ADR 0004.
2. **Report the condition inside the result.** Add `velocity_mps`,
   `altitude_m` and the derived `reynolds_number` (= `v · MAC_mm · 70`) to the
   summary dict, so the model cites the flight condition it reasoned about
   instead of assuming one.
3. **Replace the fixed α range with a stall-anchored one: α ∈ [−6°, +16°],
   1° steps, 23 points.**
   - **−6°** covers the inverted/dive branch and the zero-lift point of any
     realistic RC section (`α_L0` reaches −6.05° on the FX 61-184 computed in
     Q-VI-8). The current −10° wastes 4 points below any usable condition.
   - **+16°** is past `C_Lmax` for every section at RC Re (Lennon: stall α as
     low as 10°), so the sweep always brackets the peak. The current +15° can
     *just* miss it on a high-Re, high-camber section.
   - **1° steps.** For a quadratic peak sampled at Δα, the peak-location error
     is ≤ Δα/2 and the `C_Lmax` error ≈ ½|d²C_L/dα²|(Δα/2)². At 1° this holds
     `C_Lmax` to better than 2 %; the existing 26 points over 25° is 0.96° —
     essentially the same resolution, so this is a re-aiming, not a refinement.
4. **Do not sweep velocity.** One polar = one Reynolds number. If a second
   condition is wanted (approach, dash), run a *second* sweep and label it —
   never mix speeds into one curve.
5. **Take altitude from `profile.environment.altitude_m`**, not hard-coded 0.0.

### Disagreement + hierarchy resolution

`rc-aircraft-designer` **[RC practice]** would accept the fixed sweep for a
first-cut trainer: level-flight `C_L` is 0.2–0.3
(`[[lennon-level-flight-speed]]`), comfortably in the linear range whatever the
Re, so the *usable* part of the polar barely moves. `aircraft-design-scholz`
**[academic]** requires the phase-matched polar. **Scholz wins** — and here the
RC source's own Re data independently supports the academic ruling once the
numbers are looked at, so this is agreement rather than a genuine conflict.

### Confidence

**High.**

---

## Q-MS-5 — Should `_grid_search_trim` search a deflection grid?

### Question

`best_controls` is reset to `{}` on every improvement and returned empty, so when
the Opti stage fails the fallback trims by α/β/V alone and the elevator stays at
0°. A target needing a different deflection is unreachable and reported
`NOT_TRIMMED` rather than "not reachable with the available authority". Should
the fallback search a coarse deflection grid, at what resolution and bounds — or
should the point get its own status?

### What the code does today

`app/services/operating_point_generator_service.py`:

- Stage 1 `_solve_trim_candidate_with_opti` (`:585-700`) *does* carry control
  variables — pitch ±25°, roll ±20°, yaw ±25° — with `max_runtime=0.35 s`,
  `behavior_on_failure="return_last"`, and its failure logged at **DEBUG**
  (`:832`).
- Stage 2 `_grid_search_trim` (`:800-842`) loops 4 velocities × β candidates ×
  13 α values and sets `best_controls = {}` on **every** improvement (`:840`).
- Score: `|C_m| + 0.5|C_Y| + 0.3|C_L − C_L,target|` (`:192-196`).
- Status: `TRIMMED if best_score < 0.35 else NOT_TRIMMED` (`:853-857`).
- `C_L,target = n·m·g/(q·S)` (`:784-798`) — correct.

### Physics / analytical view

Longitudinal trim is Sadraey's 2 × 2 **linear** system **[academic]**
(`[[sadraey-elevator-longitudinal-trim-requirement]]`, Eq. 12.86):

```
| C_Lα   C_LδE | | α  |   | C_L1 − C_L0                |
| C_mα   C_mδE | | δE | = | −T·z_T/(q S c̄) − C_m0      |
```

with the closed-form Cramer solution at Eq. 12.90. **In the linear range this
has an exact solution in two unknowns. It is not a search problem.**

Grid-searching α while holding δE = 0 solves a **different, over-constrained**
problem: it asks for the single α that makes `C_m ≈ 0` *and* `C_L ≈ C_L,target`
with only one free variable. For any aircraft whose `C_m0 ≠ 0` — i.e. any
cambered wing; the FX 61-184 computed in Q-VI-8 has `c_m,c/4 = −0.165` — those
two conditions are met at *different* α. The score floor is then bounded away
from zero and the point is labelled `NOT_TRIMMED` **no matter how fine the α
grid gets**.

**That is the actual defect: a rank-deficient solve, not a resolution problem.**
Adding grid points to α cannot fix it; restoring the second degree of freedom
can.

### Tooling view **[tooling]**

AVL confirms this directly. You do not search for elevator deflection in AVL —
you *constrain* it: `D1 PM 0` makes AVL solve for the δE that yields `C_m = 0`
inside the same linear system (`Avl/avl_doc.txt:1534-1538`). AVL ships no trim
grid because none is needed. Convergence failure in AVL means the
variable/constraint system is **ill-posed** (`:1553-1555`) — which is precisely
what the current fallback is.

AeroSandbox note: `AeroBuildup` does **not** propagate main-wing downwash onto
the tail (`[[phd-aerobuildup-workbook-buildup]]`), so tail effectiveness is
somewhat over-estimated and the solved δE will be slightly small in magnitude.
This is a known bias to record, not a reason to change algorithm.

### CONSENSUS

**Do not add a deflection grid. Give the fallback its second degree of freedom
back, and give the point its own status. Both.**

**(a) Two-point secant on δE — preferred.** For each α already on the grid,
evaluate at δE = 0 and at a probe deflection δ_probe = 5°, then:

```
δE* = − C_m(0) · δ_probe / ( C_m(δ_probe) − C_m(0) )
```

clipped to the authority limit. Because `C_m` is **linear in δE** below
hinge-line separation, this is **exact in one step**, not an approximation.
Cost: exactly **2×** the current evaluation count, versus ~7–11× for any grid
worth having. Add one refinement pass if `|C_m(δE*)|` still exceeds tolerance —
it will only for a stalled tail.

**(b) If a grid is mandated anyway: δE ∈ [−25°, +25°] in 2.5° steps (21
values).**
- **Bounds** from Sadraey **[academic]**: *"Maximum deflection: ≤ 25° to avoid
  flow separation on the horizontal tail"*
  (`[[sadraey-elevator-design-principles]]`); and *"if the required δ_E exceeds
  about 30°, the elevator must be enlarged or the tail arm extended"*. Do **not**
  extend the grid past ±25° — beyond that the *aircraft* is deficient, not the
  solver.
- **Step 2.5°** because it is the coarsest step whose trim residual sits below
  the pitch resolution an RC model is actually trimmed to (transmitter trim steps
  correspond to ~0.5–1° of surface; a typical 4:1 horn/servo ratio quantises near
  0.5°). Finer is below the model's own build tolerance.

**(c) Give the point its own status — three outcomes, not two.** This is
Sadraey's design constraint expressed in the data model:

| status | condition |
|---|---|
| `TRIMMED` | `\|C_m\| ≤ 0.01` **and** `\|C_L − C_L,target\| ≤ 0.02`, with `\|δE\| ≤ 25°` |
| `CONTROL_AUTHORITY_LIMIT` *(new)* | a solution exists but needs `\|δE\| > 25°` (or hits the α limit). **Carry the required δE in the payload** so the user sees how far short they are |
| `NOT_TRIMMED` | no solution found for numerical reasons |

`CONTROL_AUTHORITY_LIMIT` is a **design finding** — enlarge the elevator or
lengthen the tail arm — and under ADR 0012 it belongs in the response body, not
in a log line.

**(d) Fix the tolerance.** `|C_m| ≤ 0.01`: with a typical RC tail volume
`V_H ≈ 0.5` and `C_mδE ≈ −0.01/deg`, ΔC_m = 0.01 is **1° of elevator** — the
resolution at which a pilot trims. The current `best_score < 0.35` on a
mixed-unit sum is ~35° equivalent, i.e. effectively no criterion at all.

**(e) Raise the Opti-failure log from DEBUG to WARNING and count it.** A
systematically failing stage 1 means every point silently pays the ~4× grid
cost. `max_runtime=0.35 s` is a very tight budget for an IPOPT solve that
rebuilds AeroBuildup each iteration — measure the failure rate before tuning it.

### RC-scale note

The hinge-line separation that sets Sadraey's 25° limit is Re-dependent and
**tightens** at model scale: an RC tail at Re 50 k–150 k separates earlier than
a full-scale one. ±20° is the honest RC authority bound; ±25° is the generous
one. Keep ±25° as the solver bound and flag anything above 20°.

### Disagreement + hierarchy resolution

`rc-aircraft-designer` **[RC practice]** frames elevator authority as a *surface
ratio* decision (trainer 25–30 %, sport 35–40 %, aerobatic 40–70 % of tail area
— `[[tail-elevator--practical-limits-and-mission-consistent-ranges]]`) rather
than a deflection number, and offers no throw limits. It therefore neither
supports nor contradicts the ±25° bound. `avl-advisor` **[tooling]** and
`aircraft-design-scholz` **[academic]** agree that trim is a constrained solve,
not a search. No conflict to resolve.

### Confidence

**High** on the rank-deficiency diagnosis and on the secant step being exact.
**Medium** on the specific 2.5° / 0.01 / 5° numbers — defensible engineering
choices calibrated as shown, not derived constants.

---

## Q-MS-12 — Operating-point sweep semantics (physics items)

### Question

A six-item bundle. Per instruction I rule on the **physics-relevant** items —
what defines an operating point, what a sweep must hold constant, the
`target_turn_n` item, `has_pitch_control`, `STALL_IN_TURN`, and the trim-weight
provenance. The `replace_existing` scoping and the SSE `targets`/`skip` filtering
are contract decisions and are flagged, not ruled on.

### What the code does today

`operating_point_generator_service.py:485-512` builds 15 targets; turn banks are
hard-coded `for bank in (20, 40, 60)` with `n_target = 1/cos(bank)`;
`profile.goals.target_turn_n` (default 2.0, `:209`) is validated and never read;
`_cl_target_for_velocity` (`:784-798`) computes `C_L,target = n·m·g/(q·S)`;
`STALL_IN_TURN` is emitted as a formatted sentence (`:173`); the six objective
weights (50, 3, 15, 2, 2, 0.001) appear at `:674-680` with no comment.

### Physics / analytical view

**What defines an operating point.** An operating point is the complete set of
arguments that make the aerodynamic problem well-posed. In AeroSandbox terms
**[tooling]** that is exactly
`OperatingPoint(velocity, alpha, beta, p, q, r, atmosphere)` **plus** the
configuration state (control deflections, flap setting) **plus** the mass and CG
the moments are referenced against (`xyz_ref`). The code's target dictionaries
carry the right input list: `velocity`, `altitude`, `beta_target_deg`,
`bank_deg`, `n_target`, `flap_deflection_deg`, `config`.

What is missing from the **stored** point is the outcome-defining pair: the
**trimmed `C_L`** and the **control deflections** that achieved it. Without
`C_L` the point cannot be replayed and cannot be placed on a V-n diagram — which
is exactly Q-MS-6's bug, and it is the same root cause. **Store the trimmed
`C_L` and the solved deflections; they are part of the operating point, not
derived output.**

**What a sweep must hold constant.** A sweep is a one-parameter family;
everything not swept must be pinned *and recorded*. This sweep varies **velocity
and configuration together** across its 15 targets. That is correct for a
*mission* sweep — it is a set of design points, not a curve — but it means the
results are **not a polar and must never be plotted as one.** Held constant and
correctly so: mass (`effective_mass_kg`), CG (`xyz_ref`), altitude
(`profile.environment.altitude_m`), atmosphere. ✅

**`target_turn_n` vs the hard-coded banks — these are the same quantity.**
For a steady level turn `n = 1/cos φ ⇔ φ = arccos(1/n)`. The code already
encodes the forward direction (`n_target = round(1/cos(radians(bank)), 4)`) and
applies it correctly in `C_L,target = n·m·g/(q·S)`. But the banks are frozen at
20/40/60°, so the hardest turn evaluated is **n = 2.0** — while a user who set
`target_turn_n = 3.0` is asking for a **70.5° bank** and gets a sweep whose
worst case is **33 % below their stated requirement**, with no warning.
**Derive the bank set from the goal**: keep a low anchor (20°), add `φ(n_target)`,
and add the midpoint, so the user's design load factor is always in the set.

**`has_pitch_control` detected but never required — physically indefensible.**
An aircraft with no pitch surface has **one** free variable (α) against **two**
conditions (`L = W`, `C_m = 0`). It is trimmable at exactly the single `C_L`
where `C_m(α)` crosses zero, if such a point exists at all. Generating fifteen
"trimmed" points for such an aircraft produces fifteen results that are all
really `CONTROL_AUTHORITY_LIMIT` (see Q-MS-5). **Require `has_pitch_control` for
every target that is not itself a stall probe.** A flying wing with elevons has
pitch control through the `[pitch]` role and passes, so this does not exclude
the configurations RC users actually build.

**`STALL_IN_TURN` feasibility check.** The physics is right: it evaluates the
required `C_L` at the **turn's own velocity** via
`_apply_turn_feasibility(point, bank_deg, point.velocity, vs_clean)`
(`:1153-1154`). ✅ The defect is purely representational — it is a formatted
sentence with embedded numbers while every sibling warning is a bare token, so
equality-matching consumers miss it. **Emit the bare token `STALL_IN_TURN` and
put `{bank_deg, n, cl_required, cl_max}` in a structured field.**

**The six trim weights (50, 3, 15, 2, 2, 0.001).** They are not arbitrary, but
they are unreproducible from the spec. The objective mixes `C_m` (moment),
`C_Y` (force) and a `C_L` error, which have different natural magnitudes. The
standard, defensible construction is **inverse-square-of-tolerance weighting**,
`w_i = 1/tol_i²`:

| quantity | tolerance | `1/tol²` | normalised | **shipped** |
|---|---|---|---|---|
| `C_m` | 0.01 | 10 000 | 50 | **50** |
| `C_L − C_L,target` | 0.02 | 2 500 | 12.5 | **15** |
| `C_Y` | 0.03 | 1 111 | 5.6 | **3** |

The shipped weights land within a factor of ~2 of a tolerance-based derivation
on all three. **Re-express them as tolerances** — that makes them reproducible
from the spec instead of magic, and it makes the trim criterion of Q-MS-5 fall
out of the same three numbers. The `0.001·δ²` term is a **regulariser**, not
physics: its only job is to select the minimum-deflection solution when several
surfaces make the trim under-determined. Relative to a 50-weighted `C_m²` it
biases trim by well under 0.1°, which is correct behaviour for a regulariser.

**Reference-speed provenance (`polar` / `cold_start`) — persist it.** The
difference is a stall speed derived from a *computed* `C_Lmax` versus an
*assumed* one, and at RC Reynolds numbers that assumption is the single largest
error source in the whole sweep: `C_Lmax` varies by −54 % across the model Re
band (Lennon **[RC practice]**). Ten of the fifteen target velocities are
multiples of `vs_clean`/`vs_to`/`vs_ldg`, so the provenance propagates into
almost every point. Storing only the consequence (`STALE_NO_POLAR`) discards the
information needed to interpret every velocity in the set.

### Items flagged, not ruled on (contract, not physics)

- `replace_existing` being aircraft-wide rather than set-scoped — it deletes
  manually created points. Scope it or rename it; either is defensible.
- The SSE stream filtering `supported` before emitting `targets`, so a
  capability-gated target appears in neither `targets` nor `skip`, and `skip`
  carries no reason. This is a real information loss and should carry the
  capability string that `_validate_target_capability` already returns
  (`:568-583`) — but it is an API-shape decision.

### RC-scale note

Two of these change character at RC scale. (i) The `target_turn_n` gap matters
more, because RC/UAV missions are frequently *defined* by a manoeuvre load
factor rather than by a cruise point. (ii) The provenance item matters more,
because `C_Lmax` is the most Re-sensitive quantity in the model and every
velocity in the sweep hangs off it.

### CONSENSUS

1. **Store the trimmed `C_L` and the solved control deflections on the
   operating point.** They are constitutive, not derived — and this simultaneously
   fixes Q-MS-6's V-n marker placement.
2. **Derive the turn banks from `profile.goals.target_turn_n`** via
   `φ = arccos(1/n)`; keep 20° as a low anchor plus the midpoint. Never ship a
   sweep whose hardest turn is below the user's stated `n`.
3. **Require `has_pitch_control`** for every non-stall-probe target; otherwise
   emit `CONTROL_AUTHORITY_LIMIT` rather than a fictitious trim.
4. **Make `STALL_IN_TURN` a bare token**; move the numbers to a structured
   field.
5. **Re-express the six weights as three tolerances** (`tol_Cm = 0.01`,
   `tol_CL = 0.02`, `tol_CY = 0.03`, `w = 1/tol²`) plus a documented `1e-3`
   control-effort regulariser. Same behaviour, reproducible from the spec.
6. **Persist the reference-speed provenance**, not only its consequence.
7. **Label the result set as a mission point-set, never a polar** — the
   velocities differ point to point.

### Disagreement + hierarchy resolution

None between sources. `aircraft-design-scholz` **[academic]** supplies the
operating-point definition and the load-factor relation; `aerosandbox-expert`
**[tooling]** supplies the exact argument list that makes the problem well-posed;
`rc-aircraft-designer` **[RC practice]** supplies the Re sensitivity that raises
the priority of the provenance item. All consistent.

### Confidence

**High** on the operating-point definition, the `n ↔ φ` identity, and
`has_pitch_control`.
**Medium** on the weight re-derivation — a defensible reconstruction that matches
the shipped numbers, not a recovery of the original author's stated intent.

---

## Q-AV-6 — Is a user's `.avl` edit expected to be ignored for single-wing runs?

### Question

`analyze_airplane`, `trim_with_avl` and the full-airplane strip-force path honour
a user-edited stored `.avl`; `analyze_wing` and the single-wing strip-force path
never consult it — they prune the airplane to one wing and always build fresh.
Deliberate given the pruning, or an inconsistency? What does AVL practice say
about round-tripping user edits?

### What the code does today

`app/services/analysis_service.py`:

- `analyze_airplane` (`:346-352`) calls `get_user_avl_content(db, aeroplane_uuid)`
  and only regenerates when it is `None`.
- `analyze_wing` (`:305-321`) **never** calls it — it always runs
  `build_avl_geometry_file(plane_schema, spacing_config)` + `inject_cdcl`, then
  prunes `asb_airplane.wings` to the named wing and clears `fuselages`.

No warning is emitted either way; the user cannot tell which file was used.

### Tooling view — what is global vs per-surface in an `.avl` **[tooling]**

From the AVL 3.40 primer (`Avl/avl_doc.txt`):

**Global header, before any `SURFACE` block** (`:243-289`):
`Mach`; `iYsym iZsym Zsym`; **`Sref Cref Bref`**; **`Xref Yref Zref`**; `CDp`.
The primer is explicit: *"Sref and Bref are assumed to correspond to the total
geometry"* (`:289`), and *"if doing trim calculations, XYZref must be the CG
location"* (`:272-274`).

**Per-`SURFACE` / per-`SECTION`** (`:305-940`):
`Nchord Cspace Nspan Sspace`, `COMPONENT`, `YDUPLICATE`, `SCALE`, `TRANSLATE`,
`ANGLE/AINC`, `NOWAKE`, `NOALBE`, `NOLOAD`, **`CDCL`**, `CLAF`, `CONTROL`,
`NACA`/`AIRFOIL`/`AFILE`, `DESIGN`.

**Therefore: you cannot reuse a hand-edited full-airplane file for a single-wing
run by deleting surfaces.** The coefficients would still be normalised against
the whole-aircraft `Sref/Cref/Bref` and moments still taken about the aircraft
CG. The output would be a set of numbers that look like wing coefficients and are
not — the same `P-WARN-0` failure shape the VSPAERO benchmark already caught once
("ASB `s_ref` taken from first wing not main wing → 8× wrong coefficients").

**But that argument only justifies rewriting the header.** It does not justify
discarding the user's *per-surface* edits — which are precisely the edits AVL's
own primer instructs you to make:

- *"Spacing should be bunched at dihedral and chord breaks, control surface ends,
  and especially at wing tips"* (`:1100-1108`).
- Rule 4: refinement must happen in **both** spanwise and chordwise directions
  (`:1121-1130`).
- Rule 3: a surface carrying a control surface needs adequate `Nchord` to resolve
  the camberline kink at the hinge line (`:1110-1119`).

A user who hand-tuned `Nspan`/`Sspace` on their wing did exactly what AVL asks
for. The single-wing route throws it away and says nothing.

### RC-scale note

Unchanged in kind, but it raises the stakes on one specific block. AVL is
inviscid and Reynolds-blind **except** through hand-entered **`CDCL`**, which is
the only mechanism for getting Re-appropriate profile drag into AVL at all
(`:547-580`, `:909-940`). At Re 50 k–500 k that is not a refinement — it is the
difference between a drag number and no drag number. `CDCL` is therefore the
per-surface edit an RC user is most likely to have made, and the one whose loss
hurts most. **Preserving `CDCL` outranks preserving the spacing parms.**

### CONSENSUS

**It is an inconsistency, not a defensible design — but the fix is a merge, not
a swap.**

For `analyze_wing` and the single-wing strip-force path:

1. **If a stored user `.avl` exists, parse it and lift out the `SURFACE` block
   matching `wing_name` verbatim** — spacing, `CDCL`, `CLAF`, `CONTROL`, section
   airfoil references, `ANGLE`, `YDUPLICATE`.
2. **Always regenerate the header** from the pruned wing: `Sref/Cref/Bref` from
   that wing alone, `Xref/Yref/Zref` from the request's `xyz_ref`.
   **Never inherit the aircraft header.**
3. **If the named wing has no matching `SURFACE` block** (renamed, or deleted by
   the user), fall back to the generated file **and emit a `DesignWarning`**
   (`input_ignored`) naming what was dropped.
4. **Report the provenance either way.** Add `avl_source:
   "user_surface+generated_header" | "generated"` to the response. Today the user
   cannot tell — and that silence, not the pruning, is the actual complaint.

**Acceptable minimum** if (1)–(2) is judged too much work for the value:
**(3) and (4) alone** — always regenerate, but always state that a stored user
`.avl` exists and was not used on this route. **Silence is the one option that is
not acceptable under ADR 0012.**

### Disagreement + hierarchy resolution

None. `avl-advisor` **[tooling]** is the sole authority on the file format and
its verdict is unambiguous in both directions: the header genuinely cannot be
reused, and the per-surface blocks genuinely can. No academic source contradicts
it. Note this project's standing preference for AeroSandbox over AVL
(AVL only where ASB cannot cover the case) caps the priority of this item — it
affects a secondary analysis route.

### Confidence

**High.**

---

## Q-FD-3 — Should the `a`/`b` ↔ ASB `width`/`height` mapping be asserted at runtime?

### Question

`a` is the Y half-axis mapping to `FuselageXSec.width`; `b` is the Z half-axis
mapping to `height`. Swapping rotates the body 90°; treating them as diameters
doubles it. Neither errors. Should there be a runtime assertion? And do existing
`fuselage_xsecs` rows hold full widths instead of half-axes?

### What the code does today

The ×2 conversion appears in **two independent places**:

- `cad_designer/aerosandbox/slicing.py:1291-1300` —
  `asb.FuselageXSec(width=2.0*d["a"], height=2.0*d["b"], shape=d["n"])`
- `app/converters/openvsp_fuselage_handler.py:215` —
  `_rounded_rect_to_n(width=2.0*a, height=2.0*b, radius=r)`

The convention lives only in field descriptions. Nothing validates it.

### Analysis — the three failure modes have very different signatures

| failure | geometric effect | caught by `volume_ratio`/`area_ratio` (Q-FD-4)? |
|---|---|---|
| **Swap `a ↔ b`** | rotates the body 90° about x | **No.** Volume and wetted area are near-unchanged — *exactly* unchanged for a body of revolution |
| **Factor-2** (half-axis read as full width) | both dimensions ×2 | **Yes** — `volume_ratio ≈ 4.0`, `area_ratio ≈ 4.0` |
| **Half-factor** (full width read as half-axis) | both ÷2 | **Yes** — `volume_ratio ≈ 0.25` |

**The mode that matters most is the one the integral metrics are blind to.** A
swap leaves volume right and everything else wrong: wrong frontal-area
distribution, wrong crossflow behaviour, wrong side force and `C_nβ`, wrong
internal layout. Slender-body and crossflow terms in AeroBuildup's fuselage model
**[tooling]** (`[[phd-aerobuildup-workbook-buildup]]`: Jorgensen slender-body
inviscid + crossflow-analogy viscous, with separation keyed to local curvature)
read width and height separately, so a swap produces confidently wrong numbers.

A bare runtime assertion is the wrong instrument, because an assertion can only
compare `a`/`b` against *something*, and the only meaningful "something" is the
source geometry.

### CONSENSUS

**Not a bare runtime assertion. Three measures, in priority order.**

**1. One conversion seam (the real fix).** `2.0 * a` currently appears in at
least two modules. Replace both with a single
`superellipse_to_asb_xsec(a, b, n) -> FuselageXSec`. The convention is then
asserted *by construction* and can only be wrong in one place. An assertion
downstream of two independent conversions only tells you that one of them ran.

**2. A source-anchored invariant where a `step_path` survives** — this also
answers the historical-data half of the question. The STEP bounding box gives
true Y and Z extents. At **import time only**, per xsec:

- `2a ≤ 1.02 · Y_extent(step)` and `2b ≤ 1.02 · Z_extent(step)`
  → catches the factor-2 error (which would give ≈ 2× the box).
- `max_x(2a) / max_x(2b)` within **20 %** of `Y_extent / Z_extent` for the whole
  body → catches the swap on any non-circular fuselage. On a body of revolution
  the swap is both unobservable and harmless, so this generates no false
  positive.

Rows with no surviving `step_path` cannot be checked; report them as
`unverified` rather than pretending. That is the same conclusion the wing-side
audit reached for pre-gh-951 terminal dihedral: genuinely unrecoverable data
should be labelled, not guessed.

**3. A plausibility band when there is no source.** The only checkable property
is that the aspect ratio is sane. For RC/UAV fuselages **[RC practice]**,
`2a/2b ∈ [0.3, 3.0]` spans everything from a deep glider pod to a flat wing-body.
Outside that band → `severity="warning"`, **never an exception**: a 0.5 kg foamie
with a genuinely 4:1 flat fuselage exists, and refusing to store it would be
worse than the bug.

**Do not raise.** Under ADR 0012 / P-WARN-0 the correct severity is a
`DesignWarning` on the import response. A hard assertion in the service path
turns a suspicious-but-possibly-fine geometry into a 500 with no user override.

**On the historical audit:** the check in (2) *is* the audit query. Run it once
over `fuselage_xsecs` rows that still have a `step_path`; a row whose `2a`
exceeds the STEP Y-extent by ≈ 2× is a pre-fix full-width row.

### RC-scale note

No Reynolds dependence — this is a units/convention question. The only
scale-specific input is the plausibility band in (3), which is set from RC
fuselage practice rather than from transport cross-sections.

### Disagreement + hierarchy resolution

None. `aerosandbox-expert` **[tooling]** confirms `FuselageXSec` takes full
`width`/`height` (and supports non-circular superellipses with arbitrary positive
shape parameter); `aircraft-design-scholz` **[academic]** contributes only
indirectly, via the fineness-ratio machinery in Q-FD-4 that consumes these
dimensions.

### Confidence

**High** on the failure-mode analysis and on the assertion being the wrong
instrument. **Medium** on the specific 1.02 / 20 % / [0.3, 3.0] numbers.

---

## Q-FD-4 — What `volume_ratio` / `area_ratio` counts as an unacceptable fit?

### Question

Both ratios are reported with every slice result but nothing thresholds, flags or
rejects a poor reconstruction. Is there a threshold below which the fit should be
rejected or warned about? Should a bound-hitting superellipse exponent `n`
produce a warning?

### What the code does today

`cad_designer/aerosandbox/slicing.py:1301-1320` reconstructs an `asb.Fuselage`
from the fitted xsecs and computes
`volume_ratio = asb_fuselage.volume() / original_volume`,
`area_ratio = area_wetted() / original_surface_area`. `n` is silently clipped at
`:1285`: `np.clip(fit["n"], 0.5, 8.0)`. Nothing thresholds either number; the
ratios are logged and returned.

### What the ratios can and cannot detect

**Can detect:**
- systematic over/under-sizing — including the factor-2 bug of Q-FD-3
  (`volume_ratio ≈ 4.0`);
- too few stations across a rapidly-changing region (nose or canopy cut off →
  ratio < 1);
- a degenerate or zero dimension (ratio ≈ 0) — this is also the F3/Stratos
  failure the benchmark already found, where a degenerate fuselage dimension
  produced 15/15 NaN inside AeroBuildup's `log10`.

**Cannot detect:**
- the `a ↔ b` **swap** — volume-neutral (Q-FD-3);
- **local** errors that cancel — a nose fitted too fat and a tail too thin
  integrate to ≈ 1.00;
- **surface smoothness**, which is what actually drives drag;
- the **position** of the volume, which is what drives CG and `C_m`.

**A ratio near 1.0 is a necessary, not a sufficient condition. Say so in the
response** rather than letting a caller read it as a fit-quality score.

### Physics / analytical view — anchoring the thresholds

Anchor on what the numbers are *used for*, which at this scale is fuselage
parasite drag and internal volume, not structural loads.

Fuselage zero-lift drag scales directly with wetted area (Sadraey Eq. 7.5,
**[academic]**, via `[[fineness-ratio]]`):

```
C_D0,f = C_f · f_LD · S_wet,f / S_ref ,   f_LD = 1 + 60/(L/D)³ + 0.0025 (L/D)
```

- A **5 % `area_ratio` error is a 5 % error in fuselage `C_D0`**. For a typical
  RC model the fuselage carries 15–30 % of parasite drag, so 5 % of area → ~1 %
  of aircraft `C_D0` — well under the Reynolds-driven scatter (profile drag
  "nearly doubles" across the model Re band, Lennon **[RC practice]**). 5 % is
  comfortably inside the noise.
- Volume errors bite through `f_LD`: a 10 % volume error at fixed length is a
  ~5 % diameter error, which for a typical RC `L/D` ≈ 6–8 moves `f_LD` by ~4 %.

### CONSENSUS — thresholds

| band | `volume_ratio` **and** `area_ratio` | action |
|---|---|---|
| **good** | both in **[0.95, 1.05]** | store, no warning |
| **degraded** | either in [0.85, 0.95) ∪ (1.05, 1.15] | store + `DesignWarning`, `severity="info"` — "simplified body; drag estimates carry ~10 % extra uncertainty" |
| **poor** | either in [0.70, 0.85) ∪ (1.15, 1.40] | store + `DesignWarning`, `severity="warning"`; name the likely cause (too few stations / sharp feature) and suggest more slices |
| **reject** | either outside **[0.70, 1.40]**, **or** `volume_ratio ≤ 0.05`, **or** non-finite | **do not store**; return a quality error |

Two deliberate design choices in that table:

- **The 1.40 upper cut sits below 4.0**, so the factor-2 bug of Q-FD-3 is caught
  by this gate as well as by the source-anchored check.
- **The ≤ 0.05 and non-finite cuts** catch the degenerate-dimension case that
  already produced 15/15 NaN on the Stratos. That must fail **loudly at slice
  time**, not silently downstream inside AeroBuildup's `log10`.

**The ratios are asymmetric in meaning: > 1 is worse than < 1 by the same
margin.** A reconstruction *bigger* than the source means the superellipse is
bulging outside the real skin — geometrically impossible for a fit, and a strong
signal of a units or half-axis error. A reconstruction *smaller* than the source
is the expected direction for a simplification (corners get rounded off). If you
want the gate to reflect that, tighten the upper edge to 1.02 and leave the
lower at 0.90. I would ship the symmetric bands first and tighten once there is
data from a real corpus.

### CONSENSUS — bound-hitting `n`

**Yes, warn. This is not optional under ADR 0012.** `np.clip(fit["n"], 0.5, 8.0)`
silently returns a fit sitting *at* the bound — the textbook silent-degradation
shape, and the exact opposite of what ADR 0012 requires.

- `n → 8.0` means the true section is nearly rectangular — **very common on
  3D-printed and foam-board RC fuselages**.
- `n → 0.5` means a strongly concave/star section, which for a real fuselage
  almost always means the optimiser diverged rather than that the body is
  genuinely star-shaped.

Recommended behaviour:

1. Per affected station: `DesignWarning(severity="info", reason="superellipse
   exponent hit the n=8.0 bound at station x=…; section is more rectangular than
   the model can represent")`. Count them.
2. **If more than 25 % of stations hit a bound, escalate to
   `severity="warning"`** — at that point the superellipse family is the wrong
   model for this body and the user should be told, not quietly handed a rounded
   box.

### RC-scale note

3D-printed and flat-plate foam RC fuselages are far more likely to be
near-rectangular than the full-scale bodies these methods were calibrated on, so
the `n = 8` bound will be hit much more often in this tool's real population than
the thresholds' provenance suggests. That is the argument for `info` on a single
station and for the 25 % escalation rule rather than a per-station alarm.

### Disagreement + hierarchy resolution

None. `aircraft-design-scholz` **[academic]** supplies the drag sensitivity that
calibrates the bands; `aerosandbox-expert` **[tooling]** supplies how
`volume()` / `area_wetted()` are computed and why a degenerate dimension goes NaN
downstream; `rc-aircraft-designer` **[RC practice]** supplies the population
argument for the `n`-bound severity. Consistent.

### Confidence

**Medium-high.** The failure-mode analysis and the reject cuts are solid; the
0.95 / 0.85 / 0.70 band edges are engineering judgement calibrated on the drag
sensitivity shown above, and should be revisited once ratio statistics exist over
a real corpus of imports.

---

## Q-WD-5 — BR-6: is a segment's root chord the previous segment's tip chord?

### Question

A segment's root chord *is* the previous segment's tip chord, but nothing in the
schema expresses it — a client write silently rewrites the previous segment's tip
chord. Is enforcing that the geometrically correct invariant for a lofted wing,
and are there legitimate cases where a chord discontinuity is wanted?

### What the code does today

The invariant is real in `cad_designer` and documented in three places, enforced
in none:

- `cad_designer/cq_plugins/wing/wing_segment.py:19` — the loft starts from the
  previous segment's **existing** tip wire:
  `airfoil_root_wires = airfoil_root.vals()[-2]`.
- `app/schemas/wing.py:190-192` (docstring) — *"A segment that follows the
  previous segment ... will have the equal geometric properties of its root
  airfoil as the tip airfoil of the previous segment."*
- `app/schemas/copilot_edits.py` (`SetSegment` docstring) — *"The cad_designer
  continuity rule means a segment's root chord follows the previous segment's tip
  chord, so set chord_tip_mm to taper."*

The copilot carries the rule as free text. Nothing validates it at any layer.

### Geometric view

**This is not a convention; it is what "lofted" means.** A loft interpolates a
surface between consecutive **closed sections**. The resulting solid is C⁰ only
if section *k*'s outboard curve and section *k+1*'s inboard curve are the *same*
curve. If they differ, the solid is either non-manifold or carries a **step face**
at the station — and that step face is a real, physical, spanwise-facing surface.

And the invariant is not only about chord: root **airfoil**, root **incidence**
and root **dihedral** are the same continuity condition, which is exactly why the
code stores incidence and dihedral per segment as *tip* properties.

Scholz **[academic]** states the same thing from the aerodynamic side: wing
sections are produced by scaling one airfoil to the local chord along a
**continuous** chord distribution, `c(y) = c_r[1 − (1 − λ)·y/(b/2)]` per panel
(`[[wing-sections-and-scaling]]`, `[[taper-ratio]]`). A double-trapezoidal wing
has a **kink**, not a step: the chord is single-valued at the kink station and
only its *slope* changes (`[[double-trapezoidal-wing-geometry]]`,
`[[kink-position-and-chord]]`).

### Are there legitimate cases wanting a chord discontinuity?

Three candidates. All three dissolve on inspection.

**1. Plug-in / removable outer panels.** Standard RC practice for large spans
**[RC practice]** (`[[rcn-aussenfluegel]]`): *"In RC aircraft with large
wingspans, wings are often divided into separate structural parts for easier
transport… outer wings are commonly referred to as removable or plug-in wings
and must be carefully jointed and aligned to the inner wing or fuselage for
structural integrity."* The division is **structural**, at a joint where the two
panels have **matching** chord. A step there would be a drag-producing defect,
not a feature. **This argues for the invariant, not against it.**

**2. A wider-chord centre section, stub wing, LERX, glove or root fillet.**
These exist, but they are a chord change *with* a leading-edge break, not a step
in the loft: the extra area is added forward and/or aft as a continuous planform
break at a station where the chord is single-valued. **This schema already
expresses that perfectly well** — a short segment whose tip chord differs from
its root chord. What it cannot express is a *zero-length* jump, and a zero-length
jump is precisely the geometry that produces a spanwise step face.

**3. A genuine discontinuity — an unfaired step, a segmented or telescoping
wing.** These are real objects, but their aerodynamics (a spanwise-facing bluff
face, a shed vortex at the step) are outside anything a VLM, a lifting line, or
AeroBuildup can represent. Every solver in the stack builds its own continuous
camber-surface representation from the xsecs
(`[[phd-geometry-degenerate-representations]]` **[tooling]**), so allowing the
geometry would produce an analysis **silently computed on a different wing**.

That last point is decisive for a *design tool*: allowing the step buys a
geometry the whole analysis stack cannot see.

### RC-scale note

No Reynolds dependence — this is topology. The RC-specific input is the plug-in
wing case above, which is the strongest-looking counter-example and turns out to
reinforce the rule.

### CONSENSUS

**Enforce it — and enforce it by removing the field, not by validating it.**

1. **Preferred — make it a read-only derived field.** A segment should not
   *have* a settable root chord: the `WingConfig` segment list already carries
   only `length`, `sweep`, `tip_airfoil` (with its chord) per segment, plus one
   root chord for the wing. Where an API surface does expose a per-segment root
   chord, serialise it (clients need it to render) and **reject it on write**
   with a message naming `chord_tip_mm` on the *previous* segment as the way to
   change it. That converts a silent side effect into an actionable 422.
2. **If it must stay writable for compatibility**, a write setting segment *k*'s
   root chord to a value ≠ segment *k−1*'s tip chord must be **either** rejected
   **or** explicitly propagated with a `DesignWarning` naming the previous
   segment it just modified. The current behaviour — silently rewriting the
   previous segment's tip chord — is the worst of the three options, because the
   client's next `GET` returns a wing it did not ask for.
3. **The copilot's free-text `note` is not enforcement and must not be counted
   as any.** An LLM will violate a note; that is exactly the failure mode the
   note exists to prevent. Keep it (it improves first-try success) but back it
   with (1) or (2).
4. **Tolerance: exact equality after rounding to 1 µm.** Chords are stored in
   mm; this is a topological invariant, not a measurement, and there is no
   physical justification for a tolerance band.

### Disagreement + hierarchy resolution

None. `rc-aircraft-designer` **[RC practice]** supplies the plug-in-wing case
that appears to be a counter-example and on inspection reinforces the rule;
`aircraft-design-scholz` **[academic]** supplies the continuous chord
distribution and the kink-vs-step distinction; `aerosandbox-expert` **[tooling]**
supplies the reason a step would be invisible to every solver. All three agree.

### Confidence

**High.**

---

## Summary table

| Q-id | Recommendation (one line) | Confidence |
|---|---|---|
| **Q-VI-8** | **#791**: ship — camber loss is a pure `C_L0`/`C_m0` offset that provably leaves `C_Lα`, the ac, the neutral point and static margin untouched; but the geometry says the importer's share is ΔC_L0 ≈ 0.10–0.17, not 0.43 (VSPAERO overshoots by more than the importer undershoots), so retitle to "`α_L0` fidelity", warn above 0.5° of `Δα_L0`, and fix the separate lost-XForm-incidence bug. **#792**: accept — keep AeroBuildup default, scale `spanwise_resolution = max(1, round(120/n_sections))` + `chordwise_resolution=8` + `run_symmetric_if_possible`; VLM has no profile drag so it can never be the polar engine at RC scale. | High (physics, cost model); Medium (root-cause attribution) |
| **Q-CO-7** | **The sum is correct; the comment is wrong** — sweep is a chordwise *distance* along an invariant `xDir`, so `x_k = x₀ + Σ sweep_i` and the merged segment must reproduce `x_{j+1} − x_{j−1} = sweep_j + sweep_{j+1}`; a weighted average would halve the sweep in the worked 40 + 80 = 120 mm case. Fix the comment, add that regression test, and warn when the merged segments' dihedrals differ by > 2° (the length sum is only exact at equal dihedral). | High |
| **Q-CO-13** | **Yes — read `ctx["v_cruise_mps"]`** exactly as `_run_stability_async` already does in the same file, and report V, altitude and Re in the summary; replace the fixed α range with **[−6°, +16°] at 1° steps (23 points)**; never sweep velocity (one polar = one Re). At RC scale `Re = v·t_mm·70` means 12 vs 20 m/s is 168 k vs 280 k — where `C_Lmax` varies by −54 % and profile drag nearly doubles, a bigger error than Q-VI-8's camber loss. | High |
| **Q-MS-5** | **No deflection grid — the defect is rank deficiency, not resolution.** Trim is Sadraey's exact 2×2 linear solve (Eq. 12.86/12.90) and AVL solves it by constraint (`D1 PM 0`), not search; with δE frozen at 0 and `C_m0 ≠ 0` the score floor is bounded away from zero however fine the α grid. Use a **two-point secant on δE** (exact in one step, 2× cost); if a grid is mandated, **±25° in 2.5° steps** (Sadraey's tail-separation limit). Add **`CONTROL_AUTHORITY_LIMIT`** as a third status carrying the required δE, tighten trim to `\|C_m\| ≤ 0.01` / `\|ΔC_L\| ≤ 0.02`, and raise the Opti-failure log to WARNING. | High (diagnosis); Medium (specific numbers) |
| **Q-MS-12** | **Store the trimmed `C_L` and solved deflections on the operating point** (constitutive, and fixes Q-MS-6's V-n markers); **derive turn banks from `target_turn_n` via `φ = arccos(1/n)`** — today the hardest turn is n = 2.0 while a user asking n = 3.0 gets no warning; **require `has_pitch_control`** (one variable cannot satisfy two conditions); make `STALL_IN_TURN` a bare token; **re-express the six weights as three tolerances** (0.01 / 0.02 / 0.03, `w = 1/tol²` — reproduces 50 : 15 : 3 within ~2×) plus a `1e-3` regulariser; persist the reference-speed provenance. The 15 targets are a mission point-set, **not** a polar. | High (definitions); Medium (weight re-derivation) |
| **Q-AV-6** | **An inconsistency — but the fix is a merge, not a swap.** `Sref/Cref/Bref/Xref` are **global header** data that "correspond to the total geometry" (avl_doc:289), so a full-airplane file genuinely cannot be reused by deleting surfaces; but spacing, `CDCL`, `CLAF` and `CONTROL` are **per-`SURFACE`** and can be. Lift the matching `SURFACE` block verbatim, always regenerate the header from the pruned wing, warn when no match exists, and report `avl_source` either way. `CDCL` matters most at RC scale — it is AVL's only Reynolds-aware input. Silence is the one unacceptable option. | High |
| **Q-FD-3** | **Not a bare runtime assertion** — the mode that matters most (the `a ↔ b` swap) is volume-neutral and therefore invisible to both an integral metric and any self-consistency check. Instead: **(1)** collapse the two independent `2.0 * a` conversions into one `superellipse_to_asb_xsec()` seam so the convention holds by construction; **(2)** assert against the **STEP bounding box** where a `step_path` survives (`2a ≤ 1.02·Y_extent`; aspect ratio within 20 %) — this doubles as the historical audit query; **(3)** a `[0.3, 3.0]` aspect-ratio plausibility band as a `DesignWarning`, never an exception. | High (analysis); Medium (numbers) |
| **Q-FD-4** | **Good [0.95, 1.05] → silent; degraded [0.85, 1.15] → `info`; poor [0.70, 1.40] → `warning`; reject outside [0.70, 1.40] or `volume_ratio ≤ 0.05` or non-finite.** The 1.40 cut catches the Q-FD-3 factor-2 bug; the ≤ 0.05 / non-finite cut catches the degenerate dimension that already produced 15/15 NaN on the Stratos. Bands are anchored on `C_D0,f = C_f·f_LD·S_wet/S_ref` — 5 % of area ≈ 1 % of aircraft `C_D0`, inside RC Re scatter. **The ratios cannot detect the a↔b swap, cancelling local errors, smoothness, or volume position — say so.** **Yes, warn on a bound-hitting `n`**: `info` per station, escalating to `warning` above 25 % of stations. | Medium-high |
| **Q-WD-5** | **Enforce it — by removing the field, not by validating it.** Root-chord continuity is what "lofted" means: the loft starts from the previous segment's existing tip wire, and a mismatch produces a non-manifold solid or a spanwise step face. All three apparent counter-examples dissolve — plug-in panels are a *structural* split at matching chord, a stub wing/LERX is a kink the schema already expresses, and a genuine step is invisible to every solver in the stack. Make the root chord read-only (422 on write, naming the previous segment's `chord_tip_mm`); if it must stay writable, propagate with a `DesignWarning` — never silently. The copilot's free-text note is not enforcement. | High |

---

### Cross-cutting observations

Three patterns recur across these nine questions and are worth naming once:

1. **Offset errors vs slope errors.** Q-VI-8's camber loss, Q-CO-7's sweep merge
   and Q-CO-13's speed mismatch are all *offset* errors — they move where the
   aircraft sits on a curve without changing the curve's shape. That makes them
   invisible to any check that looks at trends, and it makes stability metrics
   (`dC_m/dα`, neutral point, static margin) survive them intact. Triage
   accordingly: they corrupt trim, incidence and cruise α, not stability.

2. **Silent clipping is the dominant defect shape.** `np.clip(n, 0.5, 8.0)`
   (Q-FD-4), `best_controls = {}` (Q-MS-5), the discarded user `.avl` (Q-AV-6)
   and the silently rewritten tip chord (Q-WD-5) are the same bug four times: a
   plausible-looking result with the degradation removed from the record. Every
   one of them is a `DesignWarning` under ADR 0012.

3. **Reynolds number is the scale-specific multiplier.** At Re 50 k–500 k a
   `C_Lmax` swing of −54 % and a near-doubling of profile drag dwarf several of
   the geometric errors under discussion. Wherever a velocity or a stall speed
   is assumed rather than computed, that assumption deserves to be recorded
   (Q-CO-13, Q-MS-12) — it is usually the largest error term in the result.
