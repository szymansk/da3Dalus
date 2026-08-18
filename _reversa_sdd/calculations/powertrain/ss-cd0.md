---
name: ss-cd0
symbol: cd0
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Zero-lift drag coefficient (solution space)

**Definition.** Parasite drag coefficient resolved by a three-tier priority: gh-924 computation context, then the design assumption, then the PARAMETER_DEFAULTS value with a warning.

**Formula — as the code writes it.**

```
cd0_ctx = ctx.get("cd0") ; if cd0_ctx is not None and float(cd0_ctx) > 0: cd0 = float(cd0_ctx) else: cd0_raw = get_effective_assumption(db, plane_id, "cd0") ; if cd0_raw is not None and float(cd0_raw) > 0: cd0 = float(cd0_raw) else: warnings.append(...) ; cd0 = float(PARAMETER_DEFAULTS.get("cd0", 0.03))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:323` — `compute_solution_space`

**Consumed by.**

- in this graph: [[ss-drag-coefficient|Total drag coefficient]] · [[ss-p-aero-cruise|Aerodynamic power at cruise]] · [[ss-p-aero-top|Aerodynamic power at top speed]]
- outside it: `app/services/powertrain_solution_space_service.py:349` · `app/services/powertrain_solution_space_service.py:350`

**Source.** 🟢 SOURCED

> Sadraey (2013), Table 4.12 (cited in §4.6): typical turboprop transport C_Do ~ 0.025-0.035, with Eq. 4.62 given as the preferred back-calculation from flight data.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_D = C_Do + K C_L^2, C_Do from Table 4.12 or back-calculated (Eq. 4.62)
```

**⚠️ Divergence from the source.** The three-tier resolution (computation context -> design assumption -> default) is consistent with Sadraey's own preference for a derived C_Do over a table value.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The final tier resolves to 0.03, attributable only to Sadraey's transport-category Table 4.12. The RC sources give no C_D0: Lennon Ch. 12 warns 'typical sport RC models carry far more parasite drag than builders realize', and the Roxxy Motoren-Fibel Ch. 2, pp. 17-18 abandons C_D0 for a measured lumped model constant MK = c_w rho A (AcroMaster ~0.04, FunCub ~0.036, EasyGlider ~0.02, Heron ~0.014, Alpina ~0.01). ADR 0023.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Only cd0 gets the design-assumption tier; e_oswald, AR, S_ref and V_cruise jump straight from context to hardcoded fallback. The gh-924 'single source of truth' comment therefore applies to one of five aero inputs.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# cd0: gh-924 single source of truth — read from the computation context first (where e/AR/s_ref also come from), fall back to the design assumption, then warn if neither is available.`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
