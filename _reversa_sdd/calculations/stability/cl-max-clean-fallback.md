---
name: cl-max-clean-fallback
symbol: CL_max,clean
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: PARTIAL
---

# Clean CL_max fallback

**Definition.** Clean-configuration maximum lift coefficient assumed when the cl_max assumption is absent.

**Value.** `1.4`

**Formula — as the code writes it.**

```
cl_max_clean = cl_max_raw if cl_max_raw is not None else 1.4
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:500` — `_load_stability_assumptions`

**Consumed by.**

- in this graph: [[cl-max-landing|Landing CL_max]]
- outside it: `app/services/elevator_authority_service.py:507,586,993` · `app/schemas/design_assumption.py:77 (same value as PARAMETER_DEFAULTS['cl_max'])`

**Source.** 🟡 PARTIAL

> Scholz HAW Hamburg, 05_PreliminarySizing §5.1 Table 5.1 gives C_L,max,L by aircraft type — single-engine propeller 1.6–2.3, twin-engine propeller 1.6–2.5, business jet 1.6–2.6 — but those are LANDING-configuration values, not clean. Sadraey §5.17 worked example implies a clean-airfoil c_l,max requirement of 1.5 for a normal-category GA aircraft. No source states a clean-configuration aircraft C_L,max of 1.4.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_L,max,L by type, Table 5.1 (Scholz 05_PreliminarySizing §5.1)
```

**⚠️ Divergence from the source.** 1.4 is plausible for a clean RC wing but unattributed. It is repeated as three separate inline literals (elevator_authority_service.py:500, 586, 993) and duplicates PARAMETER_DEFAULTS['cl_max'] in app/schemas/design_assumption.py:77. Substitution is silent (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Table 5.1 is a transport/GA table (CS-25/FAR-23 categories). Low-Reynolds RC wings (Re ≈ 100k–400k) reach materially lower clean C_L,max than the GA values in that table; no RC-scale validation is recorded (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Repeated as three separate inline literals (lines 500, 586, 993) instead of one constant; silent substitution with no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
