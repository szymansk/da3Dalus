# ADR 0008 — A control surface's *role* decomposes into control *axes*

- **Status:** Accepted — in force, with a known open bug (#955)
- **Decided:** 2026-05-30 (epic gh-772, commit `12d5c0cd`)
- **Deciders:** Marc Szymanski (maintainer), after AVL / AeroSandbox / flight-dynamics expert critique
- **Confidence:** 🟢 CONFIRMED (commit body, module docstring, code)

## Context

Every trailing-edge device mapped to **one** AVL control variable plus a
`symmetric` boolean. That works for an aileron on a conventional wing and breaks
for every mixed surface — a ruddervator has no pitch-vs-yaw separation, an elevon
no pitch-vs-roll, a flaperon no lift-vs-roll — and `decompose_dual_role` reported
`differential_throw = 0` **always**, because it required ≥2 same-role surfaces,
never true for a mirrored wing. RC and UAV aircraft are exactly where mixed
surfaces are the norm. Second, sharp constraint: **AVL silently collapses
identically-named `CONTROL` variables into a single degree of freedom** (avl_doc
778–789), so a naive naming scheme couples unrelated surfaces with no error.

## Decision

**Model the physical *role* separately from the aerodynamic *axes* it acts on, and
make the decomposition a single shared module.**
`app/services/control_surface_mixing.py` is the one source of truth, consumed by
the AVL geometry builder, the AeroSandbox airplane builder and trim enrichment.

```
_DUAL_ROLE_AXES = { elevon:      (pitch, roll),
                    flaperon:    (lift,  roll),
                    ruddervator: (pitch, yaw)  }

PRIMARY_AXES   = {pitch, lift}     # symmetric      SgnDup = +1
SECONDARY_AXES = {roll,  yaw}      # antisymmetric  SgnDup = −1

name = f"[{role}]{axis}_{sanitize(wing_key)}_{xsec_index}"
       e.g. "[ruddervator]pitch_htail_1"
```

1. **A dual-role surface emits two control variables on the same section.** AVL
   sums multiple `CONTROL` lines per section — the native way to express mixing.
2. **Primary axis:** `SgnDup = +1`, gain `mix_gain_primary`, `symmetric = True`,
   baseline = the surface's deflection. **Secondary axis:** `SgnDup = −1`, gain
   `mix_gain_secondary`, `symmetric = False`, baseline **`0.0`** — so the
   single-axis AeroBuildup fallback never receives a roll/yaw deflection.
3. **`SgnDup` is a sign flag, never a differential magnitude.** No differential is
   expressed in geometry.
4. **`differential_ratio` is a reporting-only kinematic**, applied *after* trim to
   reconstruct left/right display angles. It never alters the aero or trim
   solution, and scales only the up-going side, never `d_sym`.
5. **Names must be globally unique**, asserted by `assert_unique_control_names`
   across surfaces (duplication *within* one surface is legitimate panel
   replication and is deduped separately).
6. **Mixing fields are role-gated on write:** `differential_ratio ≠ 1.0` only for
   `{aileron, elevon, flaperon, ruddervator}`; `mix_gain_secondary ≠ 1.0` only for
   `{elevon, flaperon, ruddervator}`; compared with
   `math.isclose(rel_tol=1e-9, abs_tol=1e-9)`; a `None` role (partial patch) skips
   the check.
7. **Roles drive capability gating elsewhere.** `PITCH_ROLES`, `ROLL_ROLES`,
   `YAW_ROLES`, `FLAP_ROLES` decide which operating-point targets are generated
   and which control the retrim service searches for.

## Consequences

- V-tails, flying wings and flaperon aircraft trim correctly for the first time;
  the role→axis table is data, so adding a mixed role is one line visible to all
  three consumers; `_ROLE_TAG_RE` recovers physical intent from a control name.
- 🔴 **Open bug #955 — the naming change was not propagated everywhere.** Three
  consumers still key on the **raw TED name from the DB** while `controls` carries
  **mixing names**, so on a dual-role aircraft the reserve/authority ratio uses a
  hard-coded **±25°** instead of the real limit, the gh-863 union injects a
  **phantom surface at 0°** no solver trims, and
  `stability_service._find_trim_elevator`'s substring match on `"elevator"` can
  never match `[ruddervator]pitch_…`. Resolved by
  [ADR 0022](0022-one-authority-per-user-facing-quantity.md):
  `control_surface_mixing` owns a resolver trim, retrim and stability are
  **required** to call.
- **The secondary axis is dead on the default solver** — AeroBuildup models a single
  axis, so mixed surfaces get their roll/yaw contribution only on the AVL path
  ([ADR 0003](0003-aerosandbox-default-avl-exception.md)).
- 🔴 The OpenVSP importer's `SS_CONTROL → TrailingEdgeDevice` post-pass is **never
  registered in production**, so imported aircraft arrive with no control surfaces
  (wired under
  [ADR 0021](0021-complete-but-unreachable-code-is-deleted-by-default.md)).

**Rejected:** encoding differential as `SgnDup ≠ ±1` — *"`SgnDup` stays ±1 (it is a
sign flag, not a throw magnitude)"*.

## Related

[ADR 0003](0003-aerosandbox-default-avl-exception.md) ·
[ADR 0022](0022-one-authority-per-user-facing-quantity.md) ·
domain rules BR-9 … BR-13, BR-21, BR-22 · [`../domain.md`](../domain.md) gap G-4 ·
[`../questions.md`](../questions.md) §Q-WD-1.
Evidence: commit `12d5c0cd` (gh-772);
`app/services/control_surface_mixing.py:14-164`;
`app/services/trim_enrichment_service.py:72-118` (the #955 divergence).
