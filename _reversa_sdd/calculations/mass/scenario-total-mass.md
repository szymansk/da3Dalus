---
name: scenario-total-mass
symbol: m_scenario
kind: quantity
unit: kg
cluster: mass
user_visible: false
source_status: SOURCED
---

# Loading-scenario total mass

**Definition.** Total mass of one loading scenario — components (after toggles and mass overrides) plus ad-hoc items. Used only as the denominator of the CG.

**Formula — as the code writes it.**

```
total_mass += m  (per component, line 177)  ...  total_mass += m  (per adhoc item, line 188)
```

**Inputs.** [[base-mass-default|Fallback base mass for scenario CG]]

**Produced by.** `app/services/loading_scenario_service.py:177` — `compute_scenario_cg`

**Consumed by.**

- outside it: `app/services/loading_scenario_service.py:193 (divisor of moment_x only)`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.2 Eq. (11.1) — the denominator ΣW_i (= Σm_i) of the CG expression; §11.3.2 ("Center of Gravity Range Definition") establishes that this same sum is a first-class published quantity: "A weight vs. cg envelope must be plotted and made available in the pilot flight manual… A typical envelope shows a maximum weight W_max and minimum weight W_min on the vertical axis."
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
X_cg = ΣW_i·x_cg,i / ΣW_i, where ΣW_i is the loaded weight of that condition (Eq. 11.1); envelope plotted as weight vs. cg (§11.3.2)
```

**⚠️ Divergence from the source.** In Sadraey the scenario mass is one of the two AXES of the balance envelope — every loading condition is a (weight, cg) point and "any point outside the polygon is forbidden". The code uses it only as a local divisor (loading_scenario_service.py:193) and never publishes it, so the app's CG envelope is one-dimensional. Concrete consequence: ad-hoc items (pilot, payload, ballast, fuel) shift the reported CG but leave the reported aircraft mass untouched, which Sadraey's weight-vs-cg envelope makes impossible by construction.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NO CONSUMER outside the local division. Ad-hoc items (pilot, payload, ballast, fuel) add real mass, but that mass never reaches the 'mass' design assumption, the CgEnvelopeRead response, or the UI — only the resulting CG shift is published. A scenario can therefore move the CG without moving the reported aircraft mass.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
