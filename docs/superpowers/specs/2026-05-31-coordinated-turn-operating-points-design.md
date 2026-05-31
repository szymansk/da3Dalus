# Design Spec — Coordinated Turn Operating Points (gh-806)

**Status:** approved (brainstorm), pending implementation plan
**Date:** 2026-05-31
**Issue:** #806
**Relationship:** Prerequisite for the aileron-differential-coordination recommendation
(follow-up spec, part of epic #772). That follow-up uses these turn conditions to
recommend the differential that drives aileron-induced `Cn ≈ 0` during roll-in.

---

## 1. Problem

The only turn operating point today, `turn_n2`, is a simplified state: it raises the
load factor but sets **body rates `p = q = r = 0`** (see
`operating_point_generator_service._solve_trim_candidate_with_opti`, which hard-codes
`p=0, q=0, r=0`). It therefore does **not** model turn dynamics — the rate-induced
damping moments (`C_lr`, `C_nr`, `C_mq`) are absent, so the trimmed control deflections
are physically wrong for a real turn. There is also only **one** turn (2g ≈ 60° bank);
the standard bank angles 20° and 40° are missing.

## 2. Goal

1. The auto-generated **default operating-point set** contains correctly-computed
   coordinated turns at **20° / 40° / 60°** bank — standard conditions the user gets
   without configuring anything.
2. An **"Add Turn OP"** capability lets the user add a coordinated turn at **any other
   bank angle** (e.g. 30°) through the "add OP" flow, specifying only the bank angle
   (speed/altitude default sensibly).

Both share one turn-kinematics + rate-aware-trim core.

## 3. Physics (validated via `/aircraft-design-scholz`, Sadraey Ch. 6 & 12)

Steady coordinated **level** turn at bank angle φ and true airspeed V (no sideslip,
no climb). Convention: **right turn, φ > 0** (mirror lateral signs for a left turn).

Bank-only quantities (independent of V):

| Quantity | Formula | 20° | 40° | 60° |
|---|---|---|---|---|
| Load factor | `n = 1/cos φ` | 1.064 | 1.305 | 2.000 |
| Stall-speed factor | `√n` | 1.032 | 1.142 | 1.414 |

Speed-dependent quantities (computed at the OP's V): turn rate `ψ̇ = g·tan φ / V`
(rad/s), turn radius `R = V² / (g·tan φ)`, required lift `C_L,turn = n · C_L,1g`.

**Body-axis angular rates** (project the Earth-vertical rotation ψ̇ onto body axes
through attitude θ; bank held constant ⇒ φ̇ = 0):

```
p = −ψ̇ · sin θ      (second-order)
q =  ψ̇ · sin φ      (nose-up pitch rate that sustains n > 1)
r =  ψ̇ · cos φ      (dominant; sets the turn)
```

**v1 simplification (resolves the α/rate coupling):** the rates depend on θ ≈ α, but α
is itself a trim variable. To avoid an outer iteration, v1 computes the rates with
**θ = 0**, giving `p = 0`, `q = ψ̇·sin φ`, `r = ψ̇·cos φ`. The Scholz reference confirms
the `p` term is second-order and negligible for level turns up to ~60°. The
`turn_kinematics(..., alpha_deg=0.0)` parameter exists so a later refinement can pass the
solved α and recompute (a single fixed-point pass) without an interface change — out of
scope for v1. Sanity check: `√(q² + r²) = ψ̇`.

**Reduced rates / solver convention.** `asb.OperatingPoint(p, q, r)` takes **dimensional**
body rates (rad/s); AeroBuildup non-dimensionalizes internally. The AVL path
(`avl_runner`) already converts via full span `pb/(2V)`, `qc̄/(2V)`, `rb/(2V)` (reference
length **b** for roll/yaw, **c̄** for pitch). So we pass dimensional `p, q, r` (rad/s) and
rely on the existing pipeline — no manual non-dimensionalization.

**Steady-turn trim balance** (β = 0, p ≈ 0). The surviving rate terms the trim must
absorb are `C_lr·(rb/2V)` in roll (→ overbanking, needs a small *hold* aileron) and
`C_nr·(rb/2V)` in yaw (→ needs a **pro-turn** rudder), plus `C_mq·(qc̄/2V)` in pitch.

**Physical effects captured / flagged:**
- *Overbanking tendency* — surfaces as the aileron deflection required to hold bank; warn
  near the aileron limit.
- *Coordinating rudder* — a pro-turn (same-direction) rudder deflection is genuinely
  required; it consumes rudder authority (budget it; warn near limit).
- *Stall in turn* — `V_stall,turn = V_stall,1g · √n`. Flag the OP infeasible if
  `C_L,turn = n·C_L,1g > C_L,max`, i.e. `V < vs_clean·√n`.
- *Adverse yaw is NOT modeled here* — it is a **roll-in transient** (needs deflected
  ailerons AND nonzero roll rate p); the steady turn has p ≈ 0. It belongs to the
  differential follow-up spec, not this one.

## 4. Architecture

### 4.1 Shared core (new, pure + unit-testable)

`turn_kinematics(bank_deg: float, velocity: float, alpha_deg: float = 0.0) -> TurnKinematics`
returns `{n, psi_dot, p, q, r, cl_factor}` (rates in rad/s). Pure function, no I/O.
Lives in a small module (e.g. `app/services/turn_kinematics.py`).

### 4.2 Rate-aware turn trim (modify existing)

Extend `_solve_trim_candidate_with_opti` (`operating_point_generator_service.py`):
- A turn target dict carries `bank_deg`; from it compute `n_target = 1/cos φ` and the
  body rates via `turn_kinematics`.
- Build `op = asb.OperatingPoint(velocity, alpha, beta=0, p=p, q=q, r=r, atmosphere=…)`
  with the computed rates instead of the hard-coded zeros.
- Keep the existing optimizer variables (α + pitch + roll + yaw controls) and the
  `Cm² + CY² + (Cl² + Cn²)` objective; the nonzero r now produces `C_lr`/`C_nr` so the
  trimmed aileron/rudder are physically meaningful.

This trim helper is the single place where rates enter; both consumers call through it.

### 4.3 Consumer A — default set (modify)

In the default-target list (`operating_point_generator_service`, ~the `turn_n2` entry),
replace the single `turn_n2` dict with **three** dicts `turn_20`, `turn_40`, `turn_60`
(each `config: clean`, the existing turn speed `max(cruise, 1.3·vs_clean)`,
`beta_target_deg: 0`, `bank_deg: 20|40|60`, `n_target = 1/cos φ`). Update
`_required_capabilities_for_target` / `_validate_target_capability` to treat the three
turn names like `turn_n2` (needs roll **or** yaw control). Update `ANALYSIS_GOALS` and
the result-summary map in `trim_enrichment_service` (`turn_n2` → `turn_20/40/60`).

### 4.4 Consumer B — Add-Turn endpoint (new)

`POST /aeroplanes/{uuid}/operating-points/add-turn`
Request: `{ bank_angle_deg: float, velocity?: float, altitude?: float, name?: str }`.
- Defaults: `velocity = max(cruise, 1.3·vs_clean)`, `altitude = 0`,
  `name = f"turn_{round(bank_angle_deg)}"`.
- Builds a one-element turn target, runs the rate-aware turn trim, computes enrichment,
  **persists** the resulting OP via the existing OP store, returns the stored OP
  (+ enrichment). Mirrors the existing `avl-trim` / `aerobuildup-trim` endpoints
  (compute → persist → return).
- Validation: `0 < bank_angle_deg < 90`; `velocity > 0`.

### 4.5 Feasibility guard

Before/while trimming, if `V < vs_clean·√n` (equivalently `C_L,turn > C_L,max`), mark the
OP `LIMIT_REACHED` (status) and attach a `stability`/`authority` design warning
("stall in turn at φ°: required C_L exceeds C_L,max"). Surface, don't silently clip
(project design-error-feedback rule).

## 5. Data / schema

- A turn target gains a `bank_deg` field (internal target dict; no DB schema change for
  the target list itself).
- Add-Turn request/response: a small Pydantic request schema; response is the existing
  `StoredOperatingPointRead`.
- Stored OP already carries `velocity, alpha, beta, p, q, r, altitude, control_deflections,
  trim_enrichment` — the turn OP populates `p, q, r` (previously always 0 for turns). No
  DB migration required.

## 6. Testing

**Unit (fast):**
- `turn_kinematics`: n for 20/40/60 (1.064/1.305/2.0); `√(q²+r²)=ψ̇`; `ψ̇=g·tanφ/V`;
  p≈0 at small θ; monotonic r(φ).
- Feasibility guard: low V at 60° → flagged `LIMIT_REACHED` + warning; adequate V → not.
- Add-Turn request validation (bank bounds, default fill).

**Integration:**
- `generate-default` produces `turn_20/turn_40/turn_60`, each trimmed (converged), each
  with **r ≠ 0**; 60° reproduces the prior 2g behavior within tolerance.
- Add-Turn endpoint creates e.g. `turn_30`, persisted, retrievable, with proper rates.
- Plausibility: in the steady turn the aileron is a small hold deflection and the rudder
  is pro-turn (same sign as the turn); both within limits for a normal config.

**Slow smoke:** turn generation across the existing smoke aircraft configs doesn't crash.

## 7. Scope boundary (deliberately NOT in this spec)

- **No aileron-differential recommendation** — separate follow-up spec (epic #772).
- **No roll-in transient / adverse-yaw modeling** — steady turn only (p ≈ 0).
- **No generic "add OP by intent"** for other condition types (climb, stall, …) — only
  the turn add-flow (YAGNI; the pattern can be generalized later if needed).
- **No configurable default bank angles** — the default set is fixed at 20/40/60; other
  banks go through Add-Turn.
- **Left-turn variants** are not separately generated (symmetric aircraft → mirror).
