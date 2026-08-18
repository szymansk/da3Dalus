---
name: vtail-cos-square-correction
symbol: cos²(γ)
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# V-tail cos² correction

**Definition.** Reduction factor applied to a flat-tail analytic Cm_δe to account for V-tail dihedral.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cos2 = math.cos(math.radians(dihedral_deg)) ** 2
return cm_delta_e_flat * cos2
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:161` — `_apply_vtail_cos_square_correction`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `NONE — grep over app/, cad_designer/, scripts/ finds only the definition (line 143) and a docstring mention (line 135)`

**Source.** 🟡 PARTIAL

> The V-tail decomposition principle is standard: a V-tail panel at dihedral γ contributes its normal force to pitch as cos γ and, because the effective area seen in the pitch plane also scales as cos γ, the pitch effectiveness scales as cos²γ. Sadraey §6.7 covers V-tail ('other tail geometries') and §6.2.2 the pitch/yaw decomposition, but no consulted source states the cos²γ correction as an equation with a number.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
—
```

**⚠️ Divergence from the source.** Cannot assess divergence: the analytic flat-tail stub formula this function exists to correct (Cm_δe_stub = a_t·(S_H/S_w)·(l_H/MAC)·cos²γ, named in the module header at elevator_authority_service.py:35) is never implemented anywhere in the code. The function has no call site (grep over app/, cad_designer/, scripts/ finds only the definition at line 143 and the docstring mention at :135) — complete but unreachable (ADR 0021). Note also that tail_sizing_service hardcodes is_v_tail = False (:417), so V-tails are never even detected.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** DEAD CODE: the analytic stub formula it exists to correct (Cm_δe_stub) is documented in the module header (line 35) but never implemented anywhere — _build_stub_result uses the 0.30·MAC shortcut instead. Complete but unreachable (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Amendment B4: This correction is ONLY for the analytic flat-tail formula:
  Cm_δe_stub = a_t·(S_H/S_w)·(l_H/MAC) · cos²(γ)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
