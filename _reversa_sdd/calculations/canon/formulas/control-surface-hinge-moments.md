---
canon: control-surface-hinge-moments
entry: formula
kind: procedure
tool: AVL
shape: law
status: approved
output: hinge-moment
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/approved
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  n_load: load-factor
  rho: air-density
  v: flight-speed
  delta: null
outputs: {h: hinge-moment}
applications:
  - id: aileron
    bind: {delta: aileron-deflection}
    when: has_aileron
  - id: elevator_up
    bind: {delta: elevator-deflection-up}
    when: has_elevator
  - id: elevator_down
    bind: {delta: elevator-deflection-down}
    when: has_elevator
  - id: rudder
    bind: {delta: rudder-deflection}
    when: has_rudder
  - id: flap_takeoff
    bind: {delta: flap-deflection-takeoff}
    when: has_flap
  - id: flap_landing
    bind: {delta: flap-deflection-landing}
    when: has_flap
---

# Hinge moment of every control surface at its role's deflection

**Canonical form**

```
for each applicable application (role r, deflection delta = the role's input):
  solve for alpha at V:   L = n * m * g               (AVL: A C CL,  CL = 2 n m g / (rho V^2 S_ref))
                          pitch NOT trimmed — only this role's surfaces are deflected, by delta
  every surface s acting in role r is its own AVL control at gain 1 (internal name; key `<wing>.<device>[_left|_right]`)
  C_hinge,s := AVL(airplane, V, alpha, delta).HM      (deflection sign per role: table below)
  H[s][r]   = q * S_ref * c_ref * C_hinge,s,      q = 0.5 * rho * V^2
hinge-moment = { s: { application id: H } }  — the union over the applicable applications
            (positive: aerodynamic moment in the +deflection sense, right-hand rule about the hinge vector)
```
**Produces** [[hinge-moment]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[load-factor]] · [[air-density]] · [[flight-speed]] · [[aileron-deflection]] · [[elevator-deflection-up]] · [[elevator-deflection-down]] · [[rudder-deflection]] · [[flap-deflection-takeoff]] · [[flap-deflection-landing]]

**Kind: a procedure — one AVL solution per role, read at every hinge.** Maintainer decisions
2026-10-19 (#1174): the construction side sizes servos from it. The output is **one quantity with one
value per control surface** (type `per_control_surface`), keyed by `<wing>.<device>[_left|_right]`
(Surface keys, below): left and right separate, twin fins separate; a dual-role surface gets one value per role. Every application
binds its role's existing deflection input and contributes the entries of its surfaces; the quantity is
the union of the applicable applications. A role without surfaces makes its application not
applicable (`when`); when no application applies, the quantity is not applicable (README `when` rule).
The operating point — speed and load factor — is the caller's: which point a servo is sized for (`V_D`,
`V_max`, full throw) is an evaluation decision (A10). `n_load` is not inert: it sets the lift the solve
balances and so the angle of attack, which enters the hinge moment through `C_hα`. No design load
factor and no safety factor is applied here.

**Roles by function.** A surface counts in the role it acts in: aileron — `aileron`, `flaperon`,
`elevon`; elevator — `elevator`, `elevon`, `ruddervator`; rudder — `rudder`, `ruddervator`; flap —
`flap`, `flaperon`. A dual-role surface is evaluated once per role, with only that role's deflection
applied. A stabilator (all-moving) has no hinge in AVL's sense and is not covered.

**Deflection sign per role.** The axes follow the geometry: a dual-role surface combines a symmetric
and an antisymmetric axis on one surface (`app/schemas/aeroplaneschema.py:42-48`). Positive is the
`+deflection` sense on each side as the per-side AVL model below orients it: for aileron, elevator
and flap surfaces trailing edge down on the right and on the left half alike; each side's `H` is
reported in that sense.

| role | deflection applied | dual-role surfaces in this role |
|---|---|---|
| aileron | antisymmetric: right `+δ_a`, left `−δ_a` (as [[aileron-deflection]] defines, ±δ_a) | elevon, flaperon — antisymmetric |
| elevator | symmetric: both sides `+δ_e` | elevon, ruddervator — symmetric |
| rudder | every fin `+δ_r` | ruddervator — antisymmetric |
| flap | symmetric: both sides `+δ_f` | flaperon — symmetric |

**Surface keys.** The output key of a surface is `<wing>.<device>[_left|_right]` (maintainer,
2026-10-19): the wing's name, which is required and unique; the device's `name` from the geometry —
derived exactly as the geometry format derives it when omitted (from `role` or `label`,
`TrailingEdgeDevice.name`); and `_left` / `_right` for a mirrored device, e.g.
`Seitenleitwerk_links.rudder`. Twin fins are separate devices. The key has no length limit. Two
surfaces with the same key are an invalid input (`invalid_input`). The keys are **not** tied to the
mixing names of #955.

AVL's `HM` gives one coefficient per **control name**, summing all surfaces that share it
(`aero.f:411-420`, `amake.f:545-549`), and a control name is `CHARACTER*16` (`DNAME`,
`Avl/src/AVL.INC:58`). The kernel therefore gives each surface its own control at gain 1 under a
short internal name (`c01`, `c02`, …) when it builds the AVL input, and maps each `HM` entry back to
the surface key. The internal name never appears in a result (ADR 0019). This is part of the
procedure, not an input.

**Per-side AVL model.** `YDUPLICATE` cannot give per-side values: the image surface keeps the same
control index, so `HM` sums both sides (`amake.f:812-822`), and AVL negates the hinge vector's
y-component and multiplies the image's deflection by `SgnDup` (`amake.f:863-865`, `avl_doc:755-757`).
The kernel therefore writes **every left half as its own explicit `SURFACE`**, without
`YDUPLICATE`, with its own internal control per device. Its sections run left → right like every
AVL surface (`avl_doc:615-625`), i.e. **tip → root** on a left half. The left hinge vector is
oriented so that `+δ` has the same physical sense as on the right — the mirror image of the right
side's sense, for aileron, elevator and flap trailing edge down (`+` rotation about the hinge vector by
the right-hand rule, `avl_doc:752-753`). Each side's `H` is reported in that sense, and the deflection
sign table above refers to it (aileron: the left half gets `−δ_a`, i.e. trailing edge up). This
AVL model differs on purpose from [[spanwise-loads]], which requires `YDUPLICATE` with the sections
root → tip so that `VM` integrates from the tip; the two procedures build separate AVL inputs.

**Pitch untrimmed, declared (ADR 0020).** α comes from `L = n·m·g` alone; no other control trims the
pitching moment (maintainer, 2026-10-19). The hinge moment is that of the deflected surface at that α,
not of a trimmed flight state.

**What AVL returns (avl-advisor).** `C_hinge` is referred to `S_ref·c_ref` (not to the surface's own
area and chord); positive is the aerodynamic moment in the +deflection sense (`avl_doc:752-753`); for
an elevator with hinge vector `(0,1,0)` + is trailing edge down, so a restoring load gives
`C_hinge < 0`. `H = q·S_ref·c_ref·C_hinge` holds because each surface is one control at gain 1. `HM`
excludes trailing-leg and viscous forces (`aero.f:621-640, 719-725`). A converged `X` run is required.
The moment reference `Xref` is the AVL file's reference point, a procedure detail: α comes from the
`C_L` constraint and there are no rates, so `Xref` only moves the reference of the overall pitching
moment and does not change a hinge moment — the CG is no input (ADR 0021). No pull-up pitch rate is
modelled.
The control surface must be resolved by the chordwise panels — best modelled as its own `SURFACE`
(`avl_doc:1110-1119`).

**The hinge moment as the sources define it.** `H = ½·ρ·V²·S_c·c̄_c·C_h` with the control surface's
own area and mean chord, `C_h = C_h0 + C_hα·α + C_hδ·δ` (Sadraey §12.7.1, Eq. 12.147–12.148). AVL's
`C_hinge` is the same moment referred to `S_ref·c_ref`; `H` is identical.

**Validity in the RC/UAV regime (ADR 0028), declared (ADR 0020).** Inviscid, steady, attached flow,
linear in δ (`amake.f:1173-1177`). Missing: boundary-layer displacement over the hinge (Anderson §17.2),
the real trailing-edge Kutta condition (§4.5), gap flow [no source in Anderson], separation behind
hinge or trailing edge (§1.10.2, §4.13) and laminar bubbles (§20.3.2). In attached flow the magnitude
is typically **over-estimated** [no source] — an upper estimate; under separation, at large deflection
(§5.5 "not valid for very large deflections"; beyond about 10–15° [no source]) or at chord Re below
7·10⁴ it is **unbounded**. A blunt trailing edge can reverse the hinge-moment slope (overbalance) [no
source]. Reliable as an estimate at chord Re ≳ 2·10⁵ [no source], degraded at 7·10⁴–2·10⁵ (the regime edges
3·10⁴, 7·10⁴ and 1·10⁶ come from ADR 0028; the 2·10⁵ edge has no source). Mach ≤ 0.3: no correction (§1.10.3). **It is not a servo torque requirement** —
that adds friction, linkage geometry and the evaluation's margins.

**Source.** 🟢 Sadraey §12.7.1, Eq. 12.147–12.148 (hinge moment); AVL user guide and source
(`avl_doc.txt:752-753`, `aero.f:411-420`, `amake.f:545-549`) for `HM`. 🔴 No source for the servo
sizing point — that is the evaluation's (A10).

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Relation and method** — which equation it solves, and by which named method
- [x] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [x] **Convergence** — the criterion, and what is returned and declared on failure
- [x] **Dimensions** — the check balances
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Preconditions** — every binding condition holds, or the violation is ticketed
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-10-25): the hinge moment of every control surface per role, one AVL
> solution per role at `L = n·m·g`, `H = q·S_ref·c_ref·C_hinge` (AVL normalises `HM` by the aircraft's
> reference area and chord), with the declared limits — an upper estimate in attached flow (inviscid),
> unbounded beyond about 10–15° deflection or below chord Re 7·10⁴, no servo sizing (lever ratios,
> linkage and safety factor belong to construction and evaluation, A10). AeroSandbox has no hinge
> moments, so AVL is the tool. The implementation checklist item holds vacuously: there is no aero_kernel
> formula yet.
