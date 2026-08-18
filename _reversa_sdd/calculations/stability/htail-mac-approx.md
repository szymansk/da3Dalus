---
name: htail-mac-approx
symbol: c_H
kind: quantity
unit: m
cluster: stability
user_visible: false
source_status: SOURCED
---

# Horizontal tail MAC (mean chord approximation)

**Definition.** Stands in for the horizontal tail mean aerodynamic chord.

**Formula — as the code writes it.**

```
chords = [x.chord for x in xsecs if x.chord]
if not chords:
    return None
return sum(chords) / len(chords)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:495` — `_wing_mac_approx`

**Consumed by.**

- in this graph: [[vtail-mac-approx|Vertical tail MAC (mean chord approximation)]] · [[x-htail-ac-m|Horizontal tail aerodynamic centre x]]
- outside it: `app/services/tail_sizing_service.py:435,463` · `app/services/tail_sizing_service.py:197 (x_htail_ac_m)`

**Source.** 🟢 SOURCED

> Scholz HAW Hamburg, 07_WingDesign §7.1 — the mean aerodynamic chord is c_MAC = (2/S)·∫₀^(b/2) c² dy, evaluating for a simple tapered surface to c_MAC = (2/3)·c_r·(1+λ+λ²)/(1+λ). Sadraey §6.7 applies the same definition to the tail.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
c_MAC = (2/S)·∫₀^(b/2) c² dy  ;  tapered: c_MAC = (2/3)·c_r·(1+λ+λ²)/(1+λ)
```

**⚠️ Divergence from the source.** The code computes the unweighted arithmetic mean of the section chords (sum(chords)/len(chords), tail_sizing_service.py:495), which is neither the integral nor the closed form. For a tapered surface the MAC is span-weighted toward the root and always exceeds the arithmetic mean — e.g. at λ = 0.5 the closed form gives 0.778·c_r while the arithmetic mean of root and tip gives 0.750·c_r (~3.6 % low). The code also ignores segment span entirely, so an unevenly discretised tail biases the result further. This value feeds x_htail_ac_m, hence l_H, hence V_H.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NAME CONTRADICTS DEFINITION: this is the unweighted arithmetic mean of section chords, not the mean aerodynamic chord (which is span-weighted: (2/3)·c_r·(1+λ+λ²)/(1+λ)). On a tapered tail the two differ by several percent, and the value feeds the AC position and hence l_H and V_H. It also ignores segment span entirely, so an unevenly discretised tail biases the result.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"""Arithmetic mean chord as MAC approximation."""`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
