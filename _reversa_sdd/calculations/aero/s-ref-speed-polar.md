---
name: s-ref-speed-polar
symbol: S_ref
kind: quantity
unit: m²
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Reference wing area

**Definition.** Wing reference area taken off the built AeroSandbox airplane.

**Formula — as the code writes it.**

```
s_ref = float(getattr(asb_airplane, "s_ref", 0.0) or 0.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:624` — `_build_speed_polar`

**Consumed by.**

- in this graph: [[speed-polar-v|Glide forward speed]] · [[v-stall|Stall speed]]
- outside it: `SpeedPolar.s_ref`

**Source.** 🟢 SOURCED

> Anderson 6e §1.5 ('S is a reference area chosen to match the body shape … for an airplane wing, S is the planform area; the choice is arbitrary but must be clearly stated'); AeroSandbox tutorial 04-01 'Basic Aircraft Geometry' (Airplane data structure)
>
> — via `aerosandbox-expert, aerodynamics-expert`

**The source states it as.**

```
C_L = L/(q_inf·S); ASB: 's_ref, c_ref, b_ref … If not specified, they are auto-computed from the FIRST wing.'
```

**⚠️ Divergence from the source.** The ASB doc explicitly states s_ref defaults to the FIRST wing, not the main wing. This confirms the recorded VSPAERO benchmark finding F1: for a tail-first geometry every coefficient is normalised by the tail area. Additionally s_ref→0.0 collapses the polar to empty curves with no warning.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Falls back to 0.0, which makes valid_geometry False and returns empty curves with no warning; memory records asb s_ref being taken from the first wing rather than the main wing (VSPAERO benchmark finding F1).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
