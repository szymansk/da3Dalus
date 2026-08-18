---
name: mkpi_resolve_polar
symbol: (LD_emp, C_D0, e, AR)
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Clean-polar provenance chain

**Definition.** Resolves the clean-configuration polar inputs across the fit-rejection fallback chain.

**Formula — as the code writes it.**

```
polar = ctx['polar_by_config']['clean']; ld_emp = polar['ld_max'] if > 0; cd0 = polar['cd0'] or ctx['cd0']; e = polar['e_oswald'] or ctx['e_oswald']; ar = ctx['aspect_ratio']
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:165` — `_resolve_polar_inputs`

**Consumed by.**

- in this graph: [[mkpi_climb_energy|KPI: climb-energy figure]] · [[mkpi_glide|KPI: maximum glide ratio]]

**Source.** 🟢 SOURCED

> Resolution chain documented in-code (gh-681, gh-636); prefers the empirical ld_max from the AeroBuildup sweep over the closed form.
>
> — via `aero`

**⚠️ Divergence from the source.** Preferring the swept empirical value over the parabolic closed form is the right precedence. The defect is downstream in mkpi_glide, which does not tell the UI which branch won.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"gh-681: resolve (ld_max_empirical, cd0, e_oswald, ar) for the clean polar"; "gh-636 empirical max(CL/CD) from the AeroBuildup sweep"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
