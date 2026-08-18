---
name: variation-thresholds
kind: constant
unit: m (applied to Xnp)
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Variation classification thresholds

**Definition.** Span bands separating robust / moderate / volatile.

**Value.** `0.5 / 2.0`

**Formula — as the code writes it.**

```
if span < 0.5: robust; if span < 2.0: moderate; else volatile
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:846` — `_classify_variation`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> 0.5 m / 2.0 m have no attribution in Sadraey §11.6.2, Scholz, Anderson, or Lennon Ch. 6.
>
> — via `aircraft-design-scholz, rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** The literature measures neutral-point position NON-DIMENSIONALLY (Sadraey Eq. 11.18: SM = (x_np − x_cg)/C̄; Lennon Ch. 6: NP at 35% MAC, static margin 5–10% MAC). Applying an absolute metre threshold to a dimensional Xnp has no counterpart in any source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** ADR 0023 — this is a transport-scale threshold. For an RC model with MAC ≈ 0.20 m, Lennon's entire usable static-margin band (5–10% MAC) is 0.010–0.020 m. The code calls up to 0.5 m of Xnp travel 'robust' — that is 2.5 MAC, i.e. 25× the whole design band. The 'volatile' verdict is effectively unreachable at 0.5–15 kg.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Applied to a neutral-point position in metres: an RC/UAV aircraft with a 1-2 m fuselage is called 'robust' for up to 0.5 m of Xnp travel — a transport-scale threshold on a 0.5-15 kg target class (ADR 0023), NO_SOURCE_FOUND.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
