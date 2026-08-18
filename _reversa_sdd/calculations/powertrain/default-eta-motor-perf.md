---
name: default-eta-motor-perf
symbol: _DEFAULT_ETA_MOTOR
kind: constant
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Default motor efficiency (performance module)

**Definition.** Fallback electrical-to-mechanical motor efficiency used when the catalog entry has no efficiency_pct.

**Value.** `0.85`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:51` — `_DEFAULT_ETA_MOTOR`

**Consumed by.**

- in this graph: [[motor-eta|Motor + gearbox efficiency]]
- outside it: `app/services/powertrain_performance.py:147`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, Ch. 3, pp. 28-29: 'For typical hobby BLDC motors, peak efficiency typically falls between 75-85% in the flight-typical operating range. Roxxy motors achieve 80-85%.'
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
eta_m = P_mech / P_el, hobby BLDC peak 0.75-0.85
```

**⚠️ Divergence from the source.** The source gives 0.75-0.85 as the PEAK efficiency band, reached 'roughly in the center of the motor's operating range'. The code adopts the top of that band (0.85) as a flat constant applied at every point of the velocity sweep, including off-design. The source explicitly says peak efficiency occurs at a power 'significantly lower than the rated power', so 0.85 is optimistic wherever the motor is not near mid-range.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback with no source (ADR 0020/0023): substituting 0.85 for a missing datasheet value emits no DesignWarning — it only appears inside the free-text notes string at line 793.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# brushless outrunner default`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
