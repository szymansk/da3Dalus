---
name: fe_b_ref
symbol: b_ref
kind: quantity
unit: m
cluster: perf-envelope
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Reference span

**Definition.** Reference span from the ASB airplane, or None when conversion fails.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
b = asb_airplane.b_ref; return float(b) if b is not None and b > 0 else None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:630` — `_get_b_ref`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Aspect ratio (gust path)` · `Mean geometric chord`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Reference span convention owned by the geometry/ASB layer.
>
> — via `aero`

**The source states it as.**

```
b_ref from ASB airplane
```

**⚠️ Divergence from the source.** ADR 0020: bare `except Exception: return None` at fe:632 disables the entire gust envelope silently. The user sees a V-n diagram with no gust lines and no statement that gust analysis was attempted and failed — indistinguishable from a design where gusts are not critical.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Bare `except Exception: return None` (line 632) swallows every conversion failure and silently disables the entire gust envelope with no warning to the user (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
