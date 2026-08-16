# Expert consensus — lateral/vertical CG, turn load factor, mission propagation

Rulings on `Q-MB-3`, `Q-MS-13` (the bank ↔ `target_turn_n` item only) and
`Q-MS-10b`, to the extent they are decidable by domain expertise rather than
maintainer preference.

**Scope framing (governs every answer below).** RC model aircraft and small UAVs,
**0.5–15 kg MTOM**, span ≈ 0.8–3 m, cruise 10–30 m/s, chord Reynolds number
50 000–500 000, incompressible. Explicitly **not** transport category. A method
that is standard in airliner literature is judged here on whether it is valid at
*this* scale.

**Authority hierarchy** (from `CLAUDE.md`):

1. **Scholz / Sadraey** (`aircraft-design-scholz`) — lead, academic, citable.
2. **Anderson, *Fundamentals of Aerodynamics* 6e** (`aerodynamics-expert`) —
   physics ground truth, used where the mechanism decides the answer.
3. **RC practice** (`rc-aircraft-designer`: Lennon 1996 + RC-Network Wiki) —
   hobbyist-level, **lower authority**, valid for RC models, not for UAV.

Source labels are explicit throughout: **[Scholz/Sadraey]** academic ·
**[Anderson]** physics text · **[RC]** hobbyist practice · **[code]** verified in
this repository · **[derived]** arithmetic done here from a cited quantity.

> **Method note.** The three expert subagents dispatched for this briefing had not
> returned when the deadline for this document arrived. Every **[Scholz/Sadraey]**,
> **[Anderson]** and **[RC]** citation below was therefore read directly out of the
> corresponding skill's concept vault, and each carries its concept file, source
> file and section number so it can be re-checked. Nothing is quoted from memory.

---

## Premise corrections — read these first

Three premises in `questions.md` / the briefing request do not survive contact
with the code. They change what the maintainer is actually being asked.

| # | Stated premise | What the code does |
|---|---|---|
| 1 | "a PATCH can leave a flight profile self-inconsistent" | **False.** `flight_profile_service.update_profile` re-validates the merged payload through `RCFlightProfileCreate` (`app/services/flight_profile_service.py:121`), which runs `validate_turn_load_vs_bank`. Verified empirically: PATCHing `max_bank_deg` 60 → 45 with `target_turn_n = 2.0` is **rejected**. There is no hole to close. |
| 2 | "the `turn_60` preset stores `n = 1.0`" | **The generator and the stored data are both correct.** `operating_point_generator_service:497` computes `n_target = 1/cos(bank)`, and all **15** `turn_20`/`turn_40`/`turn_60` rows in `db/test.db` carry 1.06 / 1.31 / 2.00 — verified by direct query. The defect is one layer downstream in plotting: `flight_envelope_service._load_operating_point_markers` (`:589`, comment at `:604`) hardcodes `n = 1.0` for **every** V-n marker. Already ruled on and endorsed as **`Q-MS-6`** (`questions.md:3742`). ⚠ Additional nuance: `n_target` is not a column — it survives only as free text inside `description` (*"config=clean, target_n=2.00, V=12.74mps…"*). That is *why* the marker loader cannot read it, and it is an independent argument for `Q-MS-6`'s "persist it as a real field". |
| 3 | "a mission-preset change moves cruise speed, g-limit, CL_max, power-to-weight, static margin" | The preset moves `g_limit`, `target_static_margin`, `cl_max`, `power_to_weight`, **`prop_efficiency`** (`app/schemas/mission_objective.py:69-76`). **Cruise speed is not a preset estimate** — `target_cruise_mps` is a separate user-set field on the same PUT payload (`mission_objective.py:35`). |

---

## Q-MB-3 — Is lateral / vertical CG out of scope?

### Consensus recommendation

**Both fields are out of scope as *CG* — but for a sharper reason than "nobody
uses them": at 0.5–15 kg they are the wrong quantity.** Sadraey's own criterion
for the y-axis CG is symmetry (target = exactly 0, no free parameter to report),
and his criterion for the z-axis CG is **not a stability quantity at all** — it is
*"the position at which the aircraft has the lowest mass moment of inertia about
the x-axis"* (§11.3.3, ideal directional cg). Lennon reaches the same place from RC
practice: the spanwise/vertical mass concern is **roll inertia**, not CG offset.
Roll inertia is a *second* moment, `I_xx = Σ mᵢ(yᵢ² + zᵢ²)`; `cg_y`/`cg_z` are
*first* moments. They are not approximations of each other — a symmetric pair of
wing batteries gives `cg_y = 0` and a large `I_xx`. So the two published fields
are not a partial implementation of a lateral-balance feature; they are a
different, second-order quantity that happens to share a name.

Quantitatively the second-order verdict holds: for a representative 2 kg / 1.5 m
model, a realistic lateral offset (a 200 g pack 100 mm off-centre ⇒ `y_cg` = 10 mm)
costs **0.46° of aileron at cruise — 1.8 % of a ±25° authority budget** [derived].
Even a gross 30 mm offset costs 1.4° at cruise and 4.8° at approach speed.

**Therefore: do not carry `cg_y` / `cg_z` forward onto the component tree.** Note
that "delete the current fields" is no longer a live decision — **`Q-MB-1` already
retires `weight_items` entirely** in favour of the component tree, so
`aggregate_weight_items` and everything it publishes goes with it. The real
question this answer settles is what the *tree-based* CG surface should publish,
and the answer is: `cg_x` (ADR 0011's feedback signal) and, if anything on the
lateral/vertical side, **`I_xx`** — not `cg_y`/`cg_z`.

Three supporting facts:

- The solver never sees y/z: **every** trim path hardcodes the moment reference to
  `[design_cg_x, 0.0, 0.0]` (`operating_point_generator_service.py:1027, 1116,
  1582`; `add_turn_service.py:74, 131`) — including for OpenVSP imports, where
  `aeroplane.xyz_ref` *did* carry real y/z.
- There is no top-down target to compare against. ADR 0011's design loop runs
  `cg_x = x_np − SM·MAC`; for y the target is exactly 0 by symmetry, and for z
  there is no stability-derived target at all.
- Publishing a number no consumer reads is ADR 0021's decisive failure mode —
  *"a protection appears to exist that does not"* — and a lateral-balance badge is
  the strongest form of that trap, because "balanced" is the reading it gives when
  the input is simply absent.

> 🔴 **Blocking finding for `Q-MB-1` / `Q-MB-4`, discovered while checking this.**
> `Q-MB-4`'s derived answer states that the CG comparison should read the tree
> because *"the tree carries `pos_x/y/z`"*. That is true of the **schema** and
> false of the **system**. In `db/test.db`: **609 `component_tree` rows, and not
> one has a non-zero `pos_x`, `pos_y` or `pos_z`.** The reason is in the editor —
> `NodePropertyPanel.tsx:260-262` writes `pos_*` **only for `cad_shape` nodes**
> and passes the existing value through for every other type:
> `pos_x: isCadShape ? parseNum(form.pos_x) : node.pos_x ?? 0`. The live tree
> contains **12 `cots` nodes** (all with a `component_id`, i.e. the mass-bearing
> ones) and **597 `group` nodes** — and **zero `cad_shape` nodes**. So the node
> type that carries mass is exactly the node type whose position the UI will not
> write.
>
> Switching the CG source to the tree today would therefore yield
> `cg = (0, 0, 0)` for every aircraft — an asserted wrong answer replacing today's
> honest `null`. **`Q-MB-1`/`Q-MB-4` need a positioning path for `cots` nodes
> before the switch, and this applies to `cg_x` — the axis that actually matters
> — not just to y and z.**

**If lateral coverage is wanted later, the ticket is "roll inertia", not "lateral
CG"** — and it needs *exactly the same enabling work* as `cg_x` itself:
per-component positions on mass-bearing tree nodes. Sadraey's point-mass treatment
(`I = m·r²`, Eq. 11.27, plus the parallel-axis theorem Eq. 11.29) is precisely what
`(mass, pos_x, pos_y, pos_z)` supports, so once the `Q-MB-1` positioning path
exists, `I_xx = Σ mᵢ(yᵢ² + zᵢ²)` is a sum over rows the tree already has. That
makes this a cheap follow-on rather than a new subsystem — and it is the reason to
record the decision now rather than re-derive it later.

### Evidence

**Lateral CG — the target is zero, and Sadraey publishes no numeric tolerance.**
[Scholz/Sadraey] §11.3.3 (`sadraey-ideal-lateral-cg`, source
`16_Sadraey_AircraftDesign.md`): *"the ideal lateral cg location is **the position
at which the aircraft requires no aileron deflection to hold lateral trim***…
*"The cg is therefore preferred to lie exactly on the fuselage centerline"*…
*"The result holds for almost all conventional aircraft and is rarely violated on
purpose."* On how much offset is acceptable he is explicitly non-numeric:
*"the acceptable offset is therefore bounded in practice by the resulting trim
drag and by passenger-comfort considerations."* And on effort:
*"The lateral cg analysis is generally simpler than the longitudinal one because
most aircraft are designed symmetric from the start, and the lateral cg therefore
sits very close to the centerline by construction."*

**The roll moment and the aileron demand it creates** [derived]. Weight off the
plane of symmetry produces a rolling moment `L_roll = W·y_cg`, i.e.
`C_l = W·y_cg /(q·S·b)`. The aileron authority to cancel it comes from Sadraey
Eq. 12.23 [Scholz/Sadraey] (`sadraey-aileron-design-principles`, §12.4.2):

```
C_lδA = (2·C_Lαw·τ·C_r /(S·b)) · [ y²/2 + (2/3)((λ−1)/b)·y³ ]_{y_i}^{y_o}
```

with τ from Sadraey Fig. 12.12 and *"maximum deflection δ_Amax (typically ±25°)"*
(`sadraey-aileron-design-procedure`, step 10).

Evaluated for a representative model — m = 2 kg, b = 1.5 m, S = 0.30 m²
(AR 7.5), rectangular (λ = 1), `C_r` = 0.2 m, `C_Lαw` = 4.5 /rad, τ = 0.45
(≈ 25 % chord aileron), ailerons 35 % → 95 % semi-span — gives
**`C_lδA` = 0.395 /rad = 0.00689 /deg** [derived]:

| `y_cg` | % semi-span | δa at V = 15 m/s | % of ±25° | δa at V = 8 m/s | % of ±25° |
|---|---|---|---|---|---|
| 5 mm | 0.7 % | 0.23° | 0.9 % | 0.81° | 3.2 % |
| 10 mm | 1.3 % | 0.46° | 1.8 % | 1.61° | 6.5 % |
| 20 mm | 2.7 % | 0.92° | 3.7 % | 3.23° | 12.9 % |
| 30 mm | 4.0 % | 1.38° | 5.5 % | 4.84° | 19.4 % |
| 50 mm | 6.7 % | 2.30° | 9.2 % | 8.07° | 32.3 % |

Two things follow. **(i)** The demand scales as `1/V²`, so the worst case is
approach and the stall, never cruise. **(ii)** Realistic causes at this scale land
in the top two rows: a 200 g pack 100 mm off-centre on a 2 kg model gives
`y_cg` = 10 mm; an 80 g FPV camera 60 mm off-centre gives 2.4 mm [derived]. To
reach the bottom row you would need ~0.5 kg hung 200 mm out on a 2 kg aircraft.

**Vertical CG contributes nothing to the dihedral effect.** This is settled by
first principles, not by preference: **weight acts at the CG, so it exerts zero
moment about the CG.** A free-flying aircraft is not suspended from anything, so
"pendulum stability" cannot be a gravity term, and `z_cg` does not appear in
`C_l_β`. What *is* real is the **wing's vertical position relative to the
fuselage** — a geometry input, not a mass one — and the aircraft's actual `C_l_β`
is already computed and stored by the solver as `Clb`
(`aerobuildup_trim_service.py:31`, `copilot_tools.py:458`) [code], so the
quantity a designer would want is available without `cg_z`.
[Anderson] is silent here — *Fundamentals of Aerodynamics* 6e does not treat
lateral-directional stability derivatives, so the `aerodynamics-expert` skill is
genuinely out of scope for this sub-question, and that gap is reported rather
than papered over.

**Sadraey's z-axis criterion is inertia, and he says so.** [Scholz/Sadraey] §11.3.3
(`sadraey-ideal-directional-cg`): *"the **ideal directional cg location is the
position at which the aircraft has the lowest mass moment of inertia about the
x-axis**. Minimizing `I_xx` produces the best lateral (roll) control authority."*
And explicitly: *"Although the ideal directional cg is dominated by the inertia
argument, directional trim and stability also play a role."* The computation he
prescribes is §11.7 (`sadraey-aircraft-mass-moment-inertia`): `I = m·R²`
(Eq. 11.27), parallel-axis `I_O = I_C + m·d²` (Eq. 11.29), summed over components
— with **point mass** as an explicitly tabulated component model
(`I_xx = m·r₁²`). The weight-item rows are already exactly that.

**RC practice agrees, and independently arrives at inertia.** [RC] Lennon 1996
Ch. 11 (`lennon-lateral-roll-inertia`): *"The model's wing is a factor, as it
weighs close to 25 percent of the model's gross weight. For good lateral
maneuverability, keeping the wing panel's CG as close to the fuselage center line
helps."* And Ch. 11 (`lennon-mass-concentration-near-cg`): *"The greater the
distance of both PU and CU from the model's design CG, the greater those moments
of inertia will be, and the greater the resistance to the maneuver."* Both are
second-moment arguments. Neither source contains a lateral-CG-offset tolerance.

**The one symptom a builder would blame on lateral balance is attributed
elsewhere.** [RC] RC-Network Wiki (`rcn-stroemungsabriss`): wing drop at the stall
is *"flow separation rarely occurs simultaneously on both wings… asymmetric
forces"*, mitigated by **washout**, not by lateral ballast.

**Where `z_cg` genuinely is the governing input — and why it is unreachable here.**
Two real criteria exist, both in Sadraey's landing-gear chapter [Scholz/Sadraey]:
tipback `α_tb = tan⁻¹(x_mg / h_cg)` with `α_tb ≥ α_TO + 5°`, typical 15–20°
(§9.6.1, `sadraey-tipback-tipforward-angle`), and overturn `φ_ot ≥ 25°` with
wheel track `T > 2·F_C·H_cg/(m·g)` (§9.5.3, `sadraey-wheel-track`). `h_cg` / `H_cg` is CG
height — so yes, `z_cg` governs. **But the project models no landing gear at
all**: there is no gear geometry, no wheel track, no gear height anywhere in
`app/models/` [code]. `runway_type` / `landing_surface` are friction selectors for
field length, nothing more. A third real consumer is the thrust-line offset in
Sadraey's longitudinal trim system, Eq. 12.86 — the forcing term is
`−T·z_T/(q·S·c̄)`, already cited and vetted in this project
(`expert-consensus-aero.md:547`). That one is also unreachable: the ASB airplane
carries **no thrust vector** — thrust exists only as the scalar `t_static_N`
consumed by `field_length_service` for the takeoff run [code].

### Disagreements

**One, and it is terminological rather than substantive.** [RC] Lennon 1996
Ch. 25 (`lennon-wing-position-dihedral`) explains his dihedral table —

| Wing position | Dihedral with ailerons | without |
|---|---|---|
| High | 2° | 5° |
| Mid | 3° | 6° |
| Low | 4° | 7° (implied) |

— with *"High wings get pendulum stability 'for free' from the CG hanging below
the wing."* Sadraey uses the same phrase in passing (*"high-wing aircraft tend to
have stronger pendulum stability"*, `sadraey-ideal-directional-cg`). **Both are
using a folk label for a real effect with the wrong cause.** The 2° of dihedral
that separates a high wing from a low wing is real and well measured by RC
practice; what it cannot be is a gravity term, because weight acts *at* the CG and
therefore exerts no moment about it. The governing input is wing height above the
fuselage centreline — a *geometry* number the solver already has — not `cg_z`, a
*mass* number. Scholz outranks RC here, and on the substance they do not actually
conflict: Sadraey's operative z-axis criterion is `I_xx`, and he never puts `z_cg`
in a stability derivative.
>
> ⚠ **Sourcing caveat.** The zero-moment-about-the-CG argument is
> [derived from first principles] and is solid. The *positive* attribution of the
> high-wing rolling moment to wing–fuselage crossflow interference is the standard
> flight-dynamics explanation, but **I could not source it** in the three vaults
> available: Anderson 6e does not treat lateral-directional derivatives, and
> Sadraey's §11.3.3 entry does not give the mechanism. Treat the mechanism as
> unsourced here; the conclusion that `cg_z ∉ C_l_β` does not depend on it.

No disagreement on lateral CG: Sadraey (target = centreline, tolerance set by trim
drag) and Lennon (keep panel CG near the centreline, for inertia) point the same
way.

### Open premises

- **Aileron geometry.** `C_lδA` = 0.00689 /deg is [derived] from an *assumed*
  representative planform and τ = 0.45. Real aircraft in this tool carry their own
  aileron span/chord, so the per-aircraft value will differ — plausibly by ±40 %.
  The conclusion (realistic offsets cost single-digit percent of authority)
  survives that spread; the specific degree values do not.
- **Why `cad_shape` positions are editable but `cots` positions are not.** I
  verified the behaviour (`NodePropertyPanel.tsx:260-262`) and the consequence
  (0 of 609 rows positioned) but not the intent. It may be deliberate — a COTS part
  inside a printed housing arguably inherits the housing's position — in which case
  the fix is inheritance through the tree rather than a per-node field. That
  changes the shape of the `Q-MB-1` work but not this ruling.
- **Whether `pos_*` is mm.** `component_tree.pos_x` is documented as mm
  (`app/schemas/component_tree.py:40`) while the CG surface is metres; `Q-MB-1` §4
  is cited as covering the conversion. I did not verify that the conversion is
  implemented anywhere, only that it is required.
- **3D-printed-wing relevance.** The maintainer 3D-prints wings; whether print
  orientation or infill produces a systematic left/right mass asymmetry is not
  something I can determine, and I have not assumed either way.
- **`I_xx` acceptance criteria.** Sadraey prescribes *minimising* `I_xx`, not
  meeting a threshold, and neither he nor Lennon publishes an RC-scale target
  value. A roll-inertia feature would therefore report a number and a trend, not a
  pass/fail — unless it is tied to the roll-rate requirement (Sadraey Table 12.5,
  Class I: 60° of bank in 1.3 s), which *is* a threshold and *is* computable.

### What to ask the maintainer

> `cg_y` and `cg_z` are computed and published but read by nothing. Since `Q-MB-1`
> retires `weight_items` anyway, the live question is not "delete them" — it is
> **what the tree-based CG should publish once the switch happens.**
>
> The engineering finding: at 0.5–15 kg lateral CG is second-order *and* the wrong
> quantity. A realistic offset (a 200 g pack 100 mm off-centre) costs under 2 % of
> your aileron authority, and what both Sadraey (§11.3.3) and Lennon (Ch. 11)
> actually care about in spanwise/vertical mass is **roll inertia**
> `I_xx = Σ m(y²+z²)` — a second moment, computable from the same
> `(mass, pos_x, pos_y, pos_z)` rows.
>
> - **(A) Publish `cg_x` only.** y and z do not come back on the tree surface.
> - **(B) `cg_x` only, plus a ticket for `I_xx`** as a manoeuvrability metric,
>   ridden along with the `Q-MB-1` positioning work since it needs the same data.
> - **(C) Publish all three and add a lateral-balance `DesignWarning`** above a
>   derived threshold of ≈ 2 % of semi-span (≈ 15 mm on a 1.5 m model — where
>   aileron trim reaches ~10 % of authority at approach speed).
> - **(D) Feed y/z into the solver** — `xyz_ref = [cg_x, cg_y, cg_z]` instead of
>   `[cg_x, 0, 0]`, letting the existing roll residual solve real aileron trim.
>   Most correct, but it re-references every stored moment coefficient.
>
> **Recommendation: (B).** (D) answers a question nobody is asking at this scale.
>
> **Separately, and this one blocks `Q-MB-1`/`Q-MB-4` rather than this question:**
> the tree's positions are not merely empty, they are **unwritable for the nodes
> that carry mass**. All 609 tree rows in your DB have `pos = (0,0,0)`, and the
> editor writes `pos_*` only for `cad_shape` nodes — of which you have none; your
> 12 mass-bearing nodes are all `cots`. Switching CG to the tree before fixing that
> would replace today's honest `null` with an asserted `(0,0,0)`. **Is the
> `cad_shape`-only restriction deliberate — i.e. should a COTS part inherit its
> parent's position rather than carry its own?** That answer decides whether the
> `Q-MB-1` work is a new field or an inheritance rule.

---

## Q-MS-13 (bank ↔ `target_turn_n` item) — is the consistency rule right?

### Consensus recommendation

**Do not tighten the validator, and do not "fix" the PATCH path — the hole does
not exist.** `update_profile` already re-validates through `RCFlightProfileCreate`
(`flight_profile_service.py:121`), so the rule is enforced on create *and* on
patch; I confirmed this by constructing the merged payload directly. Separately,
the rule is **not** the equality `n = 1/cos φ` and should not become one:
`max_bank_deg` is a *ceiling* (`Constraints`, "Maximum allowed bank angle"), not a
commanded bank, so the correct relation between the two fields is the inequality
already coded — `target_turn_n ≤ 1/cos(max_bank_deg)`. `n = 1/cos φ` holds
exactly for the *level coordinated* turn actually being commanded, and that is
computed correctly where it matters, in `turn_kinematics` (`:32`).

**The real defect in this area is a check that is missing, not one that is too
loose: nothing compares `target_turn_n` against `g_limit`.** `target_turn_n`
accepts up to 4.0 and `MAX_BANK_DEG = 85` admits `n` up to 11.5, while the
`trainer` preset seeds `g_limit = 3.0`. A profile can therefore demand a sustained
load factor above the airframe's own structural limit, and no layer objects. That
is the check worth adding.

On the `turn_60` marker: **`n = 2.0` is confirmed**, the generator and the stored
rows are both already correct, and the defect is confined to
`flight_envelope_service:589-604`. Two follow-on engineering questions are
answered below.

### The V-n marker: is a wrong marker worse than none?

**Yes — decisively, and this one is worse than none in the specific way that
matters most.** A marker at `n = 1.0` is not a *missing* datum, it is an
*asserted* one: it states "this manoeuvre loads the airframe to 1 g". For
`turn_60` that understates the load by exactly 2×, and it does so **one-sidedly,
always in the safe direction** — 1.0 is the floor of the diagram, so no turn
marker can ever be placed conservatively. A noisy indicator can be lived with; an
indicator that is systematically biased toward "safe" is a hazard, and it is
precisely ADR 0021's decisive failure mode — *"a protection appears to exist that
does not."* The V-n diagram has exactly one job, proximity to the g-limit, and a
marker pinned to the minimum possible load factor inverts it.

The stake is concrete at this scale. Sadraey's `n_max` for the remote-controlled
model class is **1.5–2** (§10.4.1) [Scholz/Sadraey], so a correctly placed
`turn_60` marker at `n = 2.0` lands **on or above the class ceiling** — the single
most actionable fact the diagram can show an RC designer, and exactly the one
currently suppressed.

**But the answer is fix, not remove.** Removing the markers would discard a
computation that is already correct: `n_target` is computed at `:497`, is already
used to set the trim's CL target (`CL_target = m·g·n/(q·S)`, `:797/:886/:894`),
and is already written into `description`. Both halves of the code comment
justifying `n = 1.0` are false — turn points are not level-flight conditions, and
the load factor *is* derivable. `Q-MS-6`'s ruling (promote `n_target` and
`cl_trimmed` to real fields, fall back to `n_target`, and flag the marker
**unverified** rather than silently placing it at 1.0) is the right shape and
needs no revision.

### The stall-in-turn reasoning — confirmed, and it is the common case at RC scale

**The reasoning is correct, and I reproduced it on live data rather than only on
paper.** At the boundary `L = n·W = ½ρV²S·C_Lmax`, so
`V_stall(n) = V_S·√n` [derived]; at `n = 2`, √2 = **1.4142**. The generator sets
turn velocity to `max(cruise, 1.3·V_S)` (`:494`), and **1.3 is a level-flight
(1 g) margin, not a manoeuvre margin.** Whenever `cruise ≤ 1.3·V_S` the floor
binds and the `turn_60` point sits at `1.3·V_S`, i.e. `1.3/1.4142 = 0.919` — **8 %
*below* the stall speed in the turn.** That is a stalled point, not a marginal one.

Live confirmation from `db/test.db`:

| aircraft | op | V | `v_s1` | `1.3·V_S` | `1.414·V_S` | verdict | status |
|---|---|---|---|---|---|---|---|
| 9 | `turn_60` | 12.74 | 9.80 | 12.74 | 13.86 | **stalled** | DIRTY |
| 8 | `turn_60` | 12.30 | 8.60 | 11.18 | 12.16 | ok (cruise bound) | LIMIT_REACHED |
| 45 | `turn_60` | 12.70 | 8.60 | 11.18 | 12.16 | ok (cruise bound) | TRIMMED |
| 34 | `turn_60` | 34.15 | 21.30 | 27.69 | 30.12 | ok (cruise bound) | NOT_TRIMMED |

Aircraft 9 is the floor-bound case, `V = 12.74 = 1.3 × 9.80` exactly, and **the
existing detector fires correctly** with the right numbers:
`STALL_IN_TURN: required CL at 60 deg bank (n=2.00) exceeds CL_max — V=12.7 <
V_stall_turn=13.9 m/s`. So the physics is already implemented and already
correct; only its *visibility* is broken.

**This is more likely at RC/UAV scale than at transport scale, and that is a
scale-validity point worth stating explicitly.** The floor binds only when
`cruise/V_S ≤ 1.3`. A transport aircraft cruises at 2–3 × `V_S`, so it never
binds. An RC trainer or small UAV routinely cruises at 1.3–1.5 × `V_S` — the
aircraft above sit at 1.30, 1.43, 1.48 and 1.60 [derived] — so at this scale the
condition is **common, not exceptional**. A rule inherited from transport practice
("1.3 V_S is a safe low-speed target") does not transfer, which is exactly the
kind of transplant this scope framing exists to catch.

**Recommendation: let the marker land outside the boundary and promote
`STALL_IN_TURN` to a first-class status — do not silently raise the turn
velocity.** Three reasons:

1. **Raising the velocity changes the question.** The user asked "how does my
   aircraft fly a 60° turn *at its cruise speed*?" Substituting a faster
   condition answers a different question, and under **ADR 0020** that is an
   undeclared substitution — it would require a `DesignWarning` anyway, at which
   point you have the warning *and* have lost the finding.
2. **"At your cruise speed this aircraft cannot sustain a 60° turn" is a design
   answer, not a solver inconvenience** — and for an RC/UAV designer it is one of
   the more useful things the turn sweep can produce. Raising the velocity deletes
   it.
3. **The project already has the right precedent.** `expert-consensus-aero`
   adopted `CONTROL_AUTHORITY_LIMIT` for exactly this shape: *"a solution exists
   but needs |δE| > 25° … carry the required δE in the payload so the user sees
   how far short they are."* The symmetric treatment here is a `STALL_IN_TURN`
   status carrying `V_stall_turn`, so the user reads "needs 13.9 m/s, has 12.7".
   `Q-MS-6` already requires the warning to become a matchable bare token rather
   than a formatted sentence; that is the whole of the work.

**If the maintainer nonetheless prefers raising the velocity, `1.05·V_S·√n` (the
constant floated in `Q-MS-6`) is too thin and should not be adopted as written.**
Five per cent above the stall boundary leaves no room for gust, trim residual or
`C_Lmax` uncertainty — and at Re 50 k–500 k `C_Lmax` itself is the least certain
number in the model. The defensible construction reuses a parameter that already
exists and is already user-facing rather than inventing a constant (ADR 0022/0023):
`V_turn = max(cruise, min_speed_margin_vs_clean · V_S · √n_target)`, which at the
default 1.20 gives `1.697·V_S` at 60° bank. A **second** point at that speed
alongside the cruise-speed one is better still — it answers "what would it take?"
without overwriting "what happens now?"

⚠ **Unverified observation, not a finding.** `db/test.db` holds **19** turn rows,
not 15: a fourth family `turn_n2` (4 rows, `target_n = 2.00`, `p = q = r = 0`).
One of them — aircraft 18, `V = 22.75`, `v_s1 = 19.4`, so needing 27.44 — is
**`TRIMMED` while inside the stall boundary and carries no warning**, because
`_apply_turn_feasibility` keys off `bank_deg` and returns early when it is absent
(`:165`). That suggests the stall check should key off `n_target` rather than
`bank_deg`. I could not establish where `turn_n2` is generated (`add_turn_service`
always sets `bank_deg` and would give non-zero `q`/`r`), and that aircraft has
`s_ref = 17.55 m²` — far outside the 0.5–15 kg scope, so plausibly stale fixture
data. **Worth a look; not something to act on from this document.**

### Evidence

**The relation.** For a steady, level, coordinated turn, vertical equilibrium is
`L·cos φ = W`, so by the definition `n ≡ L/W`, **`n = 1/cos φ` exactly** — an
identity, not a correlation. Implemented correctly at
`app/services/turn_kinematics.py:32` [code].

| φ | `n` | `V_stall` × | induced drag × (∝ n²) |
|---|---|---|---|
| 20° | 1.064 | 1.032 | 1.13 |
| 40° | 1.305 | 1.142 | 1.70 |
| 45° | 1.414 | 1.189 | 2.00 |
| **60°** | **2.000** | **1.414** | **4.00** |
| 70° | 2.924 | 1.710 | 8.55 |
| 85° | 11.474 | 3.387 | 131.65 |

[derived]. The `V_stall` column is `√n` because `V_stall(n) = V_S·√n`; the drag
column follows from `C_Di = C_L²/(π e AR)` with `C_L ∝ n` at fixed speed.

**What a 60° level turn demands of a 0.5–15 kg aircraft.** Stall speed rises by
**41 %** and induced drag **quadruples** [derived]. Against that, Sadraey's
maximum operational load factor for the *remote-controlled model* class is
**`n_max` = 1.5–2** (§10.4.1, `sadraey-ultimate-load-factor-aircraft`, with
`n_ult = 1.5·n_max`, Eq. 10.4) [Scholz/Sadraey]. So a 60° level turn sits **at or
above the load factor Sadraey assigns to the entire class** — which is precisely
the finding the V-n diagram exists to surface, and the reason `Q-MS-6` matters.

**Where `n = 1/cos φ` legitimately does not hold** — the reason a strict equality
between the two *stored fields* would be wrong even setting aside their
target-vs-ceiling roles:

- **Climbing / descending turn.** With flight-path angle γ, vertical equilibrium
  becomes `L·cos φ = W·cos γ`, so `n = cos γ / cos φ` [derived]. At RC climb
  angles (γ ≤ 20°) the correction is ≤ 6 %, but it is not zero.
- **Slipping / skidding turn.** Uncoordinated flight puts a side-force component
  in the balance; `n` is then set by the full three-axis equilibrium and is not a
  function of φ alone.
- **Knife-edge (φ = 90°).** `1/cos φ` diverges. The aircraft is held up by fuselage
  side force and thrust inclination, not by wing lift — the relation does not
  merely need a correction, it does not apply. `MAX_BANK_DEG = 85` already keeps
  the schema out of this region.

**The three different load factors in the system** [code] — worth naming, because
conflating them is the likely origin of the question:

| Field | Meaning | Consumers |
|---|---|---|
| `Goals.target_turn_n` (1.0–4.0) | aero/handling **goal** for generated turn points | `operating_point_generator_service` |
| `MissionObjective.target_maneuver_n` | spider-chart axis **score input** | `mission_kpi_service:381` |
| `g_limit` design assumption | **structural** limit load factor | V-n envelope (`flight_envelope_service:683`), **spar sizing** (`spar_plan_service:328`) |

Nothing cross-checks the first against the third.

**RC practice supports the separation of goal from structural limit.** [RC] Lennon
Ch. 11 and the RC-Network material treat manoeuvre demand and airframe strength as
distinct design inputs; the airframe g-limit is a build property, the turn a pilot
flies is an operating choice. That is an argument for keeping two fields — and for
adding the inequality between them, not for merging them.

### Disagreements

**One, on the numbers rather than the mechanism, and it goes against Scholz.**
Sadraey's `n_max` = 1.5–2 for "remote-controlled model" is almost certainly aimed
at surveillance/target-drone practice; it is flatly below what RC aerobatic and 3D
models are built and flown to, and below seven of this project's own nine mission
presets (`g_limit` 3.0–10.0, `mission_preset_seed.py`). `CLAUDE.md` gives Scholz
the ruling, and on the *method* — `n_ult = 1.5·n_max`, and n as the driver of spar
sizing — Scholz is unambiguously right. On the *value* for an acro model, his
single table row is too coarse to be binding. The honest resolution under ADR 0023
is that `g_limit` is a **user design choice with provenance**, with Sadraey's
1.5–2 recorded as the reference floor rather than as the answer. Exactly one
preset already does this properly: `motor_glider`'s description states
*"g_limit=5.3 cites CS-22.337 utility-category ultimate factor (1.5 × +3.5 limit)
for sailplanes and powered sailplanes"* (`mission_preset_seed.py:243-245`). The
other eight `g_limit` values — including `wing_racer` at **10.0**, five times
Sadraey's class ceiling — carry no source at all.

### Open premises

- I have not established whether `MAX_BANK_DEG = 85` is deliberate (it admits
  `n` = 11.5) or an artefact of "keep it below 90 so the tangent is finite".
- I did not evaluate the other three items bundled into `Q-MS-13` (`is_default`
  on `loading_scenarios`, unvalidated `component_uuid`, `ga_runway` outside the
  `AircraftMode` literal, dead `ComputeEnvelopeRequest.force_recompute`) — they
  were out of the brief and are not engineering questions.

### What to ask the maintainer

> The bank ↔ load-factor rule is fine as written, and the PATCH hole reported in
> `questions.md` does not exist — I verified the patch path re-validates. The rule
> is an inequality (`n ≤ 1/cos(max_bank)`) rather than an equality, which is
> correct, because `max_bank_deg` is a ceiling and not a commanded bank. What is
> genuinely missing is that nothing checks the turn goal against the airframe: a
> profile can demand `target_turn_n = 4.0` on an aircraft whose `g_limit` is 3.0.
>
> - **(A) Add `target_turn_n ≤ g_limit` as a hard validation error.** Simple, but
>   it couples a flight profile to an aircraft's assumptions, and profiles are
>   currently shareable across aircraft.
> - **(B) Emit it as a `DesignWarning` at assignment/generation time** instead of a
>   422 — "this profile asks for 4 g; this airframe is designed to 3 g" — which
>   keeps profiles aircraft-independent.
> - **(C) Leave it.** The V-n diagram will show the turn marker outside the
>   envelope once `Q-MS-6` lands, so the user finds out anyway.
>
> **Recommendation: (B).** It is the only option that respects the profile/aircraft
> separation, and under ADR 0020 an exceeded structural limit is exactly a
> `severity: error` finding rather than a silent one. (C) is defensible only if you
> are confident `Q-MS-6` ships first.

---

## Q-MS-10b — Should changing the mission propagate automatically?

### Consensus recommendation

**Physically, only one of the five invalidates anything: `target_static_margin`.
The other four re-target.** A stored operating point is a converged trim for a
fixed geometry at a stored velocity, altitude and moment reference; the only
preset estimate that reaches any of those is `target_static_margin`, through
`cg_x = x_np − SM·MAC` → `xyz_ref`. `g_limit`, `cl_max`, `power_to_weight` and
`prop_efficiency` are boundary and performance quantities — change them and the
stored α/δe/C_L/C_D still describe a real flight state of that aircraft; what
changes is which state you *wanted*.

**And this is already the codebase's own contract**, which is the strongest
argument available that no new invalidation policy is needed:
`_OP_AFFECTING_PARAMS = {"mass", "cg_x"}` and
`_RECOMPUTE_TRIGGERING_PARAMS = {"target_static_margin", "mass"}`
(`app/services/invalidation_service.py:16-24`). Routing
`_apply_preset_estimates` through `update_assumption` instead of writing
`estimate_value` onto the ORM rows therefore produces **exactly the right physics
for free** — SM dirties operating points, the rest trigger a context recompute
only. That is the defensible middle the question asks for, and it requires no
per-parameter policy table.

**One genuine invalidation lies outside the operating points and is the strongest
argument for propagating at all: `g_limit` sizes spars.** `wing_xsec_spares` rows
are persisted by `POST /aeroplanes/{id}/spar-plan/insert` and carry **no record of
the `g_limit` they were sized under** [code]. Switching mission `trainer` → `acro_3d`
today silently moves `g_limit` 3.0 → 8.0 and leaves physically built spars
under-sized, with no event, no warning and no marker.

**Blocking finding — fix before wiring any fan-out.** `power_to_weight` is declared
**W/kg** (`app/schemas/design_assumption.py:58`) with a seeded default of **220.0**
and an in-code RC chart of 160–440 W/kg, and is consumed as shaft power
`P = (P/W)·m·η` (`assumption_compute_service._max_level_speed:1902`). The presets
seed it as trainer **0.5** · sport **0.7** · sailplane **0.0** · wing_racer **1.0** ·
acro_3d **1.4** · stol_bush **0.8** · slope_soarer **0.0** · motor_glider **100.0** ·
flying_wing **100.0**. Two of those are legitimately zero (the unpowered gliders —
`0` is the documented "no powertrain, V_max = structural V_NE" sentinel) and two
are the right order of magnitude, but **five are thrust-to-weight-shaped numbers,
~150–400× too small in W/kg**. The seed
file contradicts itself on this: `motor_glider`'s own description says
*"Power-to-weight 80–150 W/kg covers self-launch climb"* and seeds `100.0`
correctly, while `trainer` — which needs far more power than a motor glider —
seeds `0.5` (`mission_preset_seed.py:238` vs `:39`). Because `power_to_weight` has no
CALCULATED producer, `active_source` stays `ESTIMATE`, so **the preset write is
already effective and V_max is already wrong today** for any aircraft whose
mission has been set. Adding propagation without fixing this propagates the error
further.

**On the UX question — recommend explicit apply, not silent auto-propagation.**
Not because the cascade is expensive (`Q-PC-4`'s coalescing plus the 2 s debounce
already collapse five changes into one recompute and one retrim) and not because
it is irreversible (ADR 0006 row-copy versioning gives real undo), but because a
mission change overwrites five numbers the user may have hand-tuned, and the
product already has this idiom in two places: the tail-sizing pencil action
("fill in recommended S_H / S_V + single recompute (**no cascade**)",
`TailVolumeCard.tsx:1-11`) and spar insert (`dry_run` default true, auto-snapshot
before a destructive commit, `spar_insert_service.py:485-500`).

### Evidence

**What each of the five actually feeds** [code]:

| Estimate | Trim input? | Reaches | Verdict on stored results |
|---|---|---|---|
| `target_static_margin` | **yes**, via `cg_x` → `xyz_ref` | `assumption_compute_service:108`, then `_RECOMPUTE_TRIGGERING_PARAMS` → `AssumptionChanged(cg_x)` → `mark_ops_dirty` | **INVALIDATES.** The stored δe balanced a different moment arm. |
| `g_limit` | no | V-n envelope (`flight_envelope_service:683`), spar sizing (`spar_plan_service:328`) | **Re-targets** the envelope; **invalidates built spars** (persisted, no provenance). |
| `cl_max` | no (a boundary, not a trim unknown) | `v_s1/v_s_to/v_s0`, V-n low-speed edge, forward CG limit (`elevator_authority_service:499`) | **Re-targets.** The trim is still valid; the point's *label* ("1.2·V_s") stops being true. Also largely **inert**: `cl_max` has a CALCULATED producer with `auto_switch_source=True` (`assumption_compute_service:183-190`), so once geometry has been recomputed the preset's estimate is not the effective value. |
| `power_to_weight` | no | V_max (`_max_level_speed:1902`), endurance | **Re-targets.** |
| `prop_efficiency` | no | V_max, endurance (`endurance_service:522`) | **Re-targets.** |

**Why `C_L` survives a speed change but `C_D` does not, at model scale.** In
incompressible flow a coefficient at fixed geometry and fixed α is speed-invariant
to first order, so a stored `C_L` does not die when the target cruise speed moves.
`C_D` is different at Re 50 k–500 k: [Anderson] gives turbulent
`C_f = 0.074/Re^{1/5}` and laminar `C_f ∝ Re^{-1/2}`
(`flat-plate-skin-friction`, `skin-friction-drag-incompressible`). For a 2× speed
change that is **−13 % turbulent / −29 % laminar** on the friction contribution
[derived] — and an RC wing at Re ≈ 200 k (V = 15 m/s, MAC 0.2 m) is substantially
laminar. So a stored `C_D` is only honest **at the velocity the point stores** —
which it does store (`OperatingPointModel.velocity`). This is what makes "cruise
speed moved" a *re-labelling* event rather than an invalidation: the old point is
still a true description of the aircraft at 15 m/s; it has merely stopped being
"the cruise point".

**Static margin is a target compared against a geometric property, not a solver
input** — but in *this* codebase it becomes one, because ADR 0011 makes the design
CG a function of it: `cg_x = x_np − target_static_margin·MAC`. That is why it is
the single member of the five that invalidates, and why `_RECOMPUTE_TRIGGERING_PARAMS`
already contains it. [Scholz/Sadraey] supports the direction of the loop: the
longitudinal CG is chosen from the stability requirement (§11.3.3,
`sadraey-ideal-longitudinal-cg`), not read off a component sum.

**The write path is wrong regardless of the UX answer** — already derived under
`Q-MS-10`. `_apply_preset_estimates` (`mission_objective_service.py:100`) sets
`estimate_value` directly; `update_assumption` is what publishes
`AssumptionChanged`, and it correctly fires **only when
`active_source == "ESTIMATE"`** (`design_assumptions_service.py:178-190`) — i.e.
only when the write actually changed the effective value. Routing through it also
fixes the `cl_max` inertness quietly and correctly.

**RC practice on whether the five move together.** [RC] The preset values
themselves reflect real class differences — trainer SM 0.15 / acro 0.0, against
Lennon Ch. 6 (`lennon-cg-location-and-static-margin`): sport CG at 25 % MAC with
power-on NP at 35 % MAC, i.e. *"a healthy 10 percent"* margin, *"the minimum
suggested margin is 5 percent"*; and Lennon Ch. 23
(`lennon-tailless-cg-static-margin`): *"SM = 5 % to 10 % of wing MAC"* for
tailless. Two preset values sit outside that: `trainer` at 0.15 is above Lennon's
sport band (defensible — a trainer *should* be more stable) and `acro_3d` at
**0.0** is neutral stability, which is a deliberate 3D choice but is below any
band either authority publishes. But hobbyist practice does **not** treat mission as
an atomic switch: a builder decides "this is now a sport model" and then re-picks
each number, often keeping the airfoil and CL_max they already committed to in
foam or filament. That is an argument for propose-and-adopt over silent
overwrite. It is hobbyist-level evidence about workflow, not about physics, and
it is not in conflict with anything Scholz says.

### Disagreements

**None on the physics.** Scholz/Sadraey, the code's own invalidation contract, and
RC practice all place `target_static_margin` (via CG) inside the trim problem and
the other four outside it.

**A tension on scope, worth naming.** The `Q-MS-10` narrowing note cites **ADR 0007**
(propose/adopt) as this system's idiom for wide-blast-radius changes. ADR 0007 is
scoped to the *copilot*, not to human UI edits, so it is an analogy rather than a
binding precedent. The genuinely binding precedents are narrower and closer:
`TailVolumeCard`'s "single recompute, no cascade" and spar-insert's
`dry_run` + auto-snapshot.

### Open premises

- **Whether the maintainer regards `power_to_weight` = 0.5–1.4 as a bug or as an
  intended second meaning.** I am confident it is a unit error (the declared unit,
  the 220.0 default, the in-code W/kg chart and the consumption formula all agree),
  but I have not found a ticket, and `motor_glider` / `flying_wing` at 100.0
  suggest someone already noticed a discrepancy and half-corrected it.
- **Whether `wing_xsec_spares` rows are always plan-derived.** They can also be
  authored directly, in which case "sized under a `g_limit`" is not universally
  meaningful and a provenance column would sometimes be null.
- **Whether `Q-CP-5` (persist the spar plan) is still open.** If the plan itself
  becomes persisted, the g_limit-staleness problem changes shape.
- `mission_type` has no FK to `mission_presets.id` and an unknown value silently
  no-ops (`mission_objective_service.py:88-89`) — already derived under `Q-MS-10`
  as a P-WARN-0 violation; I did not re-litigate it.

### What to ask the maintainer

> A mission change moves five design assumptions. Engineering answer: only
> **`target_static_margin`** actually invalidates a stored trim — it moves the CG,
> which moves the moment reference the solver balanced against. The other four
> (`g_limit`, `cl_max`, `power_to_weight`, `prop_efficiency`) move *targets*; the
> old trim is still a true description of the aircraft, it just stops being the
> state you wanted. Your existing `_OP_AFFECTING_PARAMS` / `_RECOMPUTE_TRIGGERING_PARAMS`
> sets already encode exactly this, so simply routing the preset write through
> `update_assumption` gives the right behaviour with no new policy.
>
> Two things I found that change the shape of the decision: **(1)** `power_to_weight`
> is in W/kg (default 220), but five of the nine presets seed it as 0.5–1.4 —
> roughly 150–400× too small; your own `motor_glider` description says
> "80–150 W/kg" and seeds 100 correctly, while `trainer` seeds 0.5. That value is
> *already live* (V_max is wrong today, without any fan-out).
> **(2)** `g_limit` sizes spars, and built spars record no g-limit, so
> trainer → acro silently leaves them under-sized.
>
> - **(A) Auto-propagate on mission change** — route through `update_assumption`,
>   let the existing invalidation contract decide what dirties. Consistent, no new
>   concepts; overwrites hand-tuned values without asking.
> - **(B) Explicit "Apply mission preset" step with a diff preview** — show the five
>   old → new values, let the user deselect any, then propagate through the same
>   path. Matches the tail-sizing pencil action and spar-insert `dry_run`.
> - **(C) Auto-propagate, but auto-snapshot first** (`aeroplane_version_service.snapshot`,
>   as spar insert already does) so the whole change is one-click revertible.
> - **(D) Keep the preset advisory only** — it suggests numbers, the user types
>   them. Least machinery, most re-typing.
>
> **Recommendation: (B), and fix the `power_to_weight` units first** — propagating
> before that fix pushes a 150–400×-wrong number into V_max for every aircraft. (C) is
> a good fallback if the diff UI is too much work; (A) is the one to avoid, because
> it is the option where the unit bug does the most damage.
>
> Separately, and regardless of which you pick: **should a `g_limit` change flag
> previously built spars as sized under an older limit?** That is the one place in
> this question with a physical safety consequence rather than a UX one.

---

## Summary table

| Question | Ruling | Confidence |
|---|---|---|
| **Q-MB-3** | `cg_y`/`cg_z` are out of scope **as CG** — second-order at 0.5–15 kg (a realistic 10 mm offset costs 0.46° of aileron, 1.8 % of authority) *and* the wrong quantity: both Sadraey §11.3.3 and Lennon Ch. 11 care about **roll inertia** `I_xx`, a second moment. `Q-MB-1` already retires `weight_items`, so the live decision is what the *tree* publishes: `cg_x` only, plus an `I_xx` ticket riding along with the positioning work. `z_cg` genuinely governs Sadraey's tipback (§9.6.1) and overturn (§9.5.3) criteria and the `T·z_T` trim term (Eq. 12.86) — all three unreachable, since the project models neither landing gear nor a thrust vector. 🔴 **Blocks `Q-MB-1`/`Q-MB-4`: 0 of 609 tree rows are positioned, and `pos_*` is unwritable for `cots` — the only mass-bearing node type.** | **high** on the ranking and the mechanism; **medium** on the specific aileron angles (assumed planform) |
| **Q-MS-13** (bank ↔ n) | The PATCH hole **does not exist** — `update_profile` re-validates through `RCFlightProfileCreate`; verified empirically. The rule is correctly an inequality against a *ceiling*, not an equality; do not tighten it (climbing turns give `n = cos γ/cos φ`; knife-edge has no relation at all). `n = 2.0` at 60° confirmed, and the generator + all 15 stored rows are already correct; the defect is the V-n marker loader alone (`Q-MS-6`). **Real gap: nothing checks `target_turn_n` against `g_limit`.** | **high** |
| **Q-MS-13 · V-n marker** | A marker pinned at `n = 1.0` is **worse than none** — it is a one-sided assertion that always reads "safe", and it suppresses the diagram's only job. Fix, don't remove: `n_target` is already computed, already drives the trim's CL target, and already sits in `description`. | **high** |
| **Q-MS-13 · stall-in-turn** | Reasoning **confirmed on live data**: `V_stall(n) = V_S·√n`, and `1.3/1.414 = 0.919` puts a floor-bound `turn_60` **8 % below** stall. Aircraft 9 reproduces it exactly and `STALL_IN_TURN` already fires correctly. **More common at RC scale than transport scale** — the floor binds only when `cruise ≤ 1.3·V_S`, which RC/UAV aircraft routinely are. **Recommend: let the marker land outside and make `STALL_IN_TURN` a first-class status** (same shape as `CONTROL_AUTHORITY_LIMIT`); raising the velocity is an undeclared substitution under ADR 0020. If raised anyway, `1.05·V_S·√n` is too thin — use `min_speed_margin_vs_clean·V_S·√n`. | **high** on the physics; the fix choice is a **preference** |
| **Q-MS-10b** | Only `target_static_margin` invalidates a stored trim (via `cg_x` → `xyz_ref`); the other four re-target. The codebase's own `_OP_AFFECTING_PARAMS`/`_RECOMPUTE_TRIGGERING_PARAMS` already encode this — routing `_apply_preset_estimates` through `update_assumption` yields correct physics with no new policy. `g_limit` is the exception worth propagating: it sizes spars, and built spars carry no provenance. 🔴 **`power_to_weight` unit bug is live and must be fixed before any fan-out.** | **high** on the per-parameter physics; the propagate-vs-apply choice is a **preference**, not derivable |

---

## Appendix — findings outside the brief

Encountered while verifying premises; recorded so they are not lost, not
investigated further.

- 🔴 **`power_to_weight` unit error in five of the nine mission presets.** Detailed
  under `Q-MS-10b`. Live today, independent of any fan-out decision — it makes
  `V_max` wrong for every aircraft whose mission has been set. Deserves its own
  bug ticket rather than riding along with the propagation work.
- 🔴 **Component-tree positions are empty and unwritable for mass-bearing nodes.**
  0 of 609 rows positioned; `NodePropertyPanel.tsx:260-262` writes `pos_*` only for
  `cad_shape`, and every mass-bearing node is `cots`. This **blocks `Q-MB-1`'s
  switch of the CG source to the tree** and affects `cg_x`, not just y/z. Detailed
  under `Q-MB-3`.
- 🔴 **`wing_xsec_spares` carry no record of the `g_limit` they were sized under**,
  so a later g-limit increase silently leaves built spars under-strength. Detailed
  under `Q-MS-10b`; the only finding in this briefing with a physical safety
  consequence.
- 🟡 **A test is broken on a clean checkout.**
  `app/tests/test_elevator_authority_avl.py:757` imports
  `app.schemas.aeroanalysis_schema`; the module is `app.schemas.aeroanalysisschema`.
  `ModuleNotFoundError`, pre-existing, unrelated to this work. Under Iron Law 6 a
  broken test is a blocker, not a footnote.
- 🟡 `app/tests/test_tessellation_endpoint.py::test_tessellation_returns_valid_viewer_json`
  also fails on a clean run. Note that ADR 0021's worked verdicts delete the
  wing-tessellation subsystem outright (`Q-CG-4`), so this may resolve itself.
