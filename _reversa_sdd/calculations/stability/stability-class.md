---
name: stability-class
symbol: stability_class
kind: quantity
unit: – (enum string)
cluster: stability
user_visible: true
source_status: PARTIAL
---

# Stability classification (static margin band)

**Definition.** Maps static margin percent to a stable/neutral/unstable label. >5 % stable, 0–5 % neutral, <0 % unstable.

**Formula — as the code writes it.**

```
if static_margin_pct > 5: return "stable"
if static_margin_pct >= 0: return "neutral"
return "unstable"
```

**Inputs.** [[static-margin-pct|Static margin percent]] · [[sm-classify-stable-threshold-pct|Stable/neutral boundary]] · [[sm-classify-neutral-threshold-pct|Neutral/unstable boundary]]

**Produced by.** `app/services/stability_service.py:70` — `classify_stability`

**Consumed by.**

- outside it: `app/services/stability_service.py:350` · `app/services/copilot_tools.py:453` · `app/mcp_server.py:1166 get_stability tool`

**Source.** 🟡 PARTIAL

> Boundary at 0 %: Sadraey §11.6.2, Eq. 11.22 (x_np − x_cg > 0 is the static-stability condition). Boundary at 5 %: Lennon, "Basics of R/C Model Aircraft Design" (Air Age 1996) Ch. 6 ("The minimum suggested margin is 5 percent"); rcplanedesigner.com, "Airplane Balance — Finding the First-Flight CG" § Center of Gravity and Static Margin ("First-flight floor is 5% of MAC").
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
Static stability: C_mα < 0 ⇔ x_cg < x_np ⇔ SM > 0 (Sadraey Eq. 11.17/11.22)
```

**⚠️ Divergence from the source.** Both boundary values are individually attributable, but no consulted source defines a three-band stable/neutral/unstable *labelling* of static margin. Sadraey §11.4 instead warns that an aircraft becomes dynamically unstable already within 2–3 % MAC of the neutral point — i.e. the code's "neutral" band 0–5 % contains a region Sadraey calls dynamically unstable.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** A second, unrelated function with the identical name `classify_stability` exists in trim_enrichment_service.py:121 with different inputs and a different output type.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `>5% → stable, 0-5% → neutral, <0% → unstable.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
