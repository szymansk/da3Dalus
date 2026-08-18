---
name: vlm-mach
symbol: mach
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: SOURCED
---

# Echoed Mach number

**Definition.** Operating-point Mach number echoed into the strip-forces result.

**Formula — as the code writes it.**

```
"mach": float(op_point.mach()),
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:317` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/services/analysis_service.py:_build_strip_forces_response`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5 (M = V/a); AeroSandbox docs_aero_3d.md ('VLM has no compressibility correction')
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
M = V_inf / a
```

**⚠️ Divergence from the source.** The value is echoed but the solver ignores it — ASB's VLM applies no Prandtl-Glauert correction (unlike AVL, avl_doc.txt L143-196). Harmless at RC/UAV speeds (M < 0.1) but the field implies a dependence that does not exist.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:317`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
