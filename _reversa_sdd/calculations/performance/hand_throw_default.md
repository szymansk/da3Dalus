---
name: hand_throw_default
symbol: v_throw_default
kind: parameter
unit: m/s
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Default throw speed

**Definition.** Throw speed assumed when the caller supplies none for hand-launch mode.

**Value.** `10.0`

**Formula — as the code writes it.**

```
_HAND_THROW_DEFAULT: float = 10.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:110` — `_HAND_THROW_DEFAULT`

**Consumed by.**

- outside it: `compute_field_lengths:377`

**Source.** 🔴 NO SOURCE FOUND

> No source. 10 m/s is a plausible human throw speed but is not attributable to any consulted work.
>
> — via `aircraft-design-scholz (confirmed gap)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Substituted silently with no DesignWarning (ADR 0020), so the user cannot tell that a load-bearing input was invented.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Substituted silently with no DesignWarning (ADR 0020); NO_SOURCE_FOUND for 10 m/s.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# m/s default throw speed`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
