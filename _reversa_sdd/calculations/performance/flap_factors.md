---
name: flap_factors
symbol: (f_TO, f_LDG)
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Flap CL_max multiplier table

**Definition.** Per-flap-type multipliers applied to the base CL_max for takeoff and landing.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `None/none:(1.0,1.0); plain:(1.1,1.3); slotted:(1.1,1.3); fowler:(1.3,1.6); slat:(1.3,1.6); fowler+slat:(1.3,1.6)`

**Formula — as the code writes it.**

```
_FLAP_FACTORS: dict[str | None, tuple[float, float]] = {None: (1.0, 1.0), "none": (1.0, 1.0), "plain": (1.1, 1.3), "slotted": (1.1, 1.3), "fowler": (1.3, 1.6), "slat": (1.3, 1.6), "fowler+slat": (1.3, 1.6)}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:114` — `_FLAP_FACTORS`

**Consumed by.**

- in this graph: `Resolved flap factors`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `detect_cl_max_flap_factors:158` · `compute_field_lengths:358`

**Source.** 🔴 NO SOURCE FOUND

> Both authorities express high-lift as ADDITIVE increments, never as ratios. Sadraey 2013, high-lift device classification, comparative dCL_max at 60 deg: plain 0.7-0.9; split 0.7-0.9; Fowler 1.0-1.3; single slotted 1.3*(Cf/C); double slotted 1.6*(Cf/C); triple slotted 1.9*(Cf/C); LE flap 0.2-0.3; LE slat 0.3-0.4; Kruger 0.3-0.4. Scholz 08_HighLift §8.2 uses DATCOM 1978: dcL_max,f = k1*k2*k3*(dcL_max)_base, Figs 8.11-8.14. Only a GH-issue amendment is cited in code.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
CL_max_flapped = CL_max_clean + dCL_max (additive)
```

**⚠️ Divergence from the source.** Three distinct errors. (1) Multiplicative is the wrong model - dCL_max is roughly independent of the base airfoil, so a ratio makes the increment scale with CL_max_clean, which neither source supports. (2) The slat factor is inverted: the code gives slat the LARGEST factor (1.3,1.6) while Sadraey puts LE slat at dCL 0.3-0.4, the SMALLEST of all devices, and states explicitly that TE devices yield far larger dCL than LE devices. (3) slotted = plain (1.1,1.3) contradicts Sadraey directly (plain 0.7-0.9 vs single-slotted 1.3*(Cf/C)); the inventory's 'fictional granularity' anomaly is confirmed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 'slotted' is given the same factors as 'plain' and 'slat' the same as 'fowler', so the table's granularity is fictional; only a GH-issue amendment is cited, no aerodynamic source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Source: gh-489 spec, Amendment 2`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
