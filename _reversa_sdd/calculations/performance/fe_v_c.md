---
name: fe_v_c
symbol: V_C
kind: quantity
unit: m/s
cluster: perf-envelope
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Cruise speed (back-derived)

**Definition.** Cruise speed inferred by dividing dive speed by 1.4.

**Formula — as the code writes it.**

```
v_c = v_dive / 1.4
```

**Inputs.** [[fe_v_dive|Dive speed]] · [[fe_dive_factor|Dive-speed factor]]

**Produced by.** `app/services/flight_envelope_service.py:190` — `_build_gust_lines`

**Consumed by.**

- in this graph: [[fe_u_gust_at_v|Gust velocity schedule]]

**Source.** 🔴 NO SOURCE FOUND

> No source for defining V_C as V_D/1.4. The regulatory dependency runs the other way: FAR 23.335(b)(1) / CS-VLA 335(b) set V_D >= 1.25*V_C, and FAR 23.335(a) sets a minimum V_C from sqrt(W/S).
>
> — via `scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Circular by construction: V_D := 1.4*V_max upstream, so V_C := V_D/1.4 === V_max. The gust envelope's 'cruise speed' is therefore max level speed, which is the one speed it certainly is not. ctx already carries an independent v_cruise_mps that is ignored. Consequence: U_de is held at the full 15.24 m/s all the way to V_max instead of tapering from a genuine cruise speed, inflating the gust line across the whole envelope.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Circular definition: V_D is defined as 1.4·V_max upstream, so V_C here is just V_max renamed. The gust envelope's V_C is therefore max level speed, not a design cruise speed; ctx also carries an independent v_cruise_mps that is ignored.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Cruise speed (V_D = 1.4 · V_C by construction)"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
