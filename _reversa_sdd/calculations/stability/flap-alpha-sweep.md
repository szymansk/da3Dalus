---
name: flap-alpha-sweep
symbol: —
kind: constant
unit: deg
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Flap CL_max alpha sweep

**Definition.** Angle-of-attack grid swept to locate CL_max in the flapped configuration.

**Value.** `-5.0, 20.0, 1.0`

**Formula — as the code writes it.**

```
alphas = np.arange(-5.0, 20.0, 1.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:875` — `_run_flap_analysis`

**Consumed by.**

- in this graph: [[alpha-stall-landing|Landing stall alpha]] · [[cl-max-landing-flap|Swept flapped CL_max]]
- outside it: `app/services/elevator_authority_service.py:880`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aerosandbox-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source specifies an alpha grid. Tool guidance is available and is not followed: AeroSandbox docs (aero_3d, AeroBuildup class reference) state that AeroBuildup 'runs an entire α-sweep in a single .run() call, returning arrays' — the code instead loops one .run() per alpha (elevator_authority_service.py:880). The 1° step quantises both CL_max and the alpha at which it occurs; np.arange(-5.0, 20.0, 1.0) ends at 19.0, so a stall beyond 19° silently returns the endpoint. Note for the record: AeroBuildup DOES model stall (NeuralFoil-backed 360° envelope per the AeroSandbox docs), so the sweep can find a genuine maximum — but AeroSandbox itself characterises extreme-attitude results as 'order-of-magnitude correct rather than highly accurate'.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 1° resolution with no refinement: CL_max and the alpha at which it occurs are quantised to 1°, and if the true CL_max lies beyond 19° the sweep silently returns the endpoint. No source for the bounds.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Sweep alpha to find CL_max_landing and Cm at that point`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
