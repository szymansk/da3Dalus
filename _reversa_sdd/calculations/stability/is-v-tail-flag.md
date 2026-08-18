---
name: is-v-tail-flag
symbol: —
kind: constant
unit: – (bool)
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# V-tail configuration flag

**Definition.** Whether the aircraft has a V-tail; gates tail-volume sizing to not_applicable.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `False`

**Formula — as the code writes it.**

```
is_v_tail = False  # V-tail decomposition is out-of-scope (gh-491)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:417` — `build_tail_sizing_context_from_aeroplane`

**Consumed by.**

- outside it: `app/services/tail_sizing_service.py:160,472`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Not a quantity — a hardcoded False. For the record, the sources do define the decomposition it stands in for: Sadraey §6.7 covers V-tail ('other tail geometries') and §6.2.2 the pitch/yaw split; the code's own module header at elevator_authority_service.py:33 names the cos²γ relation. Because the flag is always False, the is_v_tail guard at tail_sizing_service.py:160 is unreachable and a real V-tail is sized either as tailless or as a conventional tail — with the wrong formula in both cases.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Hardcoded False, so the is_v_tail guard at line 160 is unreachable from this producer — a real V-tail is classified as either tailless (no 'horizontal' in the name) or as a conventional tail, and is sized with the wrong formula either way.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# V-tail decomposition is out-of-scope (gh-491)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
