---
name: required-power-w-shim
symbol: _required_power_w
kind: quantity
unit: W (never returned)
cluster: powertrain
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Legacy power-required shim

**Definition.** Removed legacy entry point; unconditionally raises NotImplementedError directing callers to _combo_required_power_w.

**Formula — as the code writes it.**

```
raise NotImplementedError("powertrain_sizing_service requires aircraft geometry (cd0, e_oswald, AR, S); legacy estimate-only mode removed in gh-490. Use _combo_required_power_w with explicit geometry parameters.")
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:67` — `_required_power_w`

**Consumed by.**

- outside it: `app/tests/test_powertrain_sizing_service.py:28` · `app/tests/test_powertrain_sizing_service.py:133`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Dead code that only raises. Nothing to attribute.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NO PRODUCTION CONSUMER — a 17-line function whose only callers are the tests that assert it raises. ADR 0021 (complete but unreachable code is deleted by default).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Legacy shim — removed in gh-490 (Model A refactor)."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
