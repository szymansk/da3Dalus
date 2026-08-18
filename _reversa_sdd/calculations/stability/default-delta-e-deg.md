---
name: default-delta-e-deg
symbol: δe_max
kind: constant
unit: deg
cluster: stability
user_visible: false
source_status: SOURCED
---

# Default maximum elevator deflection

**Definition.** Maximum elevator deflection assumed when the TED does not declare negative_deflection_deg.

**Value.** `25.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:86` — `_DEFAULT_DELTA_E_DEG`

**Consumed by.**

- in this graph: [[delta-e-max-rad|Maximum elevator deflection (radians)]]
- outside it: `app/services/elevator_authority_service.py:122`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.5 (Elevator Design Procedure), step 4: "Establish the maximum elevator deflection to prevent flow separation (typically 25°)." The worked example (§12.5.5) uses δ_Emax,up = −25°. Related bound: §12.5.4 — "If the required δ_E exceeds about 30°, the elevator must be enlarged or the tail arm extended to avoid flow separation over the horizontal tail."
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
δ_E,max ≈ 25° (flow-separation limit); hard ceiling ~30° (Sadraey §12.5.4, §12.5.5 step 4)
```

**⚠️ Divergence from the source.** The value matches the source exactly. What diverges is its use: Sadraey's 25° is an *aerodynamic* separation limit that the designer must not exceed, whereas the code uses it as a fallback for a *mechanical* hinge limit. Real TEDs in this app's own database carry 20–35°, so the fallback both under- and over-states real hardware.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey's 25° comes from transport/GA elevator design (worked example: 20,000 kg twin-jet). RC servo-driven surfaces routinely run larger throws — the app's own DB has 35°/35° elevators. No RC/UAV-scale validation is recorded (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Same 25.0 magic value is independently hardcoded in trim_enrichment_service.py:79 and :413 as the deflection-limit fallback — two unrelated producers of the same assumed mechanical limit, no source for either. Real DB TEDs carry 20–35°.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `#: Fallback δe_max when negative_deflection_deg is not set in the model.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
