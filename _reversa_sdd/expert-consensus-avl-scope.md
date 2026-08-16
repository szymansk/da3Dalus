# Expert consensus and decision record — AVL scope boundaries

**Questions:** `Q-AV-2`, `Q-AV-3` + `Q-AV-4`, `Q-AV-8`, plus one sub-question raised
during the consultation.
**Decided:** 2026-08-15 by the maintainer, during the specification validation
interview. **This file is the reasoning record behind those decisions**, not a set of
open recommendations. Where a decision went against a source, the loss is recorded and
explained.

**Scope.** Hobby RC and UAV aircraft, **0.5–15 kg**, chord Re ≈ 5·10⁴–5·10⁵, M < 0.15.
Never transport-category. Users range from hobbyists to professional RC/UAV designers.

**Standing constraint.** [ADR 0003](adrs/0003-aerosandbox-default-avl-exception.md) —
AeroSandbox is the default; AVL is reached for only where ASB cannot cover the case.
Nothing below argues for more AVL without saying why ASB cannot do it.

**Method.** The four domain-expert skills were consulted in the authority order set by
`CLAUDE.md`, each in its own subagent with the framing constraints written into its
brief. In parallel every premise in the three questions was checked against the code
rather than accepted — which mattered: **eight premises needed correcting, and two of
the corrections inverted the answer.** Where a subagent supplied an AVL source citation
that a decision rests on, that citation was re-read directly in `Avl/src/` before being
recorded here; the four load-bearing ones are marked ✅ **verified in-repo**.

---

## Sources actually consulted

| Skill | Vault | What it had | What it did **not** have |
|---|---|---|---|
| `avl-advisor` | AVL 3.40 User Primer (`Avl/avl_doc.txt`) **+ the complete AVL 3.40 Fortran source in-repo** (`Avl/src/*.f`) | Everything. Body force accumulation, surface/strip index assignment, the `OPER→M` parameter table, `SYSMAT` validation, `MRF` output | — (the strongest-sourced answer of the four) |
| `aircraft-design-scholz` | Scholz HAW lectures + Sadraey *Aircraft Design* (Wiley 2013) | `K_f1` fuselage efficiency factor, `V_v` tables, ultimate-load-factor table, lateral-directional quartic, MIL-F-8785C Level tables, inertia build-up (§11.7) | **No additive fuselage `Cnβ` term at all.** Munk and DATCOM/Multhopp are *not* in the vault — flagged by the expert as world knowledge |
| `aerodynamics-expert` | Anderson *Fundamentals of Aerodynamics* 6e (237 concepts) | The mechanism in parts: source vs vortex panels, d'Alembert's paradox, the crossflow-cylinder solution, sub-critical `C_d` ≈ 1.0 below Re ≈ 3·10⁵, low-Re transition sensitivity | **No slender-body theory, no Munk moment, no `Cnβ`, no `Clβ`, no parasite-drag component split.** Verified by full-text search; the only "Munk" hits are thin-airfoil theory and the coining of "induced drag" |
| `rc-aircraft-designer` | rcplanedesigner.com, Lennon 1996, RC-Network Wiki (765 concepts) | CLA / Spiral-Stability-Margin method, fin area ratios, static-margin tables, the dihedral-vs-fin balance, phugoid as a CG flight-test tool | **Zero hits for `Cnβ`, "stability derivative", "short period", "eigenmode".** No numeric `V_v` table, no glider static-margin table, **no structural n-limit or safety-factor table** |

> **Chore finding, unrelated to the four questions.** The `avl-advisor` skill's
> `SKILL.md` points at `Avl/avl_doc.txt` and `Avl/doc/TextBudziak.md` **relative to the
> skill directory**, but `.claude/skills/avl-advisor/` contains only `SKILL.md`. The
> documents live at the repo root. The skill is broken as packaged — a subagent that
> cannot find the file answers from memory instead. Worth a ticket.

> **Two errors in the AVL primer itself**, found by reading the source against it, and
> relevant because this project *generates* AVL input. (1) `avl_doc.txt:1969` and
> `:1983` both show `MA` — for *Mach* and for *dCM_a*. The shipped code uses **`MN` for
> Mach** (`Avl/src/amode.f:1767`); this project already emits `mn`, so it is correct.
> (2) `avl_doc.txt:1245-1247` prints `Ixy = ∫xy dm`, `Ixz = ∫xy dm`, `Iyz = ∫xy dm` —
> the last two are copy-paste errors. The tensor diagram at `:1254-1258` is correct.

---

## Premise corrections — read this before the four answers

Each was verified by reading the code, not inferred.

**① The split is not "AVL vs AeroSandbox". It is "vortex-lattice vs AeroBuildup."**
`_build_asb_fuselages` (`app/converters/model_schema_converters.py:520-552`) builds
`asb.Fuselage` objects — with gh-715 mirroring, and gh-790 deliberately skipping
degenerate fuselages so they cannot make AeroBuildup return all-NaN — and `:824`
attaches them to the airplane. Of the three solvers `analyse_aerodynamics` dispatches
(`app/api/utils.py:97-127`), **AVL and the ASB VLM are both wing-only for `Cnb`; only
AeroBuildup sees the fuselage.** Two of the three solvers a user can select carry the
divergence, not one. The divergence is therefore real and structural, exactly as
`Q-AV-2` states.

**② `AvlBody`/`BFIL` *would* contribute to `Cnb` — and would contribute ≈ zero drag.**
The question assumes the body model covers both. The AVL source says otherwise, and
provably. Body moments reach the totals and the freestream sensitivities that produce
`ST` derivatives (`Avl/src/aero.f:1374,1402,1414`). But the body force is purely normal
to the local axis (`aero.f:1346-1347`), so for an axis-aligned body `FB(1) = 0`
identically and `CDBDY = FB(3)·sinα·2/Sref` — **at α = 0 an AVL body has exactly zero
drag.** No skin friction, no form drag, no base drag.

**③ Strip forces are keyed by NAME, end to end — not by index.** ✅ **verified
in-repo.** `Avl/src/aoutput.f:168-174` writes, per surface,
`WRITE (LUN,211) N, …, STITLE(N)(1:NT)` under `211 FORMAT (I2,1X,F9.3,8F8.4,3X,A)`; the
`FS` strip-force block does the same at `aoutput.f:290-296`
(`WRITE (LUN,211) N,STITLE(N),NV,NS,J1,…`). **AVL prints the surface name beside the
index in every force output.** `parse_strip_forces_output`
(`app/services/avl_strip_forces.py:127-147`) captures both, and the join back to the
database is by name — `build_thickness_maps_for_surface(..., surface_name=...)`
(`app/services/section_thickness.py:34-59`), called from `analysis_service.py:2241-2247`.
**A lifting-surface index mix-up is not the live hazard in spar sizing.** Two incidental
facts from the same format string: `I2` means an index above 99 prints `**`, and `F8.4`
means four decimals, **which quantises small RC-scale coefficients**.

**④ The CONTROL d-index map is LIVE on the trim path today, and it has two independent
producers.** AVL's `OPER` language has no name for a control; deflections are
`d{i} d{i} <value>`. `get_control_surface_index_map` (`avl_strip_forces.py:150-171`)
assigns those indices and **is production code** — `avl_trim_service.py:134` and
`avl_strip_forces.py:216`. The question's note that it is test-only is wrong, and the
correction matters: **every AVL trim already maps control names to AVL indices, with no
hash check guarding it.** But `build_control_deflection_commands`
(`avl_strip_forces.py:233-253`), which is what `AVLRunner._build_keystrokes` actually
calls (`avl_runner.py:159`), performs its **own** walk and its **own**
`enumerate(..., 1)`. **BR-AV13's claim that the two are "derived from one walk, so they
can never drift" does not match the code.** They are two walks that happen to be written
identically.

**④b Confirmed unreached, by direct measurement.** `build_avl_artefact` and
`verify_avl_replay` have **no** callers outside `app/tests/`. The lines sometimes cited
as call sites (`avl_artefact_service.py:88-89`) are *inside the body of
`build_avl_artefact` itself* — self-references counted as callers.
`build_yduplicate_sign_map`'s only non-test reference is from that unreached service.

**⑤ When a stored `.avl` is used, the d-indices come from a different object than the
file.** `_run_avl_strip_forces` (`analysis_service.py:1825-1831`) passes
`airplane=asb_airplane` (built from the **database**) to `AVLRunner`, then runs it
against `user_avl_content` (the **user's stored text**). Deflection indices and
`b_ref`/`c_ref` come from the DB; the geometry comes from the file. Nothing checks that
they agree.

`trim_with_avl` has the same defect, on **both** sides of the run. It consults the
stored file (`avl_trim_service.py:88`, passed at `:119`), and:

- **before** the run, `build_indirect_constraint_commands(asb_airplane, …)` emits
  `d{i} <target> <value>` tokens computed from the **DB airplane**
  (`avl_strip_forces.py:216`), which AVL resolves against the **stored file's**
  `CONTROL` declaration order. A hand edit that adds, removes or reorders a `CONTROL`
  silently retargets the trim constraint onto a different surface;
- **after** the run, `_categorize_results(result, set(cs_map.keys()))`
  (`avl_trim_service.py:134-135`) filters results by the **DB-derived** names, so a
  control present only in the file is dropped and one present only in the DB is expected
  and absent.

**This is what made `Q-AV-3` more urgent than its framing suggested:** the index map is
not dormant scaffolding awaiting a replay feature. It is load-bearing on the live trim
path *right now*, built from a different object than the file whose declaration order
defines the indices it produces.

**⑥ `POST …/regenerate` did not clear `is_dirty` — it deleted the row.**
`regenerate_avl_geometry` (`app/services/avl_geometry_service.py:337-351`) calls
`db.delete(geom)`. So `Q-AV-4` as posed could not occur: there was no `is_dirty` left to
clear, because the user's edits were destroyed. The only non-destructive route back was
a fresh `PUT` (`:315-334`, which sets `is_user_edited=True, is_dirty=False`). **The
decision below changes this behaviour** — see `Q-AV-4`.

**⑦ The dirty listener over-fires, provably.** `app/models/avl_geometry_events.py:18,58-60`
listens on `after_insert|update|delete` for `WingModel`, `WingXSecModel` **and
`FuselageModel`**. `app/services/avl_geometry_service.py` contains **zero** occurrences
of "fuselage" — the `.avl` file has no fuselage content whatsoever. **Every fuselage
edit invalidates a file it cannot possibly have changed.** So does any `WingModel`
column update, since the listener does not inspect which attributes changed.

**⑧ A per-component mass model with positions exists.** `component_tree` carries
`pos_x/pos_y/pos_z` **and** per-node mass (`app/models/component_tree.py:49-61`).
Inertias — including `Ixz` — are computable today by Sadraey's §11.7 method; nothing
computes them. This is the precondition `Q-AV-8` is gated on, and it is satisfiable.

---

# ① Q-AV-2 — Is the wing-only AVL model an accepted limitation?

## Decision (maintainer, 2026-08-15)

**No `BODY`, ever. AVL stays lifting surfaces only, and AeroSandbox is the sole
authority for `Cnb`.** The primer's own suggested alternative — crossed `SURFACE` blocks
with `NOWAKE` — was **also rejected**. The limitation is accepted as physics; what was
treated as the defect is the *labelling*.

## Why — the reasoning behind it

**The mechanism (aerodynamics-expert, from Anderson).** Decompose the freestream at
sideslip β into axial and crossflow components; each station sees a locally 2-D cylinder
([[cylinder-nonlifting-flow]], Anderson 6e Ch. 3.13). D'Alembert's paradox
([[d-alembert-paradox]], Ch. 3.13 / 15.1) asserts the *force* integrals vanish
(D = ∮p cosθ dA = 0, L = ∮p sinθ dA = 0) — it says nothing about the *moment* integral,
which for a circular cylinder vanishes only by an extra top-bottom symmetry a slender
body at incidence does not have. Outward loading on the expanding nose and inward loading
on the contracting tail form **a pure couple with no resultant force**. The expert's
framing: *"the Munk moment is the moment-counterpart of d'Alembert's paradox — the same
calculation."* Anderson supplies every ingredient and never assembles them; the assembled
result is **Munk, NACA TR-184 (1924)**, refined by **Allen & Perkins, NACA TN-2044
(1951)** — labelled as outside the vault, not passed off as sourced.

**Why a VLM cannot produce it — and the diagnosis matters.** Anderson fixes the method
completely: one horseshoe vortex per panel, Biot–Savart influence coefficients, forces
via Kutta–Joukowski `L′ = ρV∞Γ` ([[lifting-surface-theory-and-vortex-lattice]], Ch. 5.5).
*The entire solution space is spanned by vorticity.* Anderson draws the line explicitly
in [[panel-techniques]] (Ch. 6.5) — *"Nonlifting bodies (e.g., fuselage, nacelle): source
panels alone are sufficient; lifting bodies: both source and vortex panels are
necessary."* The expert is careful about which absence is responsible: **it is not "no
thickness"** — thin-airfoil theory has zero thickness and still gets lift and moment
right (Ch. 4.7) — **it is no displaced volume**, i.e. no source/doublet in the basis. The
moment ∝ Vol, and a zero-thickness sheet encloses zero volume. *"A million panels changes
nothing; you are refining the wrong function space."* Note the scope of the claim: this
is a **vortex-lattice** limitation, not a potential-flow one — a proper 3-D source/doublet
panel method does capture it.

**Why the primer's own alternative was rejected too — the tool authority lost to the
physics authority.** `avl_doc.txt:528-530` suggests: *"Non-lifting fuselage modeled by
its side-view and top-view profiles. This will capture the moment of the fuselage
reasonably well"* — i.e. crossed `SURFACE` blocks with `NOWAKE`. The aerodynamics
authority rejects this on first principles, and the argument is decisive: **a
lifting-surface substitute produces a side force with a centre of pressure, where the
truth is zero net force plus a pure couple.** Hitting the right `Cnb` at one geometry is
therefore *calibration, not physics* — and it **cannot track across fineness ratio**,
because the true term scales with **volume** while the substitute scales with **planform
area**. A correlation that is right for one fuselage is wrong for the next, silently and
in an unknown direction. This is the one place in the whole consultation where AVL's own
documentation recommends something the project declined to do; it is recorded here so
the divergence from the primer is deliberate and traceable rather than an oversight.

**Magnitude at our scale (scholz).** Reference aircraft 3 kg, S = 0.40 m², b = 1.6 m,
l_f = 1.1 m, d_f = 0.10 m; at C_L = 0.5 → V = 15.5 m/s, Re_c = 2.65·10⁵.

| Fuselage case | `Cnβ,fus` /rad | `Cnβ,total` at V_v = 0.035 | equivalent `K_f1` | omission error |
|---|---|---|---|---|
| Slim pod + boom | −0.0106 | +0.0582 | 0.85 | +18 % optimistic |
| **Central estimate** | **−0.0150** | **+0.0538** | **0.78** | **+28 % optimistic** |
| Fat trainer pod | −0.0250 | +0.0438 | 0.64 | +57 % optimistic |

Fuselage share of gross magnitude: **13–27 %** (central 18 %). **The sign cannot flip:**
reversal would need Vol_f ≥ 0.0234 m³, which is **2.7× a solid 0.10 m × 1.10 m
cylinder** — geometrically impossible at the stated width. The regime where it *does*
flip is `V_v < ~0.008` — a blended-body or tailless UAV with vestigial fins. The
equivalent `K_f1 = 0.64–0.85` lands on Sadraey's stated 0.65–0.85 band (§6.8.2.2), which
is real cross-method agreement.

**Scale dependence — the fuselage is a *milder* destabiliser at RC scale (scholz).**

| Aircraft | Vol_f/(S·b) | Vol_f/m (m³/kg) | (W/S)/(g·b) |
|---|---|---|---|
| **3 kg RC, pod+boom** | **0.0063** | 0.00135 | 4.69 |
| Cessna 172 | 0.0261 | 0.00418 | 6.23 |
| Boeing 737-800 | **0.0769** | 0.00416 | 18.5 |

**6–12× better than an airliner.** The driver is not bulkiness per kg (nearly identical
for the C172 and the 737) — it is **wing loading**: 74 N/m² vs 6220 N/m², a factor of 84,
and S sits in the denominator. Applying Sadraey's transport-derived `K_f1` to a 3 kg
model is therefore mildly *conservative* — but conservative by accident, not by design.

**Reynolds validity.** The governing Reynolds number for the crossflow correction is the
*crossflow* one, not body length: Re_c = V·sinβ·d/ν ≈ **3.5·10⁴** for a 15 kg UAV at
β = 10°. Anderson's cylinder data ([[karman-vortex-street]] Ch. 3.18;
[[real-flow-sphere-separation]] Ch. 6.6) put the drag crisis at Re ≈ 3·10⁵, so we sit
**sub-critical on the flat part where C_dc ≈ 1.0–1.2 and is Re-insensitive across the
whole 0.5–15 kg envelope** — under
[ADR 0023](adrs/0023-engineering-constants-carry-provenance.md) this constant is
validated in the right regime, not borrowed. The Munk term itself is inviscid and
therefore Reynolds-independent, so it transfers exactly.

**What AVL's own author says** (`avl_doc.txt:110-118`, verbatim):

> "The resulting force and moment predictions are consistent with slender-body theory,
> **but the experience with this model is relatively limited, and hence modeling of
> bodies should be done with caution.** If a fuselage is expected to have little
> influence on the aerodynamic loads, **it's simplest to just leave it out of the AVL
> model.**"

And `version_notes.txt:185-186`: *"It's not yet clear how useful this modeling capability
will be."* The body path also has a bug history — `version_notes.txt:438-440` records a
fix to body force derivatives, and a second historic bug is still visible as a commented
line at `Avl/src/aero.f:1409`.

**AeroBuildup is a strict superset** (verified against the installed package).
`AeroBuildup.fuselage_aerodynamics`
(`aerosandbox/aerodynamics/aero_3D/aero_buildup.py:905`) implements slender-body theory
citing **Drela, *Flight Vehicle Aerodynamics*, Eq. 6.77/6.78** (`:1003`, `:1007`) — the
same physics as AVL's `BODY` — and adds **Jorgensen cross-flow** (`:936`), **skin
friction with form factor** (`:1048`) and **base drag** (`:1044`). AVL's `BODY`
singularity strengths are moreover *prescribed from the onset flow, not solved*
(`Avl/src/asetup.f:418`), so the body never responds to wing-induced flow: the solve adds
nothing computable in closed form from the volume distribution.

**Decisive on governance.** `stability_service.py:346` renders
`is_directionally_stable = (cnb > 0)` from whichever solver the caller picked, persists
it (`:357`) and hands it to the AI copilot (`copilot_tools.py:457-460`);
`trim_enrichment_service.py:169` computes the same boolean on a second path. Under
[ADR 0022](adrs/0022-one-authority-per-user-facing-quantity.md) that is two producers of
a user-facing number with nothing deciding which is right — and corollary 1 forecloses
the obvious compromise: *"Keeping both and warning on divergence … leaves the number
order-dependent. A warning tells the user the system does not know the answer; it does
not supply one."* Both a `BODY` block and a bolted-on empirical correction would have
created a **third** producer.

**What RC practice does — and it is better than "implicitly absorbed".** Exhaustive grep
of 765 concepts for `Cn_beta`, "stability derivative": **zero hits.** Nobody at this scale
computes it. But the fuselage is handled **explicitly**: Grant's **CLA method** (Model
Airplane News 1941, via Lennon Ch. 9) cuts a full-size cardboard **side-view profile of
the entire aircraft** — fuselage, canopy, dihedral side-projection, gear, fin — and
plumb-lines it to find the centroid; the fin is sized so the CLA sits 22–33 % of VTMA aft
of the CG. Lennon Ch. 11: *"elongating the fuselage ahead of the CG increases its
directionally destabilizing side area, requiring increased vertical tail area."*
Sensitivity: on the Skylark, moving CLA from 22 % to 30 % of VTMA — **1.65 inches** —
would have needed a **60 % increase in fin area**.

## Dissent recorded

**Scholz ranks a larger error source than the one the question is about.** For the
reference aircraft:

| Error source | Effect on `Cnb` |
|---|---|
| **η_v — fin in prop slipstream vs fuselage wake** | **±25 %** ← *largest* |
| Omitted fuselage term | −18 to −57 % (one-signed) |
| `C_Lα_v` at AR 1.5, Re ≈ 10⁵ | ±20 % |
| Fuselage-induced sidewash on the fin — **also invisible to a VLM** | ±15 % |
| Uncertainty *within* a fuselage correction | ±50–100 % of a 20 % term |

*"Adding a fuselage correlation while η_v remains a hard-coded 0.95 is fixing the
second-largest error while ignoring the largest."* This independently supports the
decision not to bolt one on.

**Scholz also argues against reporting an absolute `Cnb` at all.** Sadraey §6.8.1: hitting
the statistical `V_v` target gives **~90 % confidence** directional stability is
satisfied. *"The statistical `V_v` tables were regressed from real aircraft that had
fuselages — the fuselage penalty is already baked into `V_v` = 0.03–0.04. If you size by
`V_v` you do not need the correction at all."* The RC expert reaches the same place with a
sharper caveat: the rules of thumb are calibrated *"only for the fuselage proportions
those models had"* — which is why the CLA method exists alongside them, and why a UAV with
a payload pod or boom tail falls outside every calibration behind them.

**Both quantitative experts want a hard gate at low `V_v`.** Scholz: *"if `V_v` < 0.015,
the fuselage term is no longer a correction — raise a blocking warning and refuse to
certify directional stability from `V_v` alone."* This is the one regime where the
wing-only number is wrong in **sign**, not merely optimistic. Carried into the decision as
a rider.

## Open premises (not closed by this decision)

- **Propeller position relative to the fin** (η_v ≈ 0.8 shadowed vs 1.2–1.3 in
  slipstream) — **±25 % on `Cnb`, larger than the entire fuselage term**, and not
  represented in the aero model.
- **Fuselage prismatic coefficient** — "max width 0.10 m" does not fix the volume; the
  three plausible shapes span 2.4× on `Cnβ,fus`.
- **Fuselage surface finish.** The aerodynamics expert explicitly declined to assume the
  fuselages are 3-D printed just because the wings are; roughness is a first-order driver
  of separation location (Anderson Ch. 6.6).

---

# ② Q-AV-3 + Q-AV-4 — When may a stored `.avl` file be reused?

## Decision (maintainer, 2026-08-15)

**Parse, don't cache.** The replay-artefact machinery — `build_avl_artefact`,
`verify_avl_replay`, `compute_geometry_hash`, `AvlReplayMismatch` — is **deleted** as
complete-but-unreachable under
[ADR 0021](adrs/0021-complete-but-unreachable-code-is-deleted-by-default.md) rule 1.
`get_control_surface_index_map` **stays**, because it is live on the trim path
(premise ⑤). **A successful regenerate now clears `is_dirty`.**

> **Implementation note.** Today `regenerate_avl_geometry`
> (`avl_geometry_service.py:337-351`) does not clear the flag — it `db.delete(geom)`s
> the row outright (premise ⑥). "Regenerate clears `is_dirty`" is therefore a
> **behaviour change**, not a description of current code: the row must survive
> regeneration with refreshed content and `is_dirty=False`. The escape hatch stops
> silently expiring, which is what `Q-AV-4` was about.

## Why — the finding that dissolved the question

✅ **verified in-repo.** **AVL prints the surface name beside the index in every force
output.** `Avl/src/aoutput.f:168-174` writes `N, …, STITLE(N)(1:NT)` per surface under
`211 FORMAT (I2,1X,F9.3,8F8.4,3X,A)`; the `FS` strip-force block does the same at
`aoutput.f:290-296`. **The index→name mapping is recoverable from every single run, so it
never needs persisting.** The artefact's `index_snapshot` solves a problem that does not
exist.

And it does not solve the one that does. `compute_geometry_hash`
(`avl_artefact_service.py:33-67`) **deliberately excludes coordinates**, docstring
verbatim:

> The hash covers ONLY the fields that govern AVL surface indexing: wing-order,
> xsec-order within each wing, and (name, symmetric, hinge_point) per control surface.
> Floating-point coordinates are excluded because they're irrelevant to the index map and
> drift across model edits.

**A wing whose span doubled produces the same hash.** The hash is correct for its stated
purpose — gh-529 control-index drift — and unfit as a gate on reusing a stored `.avl` for
loads, because loads depend on nothing but the excluded coordinates. Wiring it would have
installed a check that *reads* like it guards load reuse and does not, which is precisely
the failure ADR 0021 names: *"a protection appears to exist that does not, and a reader
who finds it stops looking for the check that is missing."*

`verify_avl_replay` (`:110-151`) additionally hashes the **live ASB airplane** against a
stored artefact, so it could never see a hand edit to the `.avl` text at all — the exact
case the escape hatch exists for.

## The per-edit invalidation table — reproduced in full

This is the reasoning that makes the deletion safe. Two distinct things can break: the
**index map** (surface index → logical component) and the **strip block**
(`JFRST`/`NJ` per surface, hence the global strip number `j`).

| Edit | Index map changes? | Strip ordering changes? | Mechanism |
|---|---|---|---|
| **(a)** `CONTROL` added to a section | No | No | Controls create no surfaces or strips; they only rotate normals aft of `Xhinge` (`Avl/src/amake.f:1161-1206`) |
| **(b)** Surfaces reordered in the file | **Yes** | **Yes** | By definition; `NSURF` increments once per `SURFACE` keyword in file order (`ainput.f:279`) |
| **(c)** `YDUPLICATE` toggled | **Yes** | **Yes** | The image is inserted **immediately after its parent** (`NNI = NSURF+1`, `amake.f:718`) → every later index shifts ±1; the image consumes `NJ(parent)` strips (`amake.f:744-745,775-776`) |
| **(d)** `NSPAN` changed | No | **Yes** | `NJ(N)` changes → every later `JFRST` shifts → the global strip number `j` renumbers |
| **(d′)** `NCHORD` only | No | No | Only `NK(N)`/`IFRST` change — affects `FE` element indices, not `FS` strip indices |
| **(e)** Section coordinates only (`Xle/Yle/Zle/chord/Ainc`) | No | No | `NVS = Σ NSPANS(ISEC)` is purely count-based, independent of coordinates (`amake.f:112-148`) |

**The two cases that matter — hash intact, map invalid.** A hash over the *surface list*
(names + order) still matches while the stored index map is invalid in exactly two cases:

- **(c) `YDUPLICATE` toggled** — the surface declaration list is unchanged, but surface
  *and* strip numbering both shift.
- **(d) `NSPAN` changed** — the surface list is identical, and strip numbering renumbers
  silently.

And **(a) invalidates a stored *control* map** without touching the surface list at all:
the `d(t)` control vector is *"whatever controls were declared in the xxx.avl file, in the
order that they appeared"* (`avl_doc.txt:2309-2310`). That ordering keys the `ST`
derivative columns, `HM` hinge moments, and the `D1`/`D2` constraint slots.

**Both live cases are reachable in this codebase, and one is not a geometry edit at all.**
(c) is driven by `yduplicate=0.0 if wing.symmetric else None`
(`avl_geometry_service.py:162`) — toggling a wing's `symmetric` flag changes the surface
count. (d) is worse: `n_span` comes from `optimise_surface_spacing(surface, spacing_config)`
(`:166`), and `SpacingConfig` arrives on the **operating point**
(`analysis_service.py:1820`). **Strip numbering can therefore change between two runs with
byte-identical geometry**, simply because the caller passed a different spacing config.
**No geometry hash of any coverage can detect that** — which is the final argument against
option "widen the hash".

**A sufficient hash would have needed**, per surface: name, position in file, `Nchord`,
`Cspace`, `Nspan`, `Sspace`, every per-section `Nspan`/`Sspace`, the `YDUPLICATE` flag,
**and** the control-name list in declaration order. The current artefact hash covers the
control names and the wing/xsec ordering, and none of the rest.

## How dangerous a mis-attributed load is — the reasoning kept for the record

**Scholz, physical magnitudes.** Bending moment is a *double* integral of the load, so
mis-attribution corrupts both the total force and its lever arm, in the same direction.
For the 3 kg reference aircraft with a horizontal tail at `V_H = 0.6` (S_h/S = 0.30,
b_h/b = 0.43, tail load ≈ 0.15·n·W):

| Case | M_root | Error |
|---|---|---|
| **TRUE (wing, elliptic, n_ult = 6)** | **29.98 N·m** | — |
| HT strip forces at HT y-stations (outer 57 % of wing unloaded) | 1.95 N·m | **15.4× unconservative** |
| HT strip forces re-mapped onto wing y-stations | 4.50 N·m | **6.7× unconservative** |

At σ_allow = 600 MPa the true answer picks a **10 × 1.0 mm carbon tube** — *"exactly what
an experienced RC builder would fit; the method is calibrated"* — while the mis-attributed
case picks 5 × 0.5 mm, which **fails at n = 0.87**. The wing breaks on the hand-launch.

**But that is the *safe* failure.** A 7–16× error *"is so gross the aircraft cannot leave
the ground — caught by the first flight, not by silent margin erosion. Bad, but
self-announcing."* The insidious case is **left/right mirroring**, which for a symmetric
wing under a symmetric load case is **exactly a no-op** — any test exercising only
symmetric cruise passes forever. It bites only on asymmetric cases (rolling pull-out,
aileron manoeuvre, sideslip), where the up-going panel carries ≈ 1.2× and the down-going
≈ 0.8×: **35–50 % unconservative**, *"inside everyone's intuition of close enough."*

**The margin does not absorb it.** Sadraey Eq. 10.4: `n_ult = 1.5 · n_max`. *"The 1.5 is
not a load-model factor. It exists to cover material scatter, manufacturing variation,
damage/fatigue, and analysis idealisation."* A 35–50 % load error consumes the entire
factor — residual margin **1.5/1.4 = 1.07**. And the 1.5 is weaker at this class than at
transport class, because there it sits inside a certification apparatus (A-basis
allowables, qualified processes, NDI, static test to ultimate) that *"does not exist for a
3 kg RC/UAV."*

**Would a builder notice? No — the highest-severity finding in the RC report.** *"There is
no proof-load test in RC practice. Nothing in the vault describes sandbagging a wing, a
static load test, or a test to failure — not one concept."* The spar is not sized from a
load distribution in the first place (stock dimensions by chord, Lennon Ch. 13), so a
wrong distribution feeds nothing the builder compares against; builder intuition catches
*"10× wrong, not 1.4× wrong"*. The practical failure is either a silently over-heavy wing,
or an under-built spar that survives normal flight and fails in *"the ~12 g panic pull-up
from a dive … low altitude, high speed, unrecoverable."* The RC expert's verdict in the
project's vocabulary: **defect severity, not domain-practice severity.**

**Which hazard is actually live here — and it is none of the above.** Because the join is
by name (premise ③), a HT→wing swap cannot occur through this path. The live hazard is
**geometric drift with a name-preserving join**: bending moments come from the stored
`.avl`, section thickness comes from the **current DB geometry**, and
`build_thickness_maps_for_surface` rescales each load station against the **live** wing's
half-span, then clamps (`section_thickness.py:71-73`):

```
y_span = abs(float(y_m)) * 1000.0 / half_span_mm
y_span = min(max(y_span, 0.0), 1.0)
```

If the stored file's span exceeds the live wing's, outboard stations **clamp to 1.0** and
a mid-span load is sized against tip thickness. If it is shorter, the live outer wing is
never loaded at all — structurally the **same shape** as scholz's 15.4 × unconservative
case, arrived at by a different route. **No warning is emitted in either direction.** That
silent clamp is an undeclared fallback under
[ADR 0020](adrs/0020-one-designwarning-channel-no-undeclared-fallbacks.md) and should emit
a `DesignWarning` at `error` severity.

**Scholz's mitigation, kept because it is independent of all of the above.** *"A
load-attribution bug is silent — it returns a number, just the wrong one. Unit tests on
mocked strip data will not catch it."* Catch it with physics invariants in the solver:

1. `|Σ(strip F_z on wing) − n·W·(1 − L_h/W)| / (n·W) < 0.05` — total lift must close on
   weight.
2. The load footprint's span must match the wing's y-range — *"bug (a) fails this
   instantly, since the load stops at 43 % span."*
3. `M_root ≈ n·W/2 · ȳ_elliptic` within a factor 1.5 — a coarse independent estimate no
   mis-attribution can pass.

## A geometry invariant AVL generation actually needs — measured on the live database

Measured after the consultation: of **82 wing roots in the live database, 74 sit on the
centreline and 8 do not.** Six of the eight are struts and vertical surfaces where the
offset is deliberate and `YDUPLICATE` is correct — the primer's carry-through case does
not apply to them.

**But two `Wing` rows have `y_root = −0.205 m`.** A *negative* root y means the surface
crosses the centreline, so mirroring makes it **overlap itself by 0.41 m**. That is not a
missing centre section — it is a **doubled** one, and it silently corrupts `Sref`, `CDi`
and the reported `e = (CL²+CY²)/(π·A·CDi)` (`avl_doc.txt:1643-1648`).

**So the invariant AVL geometry generation needs is `y_root ≥ 0` for any surface with
`YDUPLICATE`** — not the primer's carry-through check
(`avl_doc.txt:117-118`, *"the two wings should be connected by a fictitious wing portion
which spans the omitted fuselage"*), which addresses the opposite error. Both are worth
having, but only the overlap case is known to be present in real data.

> **Observation, not a measurement of mine:** those two rows are reported as carrying a
> **4 m chord**, which is far outside the 0.5–15 kg envelope this project targets. That
> may be a second, independent data defect (a units error, or demo data) rather than a
> consequence of the negative root y. Flagged for a look; I did not query the rows myself.

## Open premises

- **Whether any user has actually saved a hand-edited `.avl`.** The premise-⑤ hazard is
  conditional on `is_user_edited = True` rows existing. One query would settle its
  priority.
- **Whether the material allowables behind σ_allow are datasheet or knocked-down values.**
  Scholz: without it *"the effective structural margin behind the 1.5 factor is unknown."*
- **Whether asymmetric load cases are ever run.** Left/right mirroring — the insidious bug
  — is exactly a no-op on symmetric cases.

---

# ③ Q-AV-8 — Was file-based `.mass` / `.run` input deliberately dropped?

## Decision (maintainer, 2026-08-15)

**Deferred behind a precondition.** No `.mass` or `.run` files now. Ship the **spiral
criterion** and the **phugoid** instead — both inertia-free, both computable from data the
system already has. The other three modes (short period, roll subsidence, dutch roll) are
gated on a **real per-component mass model with positions**, and the system must **refuse
rather than guess** when that is absent.

## Starting correction

The question's premise — that mass properties reach AVL through the `OPER → m` submenu —
needs correcting: **no mass and no inertia is sent at all today.** `_build_keystrokes`
(`app/services/avl_runner.py:138-146`) uses that submenu for Mach, velocity, density and
gravity only:

```
ks: list[str] = ["OPER"]
ks += ["m", f"mn {op.mach()}", f"v {v}", f"d {op.atmosphere.density()}", "g 9.81", ""]
```

There is no `MASS` command, no `.mass` or `.run` writer, and **no `MODE` keystroke
anywhere in `app/`** — eigenmode analysis is not merely unexposed, it is entirely absent.
`x_cg` reaches AVL only as the file's reference point (`AvlReference.xyz_ref`,
`avl_geometry_service.py:186-191`).

## The full `.mass` field list

Reproduced because it is what "deliberately dropped" means concretely
(`avl_doc.txt:1149-1306`):

1. **`Lunit = <value> <name>`** — *not merely a label*. *"Lunit value will also scale all
   lengths and areas in the AVL input file"* (`:1164`). In code `UNITL` scales CG position
   (`Avl/src/amass.f:305-307`), inertias by `UNITL²` (`:293-303`), and derives
   `UNITF/UNITS/UNITV/UNITA` (`:492-520`).
2. **`Munit = <value> <name>`**
3. **`Tunit = <value> <name>`** — any missing unit line ⇒ magnitude 1.0 and the literal
   name `"Lunit"`/`"Munit"`/`"Tunit"` (`:1235-1237`).
4. **`g = <value>`** — gravity; **defaults to 1.0, not 9.81**, if absent (`:1264-1266`).
5. **`rho = <value>`** — density; same 1.0 default.
6. **Mass table rows:** `mass x y z [Ixx Iyy Izz Ixz Ixy Iyz]`, inertias about **that
   item's own centroid**, trailing values optional and assumed zero (`:1279-1285`).
7. **`*` multiplier and `+` adder lines**, applying to all subsequent rows and
   re-definable mid-table (`:1271-1274, 1287-1306`).

## Keystroke-settable vs not

Verified in `PARMOD`, `Avl/src/amode.f:1765-1782`:

| Settable via `OPER → M` | **Not** settable by any keystroke |
|---|---|
| `B` bank, `E` elevation, `MN` Mach, `V` velocity, `D` density, `G` gravity | **`Ixy`, `Iyz`, `Izx`** — written only by `MASPUT` from a `.mass` file (`amass.f:343-345`) |
| **`M` mass, `IX` Ixx, `IY` Iyy, `IZ` Izz** | `Lunit`/`Munit`/`Tunit` — no runtime setter at all (`amass.f:170,311`) |
| `X`/`Y`/`Z` CG, `CD` CDo | The per-item mass breakdown — only rolled-up totals reach a run case |
| `LA`/`LU`/`MA`/`MU` viscous modifiers | **`heading` (psi)** — `.run`-file only; the sole quantity with no setter in any AVL menu |

So **`Ixx`, `Iyy` and `Izz` *are* keystroke-settable** (`IX`, `IY`, `IZ`), and `MODE` is
reachable without a `.mass` file: *"Mass/inertia/CG can be input directly (in OPER's C1,
C2, or M submenus), or obtained from a xxx.mass file"* (`avl_doc.txt:2112-2114`). Two
routes reach the products of inertia — a `.mass` file (top-level `MASS f`, then `MSET i`,
`avl_doc.txt:1349,1353`) or a `.run` file (top-level `CASE f`, `:1350`, carrying
`Ixy`/`Iyz`/`Izx` lines at `:2039-2041`).

Note the scope difference: `OPER → M` edits **one run case**; the mass file sets the
**defaults** pushed into run cases by `MASPUT`/`MSET`.

## The three `MODE` traps — all three, for the record

**Trap 1 — `g` and `rho` silently default to 1.0.** Without a `.mass` file, `g` and `rho`
default to **1.0, not 9.81 / 1.225** (`avl_doc.txt:1264-1266`), and `Lunit/Munit/Tunit`
default to magnitude 1.0. Eigenvalues then emerge in a nonsense unit system **with no
warning at all**. Contrast with the inertias, which AVL *does* guard: `SYSMAT`
(`Avl/src/amode.f:844-875`) validates V, mass, `Ixx`, `Iyy`, `Izz` — each must be > 0 —
and otherwise prints `** Zero Ixx. Specify with mass file or M menu` followed by
`Eigenmodes not computed for run case N`, then returns. Products of inertia are
deliberately **not** checked, because zero is legitimate for a symmetric aircraft.
**Consequence: any future `MODE` work must assert on `g` and `rho`, not on the inertias.**
This project already emits `g 9.81` and `d {density}` explicitly, so it is covered today.

**Trap 2 — AVL adds apparent air mass itself, so supplied inertias must not pre-include
it.** `SYSMAT` adds air apparent mass and apparent inertia to the airframe values:

```
Avl/src/amode.f:889-897   MAMAT(K,K) = AMASS(K,K)*RHO + RMASS
                          RIMAT(K,L) = RINER(K,L) + AINER(K,L)*RHO
Avl/src/amass.f:466-476   APPM = S_strip * 0.25*PI*c_perp   (thin-plate added mass, per strip)
```

For a 0.5–2 kg foam or balsa model the entrained air mass is a non-negligible fraction of
airframe mass, so it genuinely shifts the modes — unlike at transport scale, where it is
noise. **An `Ixx`/`Iyy`/`Izz` estimate must NOT pre-include added air mass; AVL adds it,
and doing it yourself double-counts.** This trap is specific to our scale and is the
easiest of the three to get wrong.

**Trap 3 — `.mass` and `.run` use opposite sign conventions for the products of inertia.**
The `.mass` file takes raw products `Ixy = ∫xy dm`; AVL stores the **negated** tensor
elements:

```
Avl/src/amass.f:294   RINER0(1,2) = -Ixy * UNITM*UNITL**2
Avl/src/amass.f:343   PARVAL(IPIXY,IR) = RINER0(1,2)
Avl/src/amode.f:829   RINER(1,2) = PARVAL(IPIXY,IR)      ! straight into the tensor
```

So the `Ixy`/`Izx` numbers in a **`.run`** file are already sign-flipped relative to the
**`.mass`** convention. **Anything generating `.run` files directly must use the run-file
convention.** A generator that writes both from one source, unaware of this, produces two
files that disagree.

## Why the deferral is defensible — and where the boundary genuinely sits

**What each mode requires (scholz, Sadraey §12.3.2–12.3.3, §11.7).**

| Mode | Governing relation | Inertia needed? |
|---|---|---|
| **Phugoid** | ω ≈ √2·g/U₁; ζ ≈ 1/(√2·L/D) | **None.** Pure energy exchange |
| **Spiral — *sign*** | unstable iff \|C_lβ·C_nr\| < \|C_lr·C_nβ\| | **None.** Pure derivative product |
| Spiral — *time-to-double* | root of the lateral quartic | `Ixx`, `Izz`, **`Ixz`** |
| Short period | ω² = −C_mα·q̄·S·c̄ / `Iyy` | `Iyy`, linearly |
| Roll subsidence | T_R ≈ `Ixx` / (−q̄·S·b²·C_lp/2V) | `Ixx`, linearly |
| Dutch roll | ω² ≈ −C_nβ·q̄·S·b / `Izz` | `Izz` (both ω and ζ) |

**Three of five modes are non-issues at this scale — with numbers.** Scholz computes the
3 kg reference aircraft (`Iyy ≈ 0.15`, `Izz ≈ 0.20`, `Ixx ≈ 0.15` kg·m², SM = 0.12):

| Mode | Value | Level 1 spec | Verdict |
|---|---|---|---|
| Roll subsidence | T_R = **0.069 s** | ≤ 1.0 s (Table 12.14) | pass ×14 — *"faster than the servo transport lag"* |
| Dutch roll | ω = 5.0 rad/s, ζ = 0.115 | ζ ≥ 0.08, ζω ≥ 0.15 (Table 12.16) | pass ×1.4 to ×12 |
| Short period | ω = **7.4 rad/s**, T = 0.85 s | ζ 0.35–1.3 (Table 12.11) | see below |
| Phugoid | T = 7.0 s, ζ = **0.088** | ζ ≥ 0.04 (Table 12.10) | pass ×2.2 |
| **Spiral** | **unstable ≤ 6° dihedral** | T₂ ≥ 20 s (Table 12.15) | **marginal** |

Dutch roll is *"a transport problem because it is a transport problem"* — Sadraey names
its causes as a large fin, a long fuselage (high `Izz`) and wing sweep, and *"a 3 kg RC
aircraft has none of the three."* Short period *"passes out of the human problem space and
into the autopilot problem space"*: at 7.4 rad/s it is above a pilot's 2–3 rad/s
crossover, so Table 12.11's ζ band is *"nearly vacuous for a human RC pilot"* — **but
inverts for a UAV autopilot**, whose 50 Hz loop has ample bandwidth to interact with it.

**The spiral is the exception, and the reason is a clean scale argument.** All mode
frequencies scale as 1/√λ (Froude scaling, `I ∝ λ⁵`), so our modes are **4.6× faster than
a 737's**. But the MIL-F-8785C specs are in **absolute seconds and rad/s**, because they
are set by human reaction time, which does not scale. So `T_R ≤ 1.0 s` is a **maximum
time** → easier for us; `ω_nd ≥ 0.4 rad/s` is a **minimum frequency** → easier; **`T₂ ≥
20 s` for the spiral is a minimum time** → our times shrink 4.6× → **harder.** *"A spiral
root that is comfortably Level 1 on a 737 becomes Level 3 on a 1.6 m model at the same
non-dimensional root."*

| Dihedral | ratio \|C_lβ·C_nr\| / \|C_lr·C_nβ\| | Result |
|---|---|---|
| 0° | 0.11 | unstable (badly) |
| 4° | 0.68 | unstable |
| 6° | 0.97 | neutral |
| **8°** | **1.25** | **stable** |

*"Neutral spiral needs ~6–7° dihedral. RC trainers are built with 5–10°. That is not a
coincidence — it is this equation."* (C172: 1.7°.) The RC expert confirms the practice
independently: Lennon's **Spiral Stability Margin** — CG-to-CLA as % of VTMA — is
tabulated **22 % super stable / 25 % good / 28 % neutral / 30 % mild instability / ≥33 %
very unstable**, with a flight test (bank 15–20°, neutralise, recover within 270° of the
turning circle); RC-Network names *Spiralsturz* as a known failure mode. **Two independent
authorities, one theoretical and one from field practice, converge on the same mode.**

**Why not ASB for the gated modes — the one place "prefer AeroSandbox" does not hold.**
ASB 4.2.9's `get_modes` (`aerosandbox/dynamics/flight_dynamics/airplane.py:7`) computes
**approximate, decoupled analytic modes** from Drela *FVA* Eq. 9.55–9.68, using **only
`Ixx`, `Iyy`, `Izz`** (`:19-21`) — no `Ixz`, no full A/B matrix, no apparent mass. **Its
own test fixture concedes the limit:** `"spiral": -0.0573017,  # Too small, get_modes says
-0.17` (`:196`) — roughly a **3× error, on the spiral**, precisely the mode that matters
here. AVL `MODE` gives exact eigenvalues of a full 12-state A matrix with B control matrix
(`avl_doc.txt:2284-2310`), including `Ixz` cross-coupling and apparent mass. **If the
gated modes are ever built, they are an ADR 0003 exception case and belong in AVL, not
ASB.**

**The precondition is satisfiable (premise ⑧).** `component_tree` carries
`pos_x/pos_y/pos_z` and per-node mass (`app/models/component_tree.py:49-61`), so inertias
including `Ixz` are computable today by Sadraey's §11.7 method. Nothing computes them. The
gate is real, not a euphemism for "never".

**`.run` adds almost nothing.** Its contents are keystroke-reachable except the products
of inertia (which `.mass` also supplies) and `heading`, which matters only for animation
and banked cases. Its real value for a headless service is deterministic, replayable
multi-case batches without driving a TTY. Two cautions if ever adopted: values can be
**stale** if the case was not converged before writing (fix: `XX` before `S`,
`avl_doc.txt:2053-2072`), and mass-derived values go stale if the `.mass` file changed
(fix: `MSET`, `:2090-2092`).

## Dissent recorded

**RC practice and scholz appear to disagree on dutch roll — the disagreement dissolves on
inspection.** The RC expert reports dutch roll as **the named dynamic failure mode**:
Lennon Ch. 9 states both extremes verbatim (*"Too much dihedral, too little vertical tail →
Dutch roll … Large vertical tail, little or no dihedral → sideslip resisted strongly by
the tail, producing a killer spiral"*), with a case study (the Snowy Owl, cured by
**doubling the dorsal fin area**). Scholz computes it passing Level 1 by 1.4–12×. Both are
right: what RC practice calls "dutch roll" is a **dihedral-versus-fin geometric balance**,
fixed geometrically and never modally — *"set dihedral first (high wing 2°, mid 3°, low
4°), then size the fin to the CLA target."* It is a static-geometry relation wearing a
dynamic mode's name. **Consequence for scope: ship the balance check, not the eigenvalue.**

**The RC expert dissents from a "static-only" boundary on two grounds scholz does not
raise.** (i) *"Don't ship 'static-only' while silently owning lateral-directional"* — if
the tool sizes fins and accepts dihedral it is already in that business; the minimum honest
deliverable is the **SSM / CLA check**, computable from geometry with no dynamics solver.
(ii) *"'No dynamic modes' is fine; 'no phugoid guidance' is not"* — the phugoid is **how RC
pilots find the CG** (dive 30–45°, release elevator; abrupt recovery and excessive climb =
CG too far forward). *"If the tool emits a first-flight CG, it should emit the
dive-and-release test and how to read it, or the number ships without its calibration
procedure."*

**Scholz flags a boundary case inside our own scope.** ζ_ph ≈ 1/(√2·L/D), so a draggy 3 kg
sport model at L/D = 8 gets ζ = 0.088, but **a 15 kg high-aspect-ratio soaring UAV at
L/D = 25 gets ζ = 0.028 — fails Level 1.** *"The phugoid is not universally irrelevant
across 0.5–15 kg; it is irrelevant for draggy airframes and marginal for clean ones."*

**Scholz flags a marginal decoupling assumption.** Sadraey requires ω_ph/ω_sp < 0.1 for
clean longitudinal decoupling; ours is **0.121**, *above* the limit (C172 0.056, 737
0.040). Root cause: ω_ph = √2g/U depends on **g, which does not scale**. Within the
factor-2 `Iyy` uncertainty, but *"you should not assume the two longitudinal modes decouple
at this scale — check it."*

**Rider carried into the decision.** Never present a MIL-F-8785C Level verdict at this
scale without stating inline that these are human-pilot-in-the-loop criteria for Class I
aircraft, whose class floor (m_TO < 6000 kg, Table 12.5) is **2000× our mass**, and that
our short-period (7.4 rad/s) and dutch-roll (5.0 rad/s) modes sit **above human pilot
bandwidth**. Under ADR 0023 that is exactly the transport-literature import the ADR forbids.

## Open premises

- **Whether any user needs spiral *time-to-double*, or whether the sign plus a dihedral
  recommendation suffices.** A product question, not an engineering one.
- **Whether the component tree is populated in practice.** The schema supports positions
  and masses; whether real aeroplanes have them filled in was not queried.
- **Whether any target aircraft has a UAV autopilot.** Scholz's short-period conclusion
  *inverts* if so.

---

# ④ Sub-question — the live strip-force path takes the index map but not the sign map

**Status: OPEN. Must be resolved before `build_yduplicate_sign_map` is deleted.**

`build_yduplicate_sign_map` is reachable only from the now-deleted artefact service, so
the live strip-force path takes the **index** map but not the **sign** map. This section
records what was established from the AVL source and what genuinely remains open.

## What was established from the source

**AVL's mirror sign convention — ✅ verified in-repo, by direct reading of `Avl/src/`,
not inferred.**

`Avl/src/amake.f:753-758`, verbatim comment:

> `C--- Note hinge axis is flipped to reverse the Y component of the hinge`
> `C    vector.   This means that deflections need to be reversed for image`
> `C    surfaces.`
> `C--- Image flag reversed (set to -IMAGS) for imaged surfaces`
> `      IMAGS(NNI) = -IMAGS(NN)`

`Avl/src/amake.f:772-774`, verbatim:

> `C--- Create image strips, to maintain the same sense of positive GAMMA`
> `C    these have the 1 and 2 strip edges reversed (i.e. root is edge 2,`
> `C    not edge 1 as for a strip with IMAGS=1`

**And AVL applies that flag itself, before printing.** `Avl/src/aero.f:915-923`:

```fortran
DELX = RLE2(1,J) - RLE1(1,J)
DELY = RLE2(2,J) - RLE1(2,J)
DELZ = RLE2(3,J) - RLE1(3,J)
IF(IMAGS(NSURFS(J)).LT.0) THEN
 DELX = -DELX
 DELY = -DELY
 DELZ = -DELZ
ENDIF
```

**Three conclusions follow, and they are established, not inferred:**

1. **`SgnDup` is an *input-side* declaration, not an output correction.** It is the
   seventh field on the `CONTROL` line of the geometry file
   (`app/avl/geometry.py:72,79,83`), consumed when AVL *reads* the file. The docstring of
   `build_yduplicate_sign_map` itself says so (`avl_strip_forces.py:174-182`). So "the
   live path takes the index map but not the sign map" compares two things that are not
   counterparts: the index map is an output-decoding concern, `SgnDup` is an input
   declaration.
2. **No per-surface output sign correction is needed.** AVL consumes `IMAGS` internally
   wherever it matters — strip `cm_LE` direction (`aero.f:919-923`, quoted above), the
   surface hinge/LE moment reference point (`aero.f:1063-1071`), root/tip identification
   in the `VM` shear-bending output (`getvm.f:88`). `CLsurf/CDsurf/CYsurf/Clsurf/Cmsurf/
   Cnsurf` and strip `cl/cd/cm` arrive already in the aircraft frame with correct sign.
3. **Mirrored strip forces are not summed with a wrong sign into spar loads, because they
   are not summed at all.** `compute_spanwise_loads` (`app/services/spanwise_loads.py:134-144`)
   partitions strips by the sign of `Yle`, sorts each half outboard-first, and integrates
   the two halves **separately** into `root_bending_moment_Nm_starboard` and `..._port`.
   `_surface_to_stations` (`analysis_service.py:2199-2213`) then sizes on
   `max(|M_sb|, |M_pt|)`. **There is no summation path across the mirror.** (This is also
   the structural reason scholz's "left/right mirroring" hazard is a no-op on symmetric
   cases, reached from the other side.)

**A further finding: the dead map is not merely redundant, it is wrong.** The live
`SgnDup` producer is the gh-772 `control_surface_mixing.axes_for_xsec`
(`control_surface_mixing.py:108-131`), written into every emitted `CONTROL` at
`avl_geometry_service.py:138`. For a **dual-role** surface — elevon, flaperon,
ruddervator — it emits **two** `CONTROL` variables under distinct names, primary with
`sgn_dup=+1.0` and secondary with `sgn_dup=−1.0`. The dead
`build_yduplicate_sign_map` walks the **ASB** airplane and keys by `cs.name`, deriving
**one** sign per name from `cs.symmetric` (`avl_strip_forces.py:184-193`) — but in the ASB
representation a dual-role surface is a *single* control surface, since the mixing names
exist only inside the AVL builder. **It would produce one sign for a control AVL needs as
two with opposite signs.** It encodes a pre-gh-772 assumption, and is the pattern ADR 0021
cites as decisive in `Q-CT-3`: *"a latent 8× error waiting for its first caller."*

## What remains genuinely open

1. **Whether any dual-role surface has ever been exercised through the AVL path.** The
   dead map's error is latent; deleting it is safe, but the *live* path's dual-role
   handling has no test asserting the two-controls-opposite-signs behaviour survives.
   This sits on the same boundary as open bug **#955** (control-surface naming
   divergence), and should be resolved together with it.
2. **The global axis-orientation sign is unasserted.** ✅ **verified in-repo:** the sign
   toggle that *does* apply to AVL output is **global, not per-surface** —
   `Avl/src/aoutput.f:1669-1675`:

   ```fortran
   IF(LSA) THEN
    SATYPE = 'Standard axis orientation,  X fwd, Z down'
    DIR = -1.0
   ELSE
    SATYPE = 'Geometric axis orientation,  X aft, Z up  '
    DIR =  1.0
   ENDIF
   ```

   and `DIR` multiplies **`Cn` and `Cr` (roll) only** on output — `aoutput.f:171`:
   `DIR*CNSURF(N), DIR*CRSURF(N)`. It is printed as a text line at the head of every
   `FN`/`FS`/`FB` block, and `avl-advisor`'s instruction is explicit: **"Parse that
   line."** This project neither sets nor parses it (no match in
   `app/services/avl_runner.py`). Safe today, because `LSA` keeps its default and the
   project never issues the `O`ptions command — but it is an **unasserted assumption
   sitting on exactly the two coefficients** (`Cl`, `Cn`) that the `Q-AV-2`
   lateral-directional work depends on, and a user-edited `.avl` is a text file.
   **Whether AVL can pick up an axis-orientation setting from anywhere other than the
   interactive `O` menu was not determined — open premise, not inferred.**

**Recommended resolution before deletion:** add the one-line assertion on the
axis-orientation header in `parse_strip_forces_output`, and a test that a dual-role
surface emits two `CONTROL` blocks with opposite `SgnDup`. Both are small, and together
they close item 1 and item 2 without blocking the Q-AV-3 deletion of the artefact service
itself. A larger option exists and is **not** recommended as a rider: switching the parser
to AVL's `MRF` machine-readable output (`Avl/src/aoper.f:103`), which is self-describing
and full precision where the current text format is `F8.4` — a real precision loss at RC
scale, but it rewrites a working state machine and its byte-compatible VLM twin
(`vlm_strip_forces`, per BR-AV17), so it belongs in its own ticket.

---

## Summary of the four decisions

| | Decision (2026-08-15) | ADR discharged |
|---|---|---|
| `Q-AV-2` | **No `BODY`, ever.** AVL stays lifting surfaces only; AeroSandbox is sole authority for `Cnb`. The primer's crossed-`SURFACE`-with-`NOWAKE` alternative rejected too — a lifting-surface substitute is calibration, not physics, and does not track with fineness ratio | 0022 (one producer), 0021 (`AvlBody` deleted), 0019 (field named for what it is) |
| `Q-AV-3` | **Parse, don't cache.** Artefact service deleted as complete-but-unreachable; `get_control_surface_index_map` stays — it is live on the trim path | 0021 rule 1 |
| `Q-AV-4` | **A successful regenerate clears `is_dirty`** (behaviour change — today the row is deleted). The escape hatch stops silently expiring | 0020 (no undeclared clamp on the span rescale) |
| `Q-AV-8` | **Deferred behind a precondition.** No `.mass`/`.run`; ship the spiral criterion and phugoid (both inertia-free); the other three modes gated on a real per-component mass model — refuse rather than guess | 0023 (no unchecked MIL-spec import) |
| **④** | **OPEN.** Mirror sign convention established from source (AVL applies `IMAGS` itself; no summation across the mirror). Two residual items must close before `build_yduplicate_sign_map` is deleted | — |

**Items surfaced that are outside these questions and want their own tickets:**

1. **Two independent producers of the AVL d-index** (premise ④) — an ADR 0022 instance
   that BR-AV13 currently mis-describes as safe.
2. **The `n_max` / `g_limit` divergence.** Sadraey Table 10.9 gives RC `n_max = 1.5–2`;
   scholz **explicitly dissents from its own primary source** (*"an input to a
   weight-estimation regression for a docile model, not a manoeuvre envelope"*) and uses
   `n_max = 4, n_ult = 6`; RC practice has **no n-limit table at all**, using a lift margin
   instead (size so high-g `C_L` sits at 0.65–0.75 of `C_L,max`). The shipped defaults —
   `safety_factor_j = 1.5` and `_G_LIMIT_DEFAULT = 3.0` (`analysis_service.py:2099`) — sit
   at the bottom of all three views. **A 3× spread on every spar dimension.**
3. **`y_root ≥ 0` invariant for `YDUPLICATE` surfaces** — two live `Wing` rows at
   `y_root = −0.205 m` self-overlap by 0.41 m when mirrored, corrupting `Sref`, `CDi` and
   `e`; possibly a second data defect in the same rows (4 m chord).
4. **The silent span-rescale clamp** at `section_thickness.py:73`.
5. **The broken `avl-advisor` skill packaging.**
