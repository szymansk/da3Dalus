---
name: ss-s-ref
symbol: S_ref
kind: quantity
unit: m^2
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Wing reference area (solution space)

**Definition.** Wing area read from the aeroplane's gh-924 assumption_computation_context, or a minimal-RC fallback with a warning.

**Formula — as the code writes it.**

```
s_ref_m2: float | None = ctx.get("s_ref_m2") ; if s_ref_m2 is None or s_ref_m2 <= 0: warnings.append(...) ; s_ref_m2 = 0.25  # minimal RC plane fallback
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:278` — `compute_solution_space`

**Consumed by.**

- in this graph: [[ss-lift-coefficient|Level-flight lift coefficient]] · [[ss-p-aero|Aerodynamic power]] · [[ss-p-aero-cruise|Aerodynamic power at cruise]] · [[ss-p-aero-top|Aerodynamic power at top speed]]
- outside it: `app/services/powertrain_solution_space_service.py:349` · `app/services/powertrain_solution_space_service.py:350`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source prescribes a default wing area. The RC vault derives S from mass and target wing loading (rcplanedesigner 'Wing area / wing loading as a practical relation'; Lennon Ch. 18 wing-loading nomograph, entered with oz/ft^2 and a level-flight C_L of 0.2-0.3). The 0.25 m^2 fallback is unattributed, and it disagrees by a factor of 2 with the sizing service's 0.5 m^2 for the same quantity.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Fallback 0.25 m2 contradicts the sizing service's fallback of 0.5 m2 for the identical quantity (powertrain_sizing_service.py:47) — a factor-of-2 disagreement between two services the same user sees.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# minimal RC plane fallback — NO_SOURCE_FOUND for 0.25`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
