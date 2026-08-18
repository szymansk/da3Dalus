---
name: is-tailless-flag
symbol: —
kind: quantity
unit: – (bool)
cluster: stability
user_visible: false
source_status: SOURCED
---

# Tailless configuration flag

**Definition.** True when the aircraft has no horizontal tail and is not a canard; gates both tail-volume sizing and SM apply operations.

**Formula — as the code writes it.**

```
is_tailless = htail is None and not is_canard
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:416` — `build_tail_sizing_context_from_aeroplane`

**Consumed by.**

- outside it: `app/services/tail_sizing_service.py:160,472` · `app/services/sm_sizing_service.py:204,329 (reads ctx['is_tailless'])`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (1996) Ch. 23: a tailless aircraft is one where "the wing's aerodynamic center (AC) and the neutral point (NP) coincide — there is no horizontal tail to push the NP aft of the AC." Sadraey §6.7.1 treats the presence/absence of a horizontal surface as the configuration discriminator for tail sizing.
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
Tailless ⇔ no horizontal surface aft of the wing contributing to the neutral point (Lennon Ch. 23)
```

**⚠️ Divergence from the source.** The source's criterion is geometric/aerodynamic. The code's is lexical: substring match on the wing NAME ('horizontal'/'htail'), so a correctly modelled tail named e.g. 'Stabilizer' makes the aircraft tailless and routes it to the Lennon Ch. 23 SM 5–10 % path instead of tail-volume sizing. The in-code comment describes a wing-count rule the code does not implement.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Detection is by substring on the wing NAME ('horizontal'/'htail'), so a correctly modelled tail named e.g. 'Stabilizer' makes the aircraft tailless. The comment describes a wing-count rule that the code does not implement.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Flying-wing / tailless: no wing with "horizontal" in name and wing
#   count == 1 (only main wing).`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
