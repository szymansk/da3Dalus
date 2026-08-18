---
name: l-h-m-fallback
symbol: l_H
kind: quantity
unit: m
cluster: stability
user_visible: false
source_status: SOURCED
---

# Tail arm fallback

**Definition.** Horizontal tail moment arm used when the context value is missing or non-positive.

**Formula — as the code writes it.**

```
l_h_m = 2.0 * mac_m
```

**Inputs.** [[mac-m-fallback|MAC fallback]]

**Produced by.** `app/services/sm_sizing_service.py:160` — `_dsm_dsh`

**Consumed by.**

- in this graph: [[dsm-dsh|SM sensitivity to horizontal tail area]]
- outside it: `app/services/sm_sizing_service.py:162`

**Source.** 🟢 SOURCED

> rcplanedesigner.com, "Fuselage — Tail Lever Arm: Pitch Leverage and Stability in RC Airplanes" § Design envelope: "A practical lower limit is: Tail Lever Arm ≥ 2 × Mean Aerodynamic Chord … Below that threshold, the tail sits too close to the center of gravity to provide sufficient leverage." Mission table: Trainer 2.7–3.0 × MAC, Sport 2.3–2.7 × MAC, Acrobatic 2.0–2.3 × MAC. Corroborated: Lennon Ch. 7 uses TMA = 2.5 × MAC as its reference case.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
l_H ≥ 2 × MAC (practical lower limit); mission bands 2.0–3.0 × MAC
```

**⚠️ Divergence from the source.** The value is defensible and RC-scale, but it is the *lower bound of the envelope*, not a typical value — Lennon's reference case and every rcplanedesigner mission band sit at 2.0–3.0 × MAC with the trainer at 2.7–3.0. Using the floor as the default biases dSM/dS_H low by up to 50 %. Substitution is silent (ADR 0020), and tail_sizing_service.py:200 already computes the real l_h_m but never publishes it into the context this fallback reads.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback with no cited source for the factor 2.0; silent (ADR 0020). tail_sizing_service already computes a real l_h_m (tail_sizing_service.py:200) but sm_sizing never reads it.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Fall back: estimate l_H as 2.0 × MAC`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
