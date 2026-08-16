# Expert consensus — turbulator trip height for RC/UAV wings

> **⚠ CORRECTION (2026-08-15, maintainer).** The brief for this consultation stated
> that a 3D-printed turbulator's height is "quantised by layer height / nozzle width".
> **That premise was wrong** and originated with the interviewer, not with the expert
> sources. The wing is printed **standing on its root rib**: the spanwise axis lies
> along the build direction, so the turbulator height protrudes in the **layer plane
> (XY)** and is *not* layer-quantised — near-arbitrary heights are achievable.
> Wherever this document recommends rounding to a printable quantum, that step is
> void; the computed `k_min` is used directly. No other finding is affected — the
> criterion, the `k_min` procedure, the 0.3 mm-is-subcritical result and the
> single-height (no root/tip pair) conclusion all stand.

**Scope.** Hobby RC and UAV aircraft, 0.5–15 kg, chord-based
Re ≈ 50 000–500 000, airfoils prone to laminar separation bubbles. The
turbulator is either 3D-printed into the wing surface (height quantised by
layer height) or applied as zigzag tape / thread / dots.

**Question it answers.** `Q-WD-10` bullet 3: *"`height_mm` and `form` do not
enter the drag model — the optimiser sweeps position only, while trip height
and form are physically what determine whether transition is forced."*

**Method.** The four installed expert skills were consulted in the authority
order set by `CLAUDE.md`. Where a vault does **not** contain a criterion, this
is stated explicitly rather than papered over. Numbers were computed from the
vault formulae (exact Blasius ODE integration, not the linear approximation)
and the NeuralFoil probes were run against the project's own installed
AeroSandbox.

---

## Sources actually consulted

| Skill | Vault | What it had | What it did **not** have |
|---|---|---|---|
| `aerodynamics-expert` | Anderson, *Fundamentals of Aerodynamics* 6e, 237 concepts | Blasius solution, BL thickness definitions, transition factors, low-Re separation, trip-wire effect on a sphere | **No roughness-Reynolds number, no `Re_k`, no Braslow, no trip-height criterion.** Verified by full-text grep over the whole vault: zero hits for `Re_k`, `Braslow`, `roughness Reynolds`, `trip height`, `transition strip`, `turbulator`. |
| `aircraft-design-scholz` | Scholz HAW lectures + Sadraey, 537 concepts | Cutoff Reynolds number, "laminar flow requires roughness < 0.25 mm", parasite-drag build-up | **No admissible-roughness formula** (`k_adm = 100·l/Re` is *not* in the vault), no excrescence-drag method |
| `aerosandbox-expert` | AeroSandbox docs + Sharpe MS/PhD theses | Exact NeuralFoil input encoding, training distribution, `analysis_confidence` mechanism | — (this question is fully answered) |
| `rc-aircraft-designer` | rc-network wiki + Lennon 1996 + others | Turbulator forms, placement principle, Re range where they help | **No numeric heights anywhere in the vault** |

**Honest gap.** Neither of the two physics/design vaults contains the
quantitative trip criterion. The criterion used below (`Re_k`) is standard
external literature — **Braslow & Knox, NACA TN 4363 (1958)**, and the
follow-up **Braslow, Hicks & Harris, NASA TN D-2648 (1966)**, which give
`Re_k,crit = 600` for three-dimensional distributed roughness particles. I am
confident these documents and that value are real, but they are **not in any
installed vault**, so this is world knowledge, labelled as such. The 2D value
is quoted as a range because I cannot pin it to a single source I am sure of.

---

## Q1 — What criterion determines the minimum trip height?

### Physics / analytical view

Anderson gives the *mechanism* but not the *criterion*. Roughness is listed as
one of the factors that promotes transition, and the trip-wire effect is
described qualitatively for the sphere — an artificially tripped boundary layer
separates much further aft, dropping `C_D` from ≈0.4 to ≈0.1
([[real-flow-sphere-separation]], Anderson 6e §6.6; [[laminar-versus-turbulent-flow]],
§1.11 / §15.2). What is missing is *how tall the wire must be*.

The standard criterion is the **roughness Reynolds number**:

```
Re_k = u_k · k / ν
```

where `k` is the element height and `u_k` is the *undisturbed laminar
boundary-layer velocity at height `k`* — **not** the freestream, and **not**
the edge velocity. Transition is forced at the element once `Re_k` exceeds a
critical value.

| Element type | `Re_k,crit` | Source / confidence |
|---|---|---|
| 3D distributed roughness (grit, dots) | **600** | Braslow & Knox NACA TN 4363 (1958); NASA TN D-2648 (1966). External, high confidence in the value. |
| 2D element (wire, thread, plain tape step) | **≈ 200–400**, take **300** | External literature range; I cannot attribute a single source with confidence. **Medium confidence.** |
| Zigzag / serrated tape | ≈ 300, behaves 2D-like but the serration sheds streamwise vorticity, making it more effective than a plain step of the same height | Inference, not a measured value. **Low–medium confidence.** |

A 2D element is more effective than 3D roughness of the same height because it
disturbs the entire span at once rather than relying on the growth and merging
of discrete wakes — hence the lower critical value.

### Tooling view

Irrelevant to this question: neither NeuralFoil nor AeroSandbox has any notion
of `k` (see Q6).

### RC practice

`[[rcn-turbulator]]` (rc-network wiki, *Turbulator (Aerodynamik)*) states the
principle — *"Better turbulent and attached than laminar and separated"* — and
lists the forms (crinkle/zigzag tape, wire or thread fences, bleed turbulators,
even hairspray overspray for a surface that is "too smooth"). It gives **no
heights** and the placement rule only qualitatively: *"turbulators must be
placed at the location where natural transition would otherwise be delayed."*

### CONSENSUS

**`Re_k = u_k·k/ν ≥ Re_k,crit` is the criterion.** Use `Re_k,crit = 600` for
`form="dots"`, `300` for `form="thread"` and `form="zigzag"`. All four experts
are consistent — the physics vault supplies the boundary-layer machinery, the
critical value comes from outside it, and RC practice does not contradict it.

**Confidence: medium-high** on the form of the criterion, **medium** on the 2D
critical value, **high** on the 3D value.

### Disagreement

None between the experts. The disagreement is between **the criterion and
observed RC practice** — see Q3, where it is real and material.

---

## Q2 — How is `k_min` computed from what the tool already has?

### Physics / analytical view

Everything needed is in the Anderson vault. From
[[blasius-solution-incompressible-flat-plate]] and
[[boundary-layer-thickness-parameters]] (Anderson 6e §18.2):

```
η  = y·√(u_e / (ν·x))            similarity variable
u(y)/u_e = f'(η)                 Blasius profile,  f''(0) = 0.332
δ  = 5.0·√(ν·x/u_e) = 5.0·x/√(Re_x)    (f' = 0.99 at η = 5.0)
```

so `η = 5·y/δ`. Assembling the inputs the tool already has:

```
Re_c = V·c/ν                          local chord Reynolds number
x    = (x/c)·c                        trip station, metres
λ    = u_e/V = √(1 − C_p)             local edge-velocity ratio at the trip
u_e  = λ·V
Re_x = u_e·x/ν = λ·Re_c·(x/c)
```

and the trip criterion becomes an implicit equation in `k`:

```
Re_k(k) = f'(5k/δ) · u_e · k / ν  =  Re_k,crit          … (★)
```

Solve (★) for `k` — one scalar root-find, monotone in `k`, always well posed.

**Closed form, valid only in the linear sublayer.** For `k/δ ≲ 0.3` the profile
is linear, `f'(η) ≈ 0.332η`, and (★) inverts analytically:

```
Re_k ≈ 8.30 · √(Re_x) · (k/δ)²

k_min/c = √(Re_k,crit) · (x/c)^(1/4)
          ────────────────────────────────
          0.576 · λ^(3/4) · Re_c^(3/4)
```

(`0.576 = √0.332`.) Hence the scaling laws:

```
k_min ∝ Re_c^(−3/4)     ← lower Re needs a TALLER trip
k_min ∝ (x/c)^(1/4)     ← very weak dependence on trip position
k_min ∝ λ^(−3/4)        ← faster local flow needs a shorter trip
k_min ∝ c^(1/4)   at fixed V   ← see Q5
```

> **Implementation warning — do not ship the closed form alone.** At RC
> Reynolds numbers `k_min/δ` lands at **0.3–0.9**, i.e. `η_k` = 1.5–4.5, well
> outside the linear region. There the linear form overestimates `u_k` by 10–25 %
> and therefore **under**-estimates `k_min`. Checked numerically: for the
> 200 mm / 8 m/s glider case at `x/c = 0.3`, linear gives 0.93 mm, the exact
> Blasius root gives 1.04 mm (12 % low). Use (★) with the real `f'`.

**Embeddable `f'(η)` table** (integrated here from `2f''' + f·f'' = 0`,
`f''(0) = 0.33206`, matching the vault's quoted 0.332). Piecewise-linear
interpolation on this grid is accurate to `8.8e-4` in `f'`:

```
η  = 0.00 0.25 0.50 0.75 1.00 1.25 1.50 1.75 2.00 2.25 2.50
     2.75 3.00 3.25 3.50 3.75 4.00 4.25 4.50 4.75 5.00
f' = 0.0000 0.0830 0.1659 0.2483 0.3298 0.4096 0.4868 0.5605 0.6298 0.6936 0.7513
     0.8022 0.8460 0.8829 0.9130 0.9370 0.9555 0.9694 0.9795 0.9867 0.9915
```

(clamp `f' = 1.0` for `η > 5`).

**Two systematic biases, both in the unsafe direction:**

1. **Pressure gradient.** Blasius is a *zero*-pressure-gradient solution. A
   turbulator normally sits aft of the pressure minimum, in the adverse
   gradient — exactly where Anderson notes the boundary layer is decelerating
   ([[boundary-layer-transition-separation]], §4.12.3). An adverse gradient
   makes the profile *less full*, lowering `u_k` for the same `k`. Using the
   Falkner-Skan wall-shear ratio for a mild adverse gradient (β ≈ −0.1,
   `f''(0)` drops from 0.332 to ≈0.22), `k_min` grows by roughly
   `√(0.332/0.22) ≈ 1.25`. **Apply a factor of ≈1.25 when the trip is aft of
   the pressure minimum.**
2. **λ.** If the tool does not have a `C_p` distribution, `λ = 1.0` is the
   conservative default (gives a larger `k_min`). `λ = 1.15–1.25` is typical
   for an upper surface at moderate `C_L`.

**Independent cross-check against the Scholz vault.** `[[exam-wave-drag-estimation]]`
(Scholz, *17_Klausur_SS19* Q1.23) states that natural laminar flow *"requires
smooth surfaces (roughness < 0.25 mm)"*. Running (★) backwards for a transport
wing — `c = 5 m`, `V = 250 m/s`, FL350 (`ν = 3.9e−5`), `x/c = 0.1`,
`Re_k,crit = 600` — gives **`k_min = 0.282 mm`**. The two agree to within 13 %,
from completely independent sources. This is the strongest validation available
for the whole procedure.

### CONSENSUS

Solve (★) numerically with the tabulated Blasius `f'`; multiply by ≈1.25 when
the trip lies in the adverse-gradient region. **Confidence: high** on the
procedure, **medium** on absolute accuracy (the flat-plate assumption is the
weak link).

### Disagreement

None. Scholz's 0.25 mm datum independently corroborates the Anderson-derived
result.

---

## Q3 — Typical real numbers, and does 0.3 mm hold up?

### Physics / analytical view — computed `k_min` [mm]

Exact Blasius root of (★), `λ = 1.2`, `ν = 1.5e−5` (the value the service
already uses, `turbulator_optimizer_service.py:396`):

**`Re_k,crit = 300` (thread / zigzag)**

| Case | c [mm] | V [m/s] | Re_c | x/c=0.2 | 0.3 | 0.5 | 0.7 | δ@0.3 |
|---|---|---|---|---|---|---|---|---|
| glider tip, slow | 100 | 8 | 53 000 | 0.55 | 0.59 | 0.65 | 0.71 | 1.08 |
| glider, thermalling | 200 | 8 | 107 000 | 0.62 | 0.68 | 0.77 | 0.83 | 1.53 |
| glider, cruise | 200 | 15 | 200 000 | 0.38 | 0.42 | 0.47 | 0.51 | 1.12 |
| trainer | 150 | 12 | 120 000 | 0.43 | 0.47 | 0.52 | 0.57 | 1.08 |
| F3B/F5B fast | 180 | 25 | 300 000 | 0.25 | 0.28 | 0.31 | 0.34 | 0.82 |
| small UAV | 250 | 20 | 333 000 | 0.32 | 0.35 | 0.40 | 0.44 | 1.08 |
| larger UAV | 350 | 22 | 513 000 | 0.32 | 0.36 | 0.41 | 0.44 | 1.22 |

**`Re_k,crit = 600` (dots / grit)** — same cases: 0.94/0.99/0.58/0.67/0.37/0.47/0.47 mm
at `x/c = 0.2`, rising to 1.07/1.21/0.74/0.83/0.49/0.63/0.63 at `x/c = 0.7`.

**What the project default actually achieves.** A 0.3 mm trip at `x/c = 0.3`,
`λ = 1.2`, delivers:

| Case | Re_k @ x/c 0.2 | 0.3 | 0.5 | 0.7 | Verdict |
|---|---|---|---|---|---|
| glider tip, slow | 105 | 87 | 68 | 58 | **subcritical** |
| glider, thermalling | 76 | 62 | 48 | 41 | **subcritical (≈10× short)** |
| glider, cruise | 191 | 158 | 123 | 105 | **subcritical** |
| trainer | 157 | 130 | 102 | 86 | **subcritical** |
| F3B/F5B fast | 414 | 349 | 276 | 235 | marginal — 2D only |
| small UAV | 262 | 217 | 170 | 144 | **subcritical** |
| larger UAV | 258 | 213 | 166 | 140 | **subcritical** |

**The 0.3 mm default does not hold up.** It is subcritical across essentially
the whole RC/UAV envelope, and it is *worst* exactly where turbulators matter
most — the slow, low-Re thermalling case, where it falls short by a factor
of ~5 in `Re_k` (and `Re_k ∝ k²`, so ~2.3× in height).

**A second, sharper finding:** at Re ≈ 50–110 k the `Re_k,crit = 600` height
lands at **`k/δ = 0.68–0.89`** — the element would fill most of the boundary
layer, which is squarely in the over-trip form-drag regime of Q4. That is not a
tuning problem, it is a statement about form: **discrete 3D roughness (`dots`)
is the wrong turbulator form below Re ≈ 150 k.** Only the lower-`Re_k,crit` 2D
forms (`thread`, `zigzag`) can be made critical without becoming bluff bodies.

### RC practice

Two data points from the vault, and they pull in opposite directions:

- `[[rcn-turbulator]]` (rc-network wiki) — forms and placement, **no heights**.
- Lennon, *The Basics of R/C Model Aircraft Design* (1996), airfoil-construction
  sidebar: *"Most powered model aircraft operate in an Rn range from 200,000 to
  well over 1,000,000. **This is above the critical range of Rns at which
  turbulators are considered to be effective.**"* — i.e. Lennon puts the useful
  ceiling below ≈200 k.

Commonly used commercial zigzag tape ("Zackenband") for gliders is **0.3–0.5 mm**
thick — that is community practice, **not from the vault**, flagged as such.
Which sets up the real disagreement below.

### CONSENSUS

Replace the 0.3 mm default with **0.5 mm**. Checked across the whole table
above, 0.5 mm delivers `Re_k` = 168–853 (`k/δ` = 0.33–0.61) — critical or
near-critical for the 2D forms everywhere and never in the over-trip regime.
It is also a clean multiple of common FDM layer heights (0.1 / 0.25 mm) and
2 × the 0.25 mm typical layer. For the slowest, largest-chord thermal cases
0.6–0.8 mm is better.

**Confidence: high** that 0.3 mm is too small; **medium** on 0.5 mm as the
single best default, since it depends on where in the envelope the user sits.

### Disagreement — and it is real

**Braslow-type theory says RC zigzag tape at 0.3 mm should not work. RC
practice says it demonstrably does, on F3B/F3J gliders at Re 100–300 k.**
Do not smooth this over. Three reconciling mechanisms, in decreasing
confidence:

1. **The criterion is for an *attached, stable* Blasius layer — the worst
   case.** At Re 50–500 k with a laminar separation bubble present, a trip
   placed at or just upstream of laminar separation acts on an *inflectional*
   velocity profile, which is Rayleigh-unstable and amplifies disturbances
   orders of magnitude faster. Far less disturbance energy is needed.
   Anderson supports the premise: at Re_c = 100 000 the laminar solution
   separates on *both* surfaces while the turbulent one stays fully attached
   ([[flow-over-airfoil-low-reynolds]], §20.3.2).
2. **Freestream turbulence.** `Re_k,crit = 600` derives from quiet-tunnel work.
   The Anderson vault flags this directly: transition occurs at Re_x ≈ 500 000
   *in a quiet wind tunnel* but ≈ **100 000** in a typical environment
   ([[laminar-versus-turbulent-flow]], noting the source conflict between
   Anderson §1.11 and §15.2). Real RC flight — atmospheric turbulence, prop
   wash — is the "typical environment" case, a 5× reduction in the transition
   Reynolds number.
3. **Serration.** A zigzag is not a plain 2D step; the sawtooth generates
   streamwise vorticity, which is a far more efficient transition mechanism per
   unit height.

**How the hierarchy resolves it.** `aerodynamics-expert` outranks
`rc-aircraft-designer`, so the physics criterion governs — but the correct
reading of the physics is that **`Re_k ≥ Re_k,crit` is a *sufficient*
condition, not a necessary one.** Therefore: treat `k ≥ k_min` as "transition
is guaranteed, the computed polar is trustworthy" and `k < k_min` as
"transition is *plausible but unproven*, the polar may be optimistic" — a
graded warning, never a hard rejection. This is the single most important
design decision in this document.

Note also that Lennon's ≤200 k ceiling is **contradicted by modern practice**
(F3B/F5J gliders run turbulators well above 200 k) and by the NeuralFoil
evidence in Q7, which shows a real benefit up to ≈200 k and essentially none at
400 k. Lennon is 1996 hobbyist material and the lowest authority here; treat
his ceiling as roughly right in spirit (the benefit does die out) but not as a
number to encode.

---

## Q4 — Is there an upper bound?

### Physics / analytical view

Yes, and there are two independent bounds that bite in the same place.

**Bound 1 — saturation.** Once `Re_k > Re_k,crit`, transition is already fixed
at the element. Additional height buys **nothing** aerodynamically; it only
adds drag. The optimum is therefore the *smallest* `k` satisfying the
criterion, plus a safety margin — never "more is safer".

**Bound 2 — the element's own form drag.** A protrusion of height `k`
immersed in the boundary layer sheds a wake. Estimating it as a bluff body
integrated against the local dynamic pressure profile:

```
Δcd_trip ≈ C_D,k · (k/c) · λ² · (1/k)∫₀^k (u/u_e)² dy
         ≈ 0.92 · C_D,k · λ² · (k/c) · (k/δ)²          [linear profile]
```

with `C_D,k ≈ 1.0` for a 2D fence (use ~0.5 for a zigzag, which blocks roughly
half the span). **This is constructed here from first principles — it is not a
published correlation.** Label it as an engineering estimate. Neither the
Anderson nor the Scholz vault contains an excrescence-drag method;
`[[parasite-drag-analysis]]` mentions "miscellaneous items (antennas,
protuberances, gaps)" inside `C_D,0` but gives no formula.

The important structural result is the **cubic scaling, `Δcd_trip ∝ k³`**
(`k/c` × `(k/δ)²`). The penalty is negligible while `k` is small and blows up
suddenly. Worked for a 200 mm / 12 m/s glider at `x/c = 0.3` (δ = 1.25 mm,
`k_min` = 0.40 mm at `Re_k,crit` 300):

| k [mm] | k/δ | Re_k | Δcd_trip | as % of cd ≈ 0.012 |
|---|---|---|---|---|
| 0.2 | 0.16 | 51 | 0.000034 | 0.3 % |
| 0.3 | 0.24 | 113 | 0.000114 | 1.0 % |
| 0.4 | 0.32 | 198 | 0.000271 | 2.3 % |
| 0.5 | 0.40 | 302 | 0.000530 | 4.4 % |
| 0.6 | 0.48 | 420 | 0.000916 | 7.6 % |
| 0.8 | 0.64 | 673 | 0.002171 | 18 % |
| 1.0 | 0.80 | 917 | 0.004239 | 35 % |
| 1.5 | 1.20 | 1439 | 0.014308 | **119 %** |
| 2.0 | 1.60 | 1920 | 0.033915 | **283 %** |

For reference, the bubble-kill benefit measured with NeuralFoil (Q7) is 19 % of
`cd` at Re 100 k and 40 % at Re 60 k. So the trip pays for itself up to about
`k/δ ≈ 0.6–0.7` and is a net loss beyond `k/δ ≈ 0.8`.

**Criterion:** `k/δ ≲ 0.5` is comfortable, `0.5–0.8` is a caution band,
`> 0.8` means the trip almost certainly costs more than the bubble it removes.
Above `k ≈ δ` the element is no longer a boundary-layer device at all — it is a
spoiler in the outer flow.

### RC practice

Consistent, qualitatively: `[[rcn-grenzschicht]]` notes that at model
Reynolds numbers the laminar boundary layer is "a few millimetres" thick —
matching the computed δ = 0.8–1.5 mm above — and that a turbulent layer is
thicker and higher-drag. The "hairspray overspray" trick in `[[rcn-turbulator]]`
is the extreme low-`k` end of the same spectrum and shows practitioners
instinctively reach for the smallest effective disturbance.

### CONSENSUS

Two-sided bound: `k_min ≤ k ≤ ~0.5·δ`, and inside that band pick the
**smallest** `k` that clears the criterion with margin. Where the band is
empty — which happens for `form="dots"` below Re ≈ 150 k — the form is wrong,
not the height.

**Confidence: high** on the qualitative shape (saturation above, cubic penalty
below), **low–medium** on the absolute `Δcd_trip` numbers, since the formula is
my own construction with an assumed `C_D,k`.

### Disagreement

None between experts; the vaults are simply silent, so this answer leans on
constructed physics and is labelled accordingly.

---

## Q5 — Does trip height need to vary spanwise?

### Physics / analytical view

This one has a clean analytic answer. From Q2, at fixed flight speed
`Re_c ∝ c`, so:

```
k_min ∝ c · Re_c^(−3/4) ∝ c · c^(−3/4) = c^(1/4)
```

**The required trip height scales with the fourth root of local chord.** That
is an extremely weak dependence:

| Taper ratio | k_min(tip)/k_min(root) | If k is fixed at the root value: Re_k(tip)/Re_k(root) |
|---|---|---|
| 1.0 | 1.00 | 1.00 |
| 0.7 | 0.92 | 1.20 |
| 0.5 | 0.84 | 1.41 |
| 0.4 | 0.80 | 1.58 |
| 0.3 | 0.74 | 1.83 |

Even at an aggressive taper of 0.3, the required height changes by only 26 %
root→tip. Since the tip needs *less* height than the root, **sizing one height
at the root covers the whole span**, and the tip merely ends up 1.2–1.8× over
critical in `Re_k` — comfortably inside the acceptable band from Q4 and nowhere
near the `k/δ > 0.8` cliff.

Against this, a 3D-printed trip is quantised to the layer height: 0.1–0.3 mm
steps. A 0.5 mm trip on a λ=0.5 taper would want 0.42 mm at the tip — **less
than one layer of difference.** The physical variation is below the
manufacturing resolution.

### Tooling view

The stored `Turbulator` already carries `position_root` / `position_tip` and the
service interpolates `xtr` linearly along the span
(`compute_delta_cd0_from_turbulator_position`, `turbulator_optimizer_service.py:687-689`).
Adding `height_root_mm` / `height_tip_mm` would double the field count and the
UI surface for an effect that is sub-quantisation.

### RC practice

No vault content. Community practice is to apply one tape of one thickness
across the span, which is consistent.

### CONSENSUS

**One `height_mm` per turbulator is adequate. Do not add a root/tip height
pair.** Size it at the **root** (largest chord ⇒ largest `k_min`) and at the
**slowest** relevant speed (see Q7). Report the tip's resulting `Re_k` and
`k/δ` as a check, not as a second input.

**Confidence: high.** The `c^(1/4)` law is a direct consequence of the Q2
derivation and the conclusion is robust to a factor-of-2 error in `Re_k,crit`
(which only shifts `k` by √2 uniformly, not the root/tip *ratio*).

### Disagreement

None. This is the one question where all four sources trivially agree, because
the physics is decisive.

---

## Q6 — What does NeuralFoil's `xtr_upper` actually model?

### Tooling view — verified two ways

**From the vault.** `[[phd-neuralfoil-physics-informed-design]]` (Sharpe PhD
thesis 2024, §7.2) gives NeuralFoil's 25-dimensional input latent space
verbatim (Eq. 7.1):

```
z_in = Affine[ Airfoil shape (18 CST parameters),
               sin(2α), sin²(α), cos(α),
               ln(Re_c), N_crit,
               xtr,top,forced,  xtr,bot,forced ]
```

The parameter is literally named **`xtr,top,forced`**.

**From the installed source**, which is the authority for this project.
`neuralfoil/main.py:108`:

> *"`xtr_upper`: Forced transition location on the upper surface, as a fraction
> of chord (x/c). 1.0 allows fully natural transition."*

and the input vector assembly at `main.py:163-177` is
`[…8 upper CST weights, 8 lower CST weights, LE weight, TE thickness×50,
sin2α, cosα, 1−cos²α, (ln Re −12.5)/3.5, (n_crit−9)/4.5, xtr_upper, xtr_lower]`.

Three consequences follow directly and are not matters of opinion:

1. **`xtr_upper` is XFoil's `XTR` setting — "transition is forced here",
   mechanism-agnostic.** It is a pure boundary-condition switch on the
   transition model.
2. **The geometry input is completely independent of it.** The 18 CST
   parameters describe the clean airfoil. Setting `xtr_upper = 0.35` does not
   perturb the shape by one micron. **NeuralFoil therefore models none of the
   trip's own form drag** — the `Δcd_trip` of Q4 is entirely outside the model
   and must be added by the caller if it is to be counted at all.
3. **NeuralFoil is structurally blind to trip height.** There is no `k`, no
   roughness, no `Re_k` anywhere in the 25 inputs. It cannot tell a 0.1 mm trip
   from a 2 mm one, and it will happily report the drag benefit of a forced
   transition that no physically realisable element at that location would
   actually produce.

**Training coverage.** `[[phd-neuralfoil-training-data-generation]]` (§7.2.5):
of 7.9 M cases, forced trip locations were **"80 % natural; 20 % uniform in
[0,1]"**, with `Re_c` log-normal, 95 % within [1.87 k, 262 M], and
`N_crit` uniform on [0,18]. So the RC range 50–500 k with a forced trip is
inside the training distribution, though the trip cases are only a fifth of it.

**`analysis_confidence`** is a binary classifier for *"did XFoil converge for
these inputs?"*, modified by subtracting the squared Mahalanobis distance of
the query from the training distribution so that confidence provably → 0 far
from training data ([[phd-neuralfoil-analysis-confidence]], §7.2.4). The vault
is explicit that XFoil failures *"cluster in regions where flow physics is
delicate (separation bubbles, transitional Reynolds numbers, massive
separation)"* — i.e. **precisely this application**. The service's existing
0.80 floor (`turbulator_optimizer_service.py:56`) is below the 0.90 the vault
recommends for conventional low-speed work ([[nfoil-analysis-confidence-constraint]]).
Measured values in the Q7 probe were 0.87–0.98, dipping to 0.87–0.89 at CL 1.2.

### Physics view

The physics side agrees and adds the reason it matters: forced-transition
analysis is a *counterfactual*. It answers "what would the drag be if the flow
tripped here", which is only useful if something actually trips it there.

### CONSENSUS

**Confirmed, unambiguously.** `xtr_upper` means "assume transition at this
x/c", full stop. The optimiser's premise is therefore sound *as a
position-optimiser* but its result is **conditional on an unstated physical
assumption** — that a trip exists which is tall enough. The whole `k_min`
proposal rests on this being true, and it is.

**Confidence: high.** Verified in the vault *and* in the installed source.

### Disagreement

None. This is a factual question and the fact is settled.

---

## Q7 — Is minimising `cd` at one (CL, Re) the right objective?

### Tooling view — measured, not argued

Run against the project's own AeroSandbox/NeuralFoil, airfoil `e205`,
`XTR_GRID = linspace(0.2, 0.9, 15)`, the service's own `_cd_at_cl_xtr`
interpolation:

| Re | CL | cd natural | natural Top_Xtr | conf | xtr_opt | cd_opt | gain |
|---|---|---|---|---|---|---|---|
| 60 000 | 0.3 | 0.02064 | 0.831 | 0.97 | 0.450 | 0.01608 | **22.1 %** |
| 60 000 | 0.6 | 0.02928 | 0.702 | 0.95 | 0.350 | 0.01762 | **39.8 %** |
| 60 000 | 0.9 | 0.03883 | 0.550 | 0.95 | 0.300 | 0.02301 | **40.7 %** |
| 60 000 | 1.2 | 0.04753 | 0.168 | 0.89 | 0.400 | 0.04226 | 11.1 % |
| 100 000 | 0.6 | 0.01756 | 0.652 | 0.96 | 0.350 | 0.01420 | **19.1 %** |
| 100 000 | 0.9 | 0.02152 | 0.528 | 0.97 | 0.300 | 0.01759 | 18.2 % |
| 200 000 | 0.6 | 0.01184 | 0.592 | 0.98 | 0.400 | 0.01137 | 4.0 % |
| 200 000 | 0.9 | 0.01305 | 0.509 | 0.98 | 0.500 | 0.01303 | 0.1 % |
| 400 000 | 0.6 | 0.00861 | 0.541 | 0.98 | 0.900 | 0.00862 | **−0.0 %** |
| 400 000 | 0.9 | 0.00957 | 0.465 | 0.98 | 0.900 | 0.00962 | **−0.5 %** |

Three things fall out:

1. **The benefit is overwhelmingly a low-Re phenomenon.** 40 % at Re 60 k,
   19 % at 100 k, 4 % at 200 k, **zero or negative at 400 k**. At 400 k the
   argmin lands on the grid boundary (0.9) — the existing boundary-solution
   warning (`turbulator_optimizer_service.py:263-268`) correctly fires; it
   means "no interior optimum exists", i.e. *this wing does not want a
   turbulator*.
2. **The single-point objective is defensible where it matters.** At Re 100 k,
   taking the CL = 0.6 optimum (`xtr = 0.35`) and applying it across the range
   costs only **+0.0 % / +1.9 % / +4.1 % / +0.2 %** versus the per-CL optimum
   at CL 0.6 / 0.9 / 0.3 / 1.2. The `cd(xtr)` curve is flat near its minimum,
   so the answer is not sensitive to the design point. The apparent "spread" of
   `xtr_opt` at Re 200–400 k (0.6–0.7 in x/c) is an artefact of there being no
   real optimum to find, not genuine sensitivity.
3. **The trip position must respect natural transition.** `Top_Xtr` marches
   forward with CL — 0.83 → 0.17 at Re 60 k, and 0.02 at Re 200 k / CL 1.2.
   A trip aft of natural transition is **inert**: the flow is already turbulent
   there. Sweeping `xtr` out to 0.9 at high CL evaluates physically meaningless
   points.

### Physics view

Agrees, and supplies the argument the tooling cannot see. The trip is a fixed
piece of geometry but `Re_k ∝ V^1.5` at fixed geometry (from Q2:
`Re_k ∝ λ^1.5 Re_c^1.5`). So:

| Speed | Re_k factor | k_min factor |
|---|---|---|
| ×1.0 | 1.00 | 1.00 |
| ×0.7 | 0.59 | 1.31 |
| ×0.5 | 0.35 | 1.68 |

**A trip sized at cruise goes subcritical when the aircraft slows down** — and
slow flight (thermalling, high CL) is exactly when the bubble is worst and the
turbulator is most needed. Halving the speed costs a factor 2.8 in `Re_k`.
This is the decisive argument for evaluating across the operating range rather
than at one point, and it is a *height* argument that no amount of position
optimisation can surface.

### RC practice

Lennon's ≤200 k effectiveness ceiling (Q3) is directionally confirmed by the
measurements above — the benefit is 4 % at 200 k and gone by 400 k — while
being too pessimistic about the 100–200 k band where a real 19 % / 4 % remains.

### CONSENSUS

**Keep the single-point argmin for *position*** — it is cheap, stable, and the
optimum is flat. **But evaluate the *height* across the operating range**, and
size `k` at the **lowest** speed at which the turbulator is expected to work,
not at cruise. Additionally, report the `xtr_opt` and gain at 2–3 points
(minimum-speed / cruise / high-CL) so the user can see that the device is
worthless above ≈200–300 k rather than reading a boundary-solution `xtr_opt`
as a recommendation.

**Confidence: high** on the measured Re-dependence and the flat optimum
(directly measured against the project's own stack); **high** on the `V^1.5`
argument (algebra from Q2).

### Disagreement

`rc-aircraft-designer` (Lennon) says turbulators are ineffective above
≈200 000; the NeuralFoil measurements show a real if modest 4 % at 200 000 and
nothing at 400 000. **Scholz/physics wins on the hierarchy, but here the
tooling measurement is the better evidence and it splits the difference.**
Practical resolution: warn — do not block — above Re ≈ 250 k.

---

## Recommended procedure

Inputs already available per section in `WingSectionData`: `chord_m`,
`re_local`, `cl`, `airfoil_name`, plus the turbulator's `position_root` /
`position_tip`, `form`, `height_mm`.

### Step 1 — Establish the sizing station and speed

- **Station:** the wing **root** of the segment carrying the turbulator
  (largest chord ⇒ largest `k_min`; Q5).
- **Speed:** the **lowest** speed in the operating range at which the
  turbulator is expected to work — typically `1.1–1.3 × V_stall`, *not*
  cruise (Q7). If only one operating point exists, use it but emit a notice
  that the height is not validated at low speed.

### Step 2 — Local flow quantities at the trip

```python
nu   = 1.5e-5
x_c  = position at this station          # 0..1, interpolated root→tip
Re_c = V * c / nu
lam  = 1.0                                # or sqrt(1 - Cp) if a Cp distribution exists
u_e  = lam * V
x    = x_c * c
delta = 5.0 * sqrt(nu * x / u_e)          # Blasius, metres
```

### Step 3 — Critical roughness Reynolds number by form

| `form` | `Re_k,crit` |
|---|---|
| `"dots"` | 600 |
| `"zigzag"` | 300 |
| `"thread"` | 300 |

### Step 4 — Solve for `k_min`

Root-find on `k` (bisection over `[1e-7, 0.05]` m; monotone, always converges):

```
g(k) = f_prime(5*k/delta) * u_e * k / nu  -  Re_k_crit  = 0
```

with `f_prime` = linear interpolation over the 21-point Blasius table in Q2
(clamped to 1.0 above η = 5). **Do not use the closed-form linear
approximation** — it under-predicts `k_min` by 10–25 % at RC Reynolds numbers.

Then apply the adverse-gradient correction (Q2):

```
if x_c > x_c_of_pressure_minimum (use 0.3 as a fallback threshold):
    k_min *= 1.25
```

### Step 5 — Round to a printable height

```
k_print = ceil(k_min * safety / layer_height) * layer_height
```

with `safety = 1.2` and `layer_height` a user setting (default 0.2 mm; typical
FDM 0.1 / 0.15 / 0.2 / 0.25 / 0.3). Always round **up** — the penalty for one
extra layer is `Δcd ∝ k³` and small in this band, whereas being subcritical
loses the entire benefit.

### Step 6 — Classify the *stored* `height_mm` and warn

Compute `Re_k_actual = f_prime(5*k/delta) * u_e * k / nu` and `k/delta` for the
stored height, then:

| Condition | Severity | Message |
|---|---|---|
| `Re_k_actual < 0.5 · Re_k,crit` | **ERROR** | Trip height `k` mm is far below the `k_min` mm needed to force transition at x/c. The computed polars assume forced transition that this trip will not produce — treat ΔCD0 and L/D as optimistic. |
| `0.5 ≤ Re_k_actual/Re_k,crit < 1.0` | **WARNING** | Marginal: transition may occur (a separation bubble lowers the effective threshold) but is not guaranteed. Recommended height: `k_print` mm. |
| `1.0 ≤ Re_k_actual/Re_k,crit ≤ 3.0` **and** `k/δ ≤ 0.5` | **OK** | — |
| `Re_k_actual/Re_k,crit > 3.0` **or** `0.5 < k/δ ≤ 0.8` | **NOTICE** | Over-tripped: transition is already forced at `k_min` mm; the extra height adds ≈`Δcd_trip` in form drag for no benefit. |
| `k/δ > 0.8` | **WARNING** | Trip height is `k/δ` of the local boundary-layer thickness — it is acting as a spoiler, not a turbulator. Estimated form-drag penalty `Δcd_trip` exceeds the bubble-drag saving. |
| `form == "dots"` and `Re_local < 150 000` | **WARNING** | Discrete 3D roughness needs `Re_k ≈ 600`, which at this Reynolds number requires `k/δ > 0.65`. Use `zigzag` or `thread` instead. |
| `x_c > natural Top_Xtr` at the design CL | **NOTICE** | Trip sits aft of natural transition (`Top_Xtr`) — it is inert at this operating point. |
| `Re_local > 250 000` and optimiser gain < 2 % | **NOTICE** | Turbulator gives negligible benefit at this Reynolds number. |

The estimated penalty for the message text:
`Δcd_trip ≈ 0.92 · C_D,k · λ² · (k/c) · (k/δ)²`, `C_D,k` = 1.0 for
`thread`, 0.5 for `zigzag`/`dots` — labelled in the UI as an **order-of-magnitude
engineering estimate**, since it is not a published correlation.

### Step 7 — Carry the caveat in the response

Per `Q-WD-10` bullet 3 and the `airfoil-catalog` precedent, the
`/turbulator/optimize` response must carry an explicit caveat block, because
the caveat is structural and not a fixable bug:

> NeuralFoil's `xtr_upper` forces transition at the given x/c regardless of
> mechanism. It models neither the trip height needed to achieve that
> transition nor the trip's own form drag. `height_mm` and `form` are checked
> separately against a roughness-Reynolds criterion and reported as warnings;
> they do not enter the drag model.

### Step 8 — Change the default

`Turbulator.height_mm` default `0.3` → **`0.5`**
(`cad_designer/airplane/aircraft_topology/wing/Turbulator.py:27,75`). This is a
`cad_designer` topology change and falls under the same gh-934 approved
exception that introduced the class. *(Not applied — this document makes no
code changes.)*

---

## Summary table

| # | Question | Answer | Confidence | Disagreement |
|---|---|---|---|---|
| 1 | Minimum-height criterion | `Re_k = u_k·k/ν ≥ Re_k,crit`; **600** for 3D roughness (Braslow & Knox, NACA TN 4363, 1958 — *external, not in any vault*), **≈300 (200–400)** for 2D elements | med-high / med on the 2D value | none between experts |
| 2 | How to compute `k_min` | Root-find `f'(5k/δ)·u_e·k/ν = Re_k,crit` with the tabulated Blasius `f'`; `δ = 5.0√(νx/u_e)`; ×1.25 in an adverse gradient. Closed form `k_min/c = √Re_k,crit·(x/c)^¼ / (0.576·λ^¾·Re_c^¾)` valid only for `k/δ ≲ 0.3` | high | none — Scholz's 0.25 mm datum independently reproduces the method to 13 % |
| 3 | Real numbers; is 0.3 mm OK? | `k_min` = **0.25–0.85 mm** across the envelope (`Re_k,crit` 300). **0.3 mm is subcritical almost everywhere**, worst at low speed. Recommend **0.5 mm** default | high that 0.3 mm is too small; med on 0.5 mm | **Yes — real.** Theory says 0.3 mm zigzag shouldn't work; RC practice says it does. Resolved by treating `Re_k ≥ Re_k,crit` as *sufficient, not necessary* ⇒ graded warning, never a hard block |
| 4 | Upper bound | Saturates above `Re_k,crit`; penalty `Δcd_trip ∝ k³`. Comfortable `k/δ ≲ 0.5`; caution 0.5–0.8; net loss above ≈0.8 | high on shape, low-med on absolute Δcd | none (vaults silent; formula constructed here) |
| 5 | Spanwise variation | **`k_min ∝ c^(1/4)`** — ≤26 % root→tip even at taper 0.3, below print quantisation. **One height per turbulator; size at the root.** Do **not** add `height_root/tip_mm` | high | none |
| 6 | What `xtr_upper` models | "Transition is forced here", mechanism-agnostic. Input latent space is `[…CST, sin2α, sin²α, cosα, lnRe, N_crit, xtr_top_forced, xtr_bot_forced]`; geometry is independent of it ⇒ **blind to `k`, and models no trip form drag**. Verified in the Sharpe PhD vault §7.2 **and** in installed `neuralfoil/main.py:108,163-177` | high | none — factual |
| 7 | Single-point objective | Position: **fine** — measured penalty of the design-CL optimum at off-design CL is +0.0…+4.1 % at Re 100 k. Height: **no** — `Re_k ∝ V^1.5`, so a cruise-sized trip goes subcritical at 0.5×V by 2.8×. Benefit measured: 40 % @60 k, 19 % @100 k, 4 % @200 k, **0 % @400 k** | high | Lennon caps usefulness at 200 k; measurement shows 4 % at 200 k, 0 % at 400 k. Warn above ≈250 k, don't block |

### Citations used

- Anderson, *Fundamentals of Aerodynamics* 6e — [[blasius-solution-incompressible-flat-plate]] §18.2, [[boundary-layer-thickness-parameters]] §18.2, [[boundary-layer-transition-separation]] §4.12.3–4.12.4, [[laminar-versus-turbulent-flow]] §1.11/§15.2, [[flow-over-airfoil-low-reynolds]] §20.3.2, [[real-flow-sphere-separation]] §6.6, [[airfoil-drag-skin-friction]] §4.12
- Sharpe, PhD thesis 2024 — [[phd-neuralfoil-physics-informed-design]] §7.2, [[phd-neuralfoil-training-data-generation]] §7.2.5, [[phd-neuralfoil-analysis-confidence]] §7.2.4; AeroSandbox docs — [[nfoil-rapid-airfoil-analysis]], [[nfoil-get-aero-from-neuralfoil]], [[nfoil-analysis-confidence-constraint]]
- Scholz — [[exam-wave-drag-estimation]] (*17_Klausur_SS19* Q1.23), [[parasite-drag-analysis]] (*05_PreliminarySizing* §5.4)
- rc-network wiki — [[rcn-turbulator]] (*Turbulator (Aerodynamik)*), [[rcn-grenzschicht]], [[rcn-re-zahl]]; Lennon, *The Basics of R/C Model Aircraft Design* (1996), airfoil-construction sidebar
- **External, not in any installed vault:** Braslow & Knox, NACA TN 4363 (1958); Braslow, Hicks & Harris, NASA TN D-2648 (1966)
- Installed source read directly: `neuralfoil/main.py:71-72, 108-112, 163-177`
