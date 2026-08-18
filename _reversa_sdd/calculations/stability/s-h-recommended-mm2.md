---
name: s-h-recommended-mm2
symbol: S_H,rec
kind: quantity
unit: mm²
cluster: stability
user_visible: true
source_status: SOURCED
---

# Recommended horizontal tail area

**Definition.** Horizontal tail area that would place V_H at the midpoint of the class target band, converted to mm².

**Formula — as the code writes it.**

```
v_h_mid = (v_h_range[0] + v_h_range[1]) / 2.0
result.s_h_recommended_mm2 = round(v_h_mid * s_ref_m2 * mac_m / l_h * 1e6, 0)
```

**Inputs.** [[aircraft-class-tail-targets|Tail-volume target ranges by aircraft class]] · [[l-h-m|Horizontal tail moment arm]]

**Produced by.** `app/services/tail_sizing_service.py:259` — `compute_tail_volumes`

**Consumed by.**

- outside it: `app/api/v2/endpoints/aeroplane/tail_sizing.py:85` · `frontend/components/workbench/TailVolumeCard.tsx:197-198,244` · `frontend/lib/metricsAdapters.ts:621-630`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.7.1: "Compute S_h from the V_H definition: S_h = V_H · C̄ · S / l". Same inversion stated at RC scale by rcplanedesigner.com, "Tail — Horizontal Tail Placement and Sizing": "Horizontal tail area = (Horizontal tail volume coefficient × Wing area × Wing MAC) / Tail lever arm."
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
S_h = V_H · C̄ · S / l   (Sadraey §6.7.1)
```

**⚠️ Divergence from the source.** The inversion matches. Choosing the MIDPOINT of the target band as the recommendation is the code's own decision — Sadraey §6.7.1 selects V_H from stability requirements and then solves Eq. 6.29 for C_Lh, and rcplanedesigner explicitly frames its bands as "starting ranges, not final guarantees" with the note that a trainer should sit at the UPPER end of its range, not the middle. The ×1e6 mm² conversion is applied here at line 259, contradicting the service docstring at lines 353-356 which says the endpoint does it.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The service docstring at build_tail_sizing_context_from_aeroplane (lines 353-356) states 'compute_tail_volumes returns m²; endpoint multiplies by 1e6 for mm²' — false: the 1e6 is applied here at line 259, and the endpoint (tail_sizing.py:85) passes it through unchanged. The comment contradicts the code.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# --- Recommended areas (m² → mm²) ----------------------------------------`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
