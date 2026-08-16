# ADR 0012 — An unphysical result is a design warning, never a silent fallback

- **Status:** Accepted — in force; the mechanism is supplied by [ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md)
- **Decided:** crystallised 2026-06 (gh-956, commit `de22bcec`; gh-672, `91315e8b`); the pattern predates both
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (commits, module docstrings, schema validators)

## Context

Every physics pipeline here can fail to produce a number: a polar fit rejected by a
laminar-separation bubble, an Oswald factor above 1.0, `best_ld_cl` undefined for
`k ≤ 0`, NeuralFoil returning NaN outside its confidence band. The tempting
response is a default — `e = 0.8` and `cd0 = 0.03` are perfectly reasonable values,
and a tool that quietly substitutes them always produces a plausible answer. That
is precisely the danger, because the *reason* the value could not be computed is
usually a fact about the design the user needs to know: a `k ≤ 0` fit usually means
the polar is not physical. gh-924 documented the damage — a hard-coded `0.03 / 0.8`
fallback contradicted the authoritative cruise values and generated a spurious
"min-sink at stall" warning that was purely an artifact.

## Decision

**When a computation cannot produce a physically meaningful number, surface it —
categorised, attributed and visible — instead of substituting a default.** Five
concrete forms:

1. **Categorised rejection gates.** The parabolic polar fit has six gates, each
   bound to a category by a Pydantic model validator enforcing the canonical
   gate→category pair:

   | Gate | Condition | Category |
   |---|---|---|
   | `insufficient_points` | ≥ 6 samples in the CL window | `sweep` |
   | `non_monotonic_polar` | `dCD/d(CL²) ≥ −1e-6` | `data` |
   | `negative_slope_k` | `k > 0` | **`design`** |
   | `non_positive_cd0` | `cd0_fit > 0` | `consistency` |
   | `unphysical_e_oswald` | `0.4 < e ≤ 1.0` | **`design`** |
   | `cd0_stability_mismatch` | within 20 % of the stability run | `consistency` |

   **Only `category == "design"` is surfaced to the user**; the rest are internal
   diagnostics.

2. **Resolution goes up; thresholds never move** (gh-672). Refinement retries
   *only* for `{insufficient_points, non_monotonic_polar}`, halving the α step and
   widening the margin by 1.5× per attempt (max 2), and sets `auto_refined=True`
   only when a refinement actually produced a fit. As a rule: *"polar-fit problems
   → raise the α resolution, never loosen the thresholds; AeroBuildup is cheap."*

3. **Provenance instead of silence.** Where a fallback genuinely is used it is
   *labelled*: `e_oswald_provenance ∈ {aerobuildup_trefftz, fit, fallback}`,
   `context["e_oswald_fallback_used"]`, `provenance ∈ {polar, cold_start}`,
   `trim_method ∈ {opti, grid_fallback}`, KPI confidence tiers
   `trimmed > computed > estimated > limit`.

4. **`null` rather than a fabricated number.** `NonFiniteSafeJSONResponse` converts
   non-finite floats to `null` and logs the count: `null` is *"an honest 'no value',
   never a fabricated fallback number that would hide the underlying design
   problem"*.

5. **Structured warnings on the API, not just the log** — `GustCriticalWarning`,
   `GustValidityWarning` (`μ_g ∉ [3, 200]`, the **normal** case for
   low-wing-loading RC models), turbulator-optimiser warnings, operating-point
   `STALE_NO_POLAR` / `FLAP_DEFLECTION_CLIPPED` / `STALL_IN_TURN`, powertrain
   `extrapolation_warning`, and the OpenVSP import's warning-based error policy.

## Consequences

- The user learns something true about their design instead of receiving a plausible
  number; provenance labels made gh-924 diagnosable at all and let the copilot answer
  "how confident is this?".
- **Warning fatigue is a real risk** — nothing clears operating-point warnings on a
  successful retrim, and `GustValidityWarning` fires for the *normal* RC case.
  Addressed by ADR 0020's `severity` grading.
- **Consumers must handle `None` everywhere**; a client that assumes a number breaks.
- 🔴 **Polar-rejection `hint` strings are German** while the UI is English-only, as
  are the `IntegrityError` / `RequestValidationError` handlers and the seeded
  component-type labels (`Q-CC-5`: translate all of them).
- 🔴 **`NonFiniteSafeJSONResponse` protects exactly one router** (`aeroanalysis.py`);
  five others can still 500 on a NaN.
- **This ADR defines no mechanism**, which is why it is violated at ~30 sites: there
  was nothing to emit *into*. Supplied by
  [ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md). The
  labelled-but-unremoved fallbacks (`DEFAULT_E_OSWALD = 0.8`, `_TC_FALLBACK = 0.12`,
  `_G_LIMIT_DEFAULT = 3.0`, `_CD0_REFERENCE_FALLBACK = 0.020`) and the
  `mass = 1.0 kg` speed polar are the catalogue of that gap.

**Rejected:** raising an exception on any unphysical result — a preliminary design
*is* often unphysical mid-iteration, and failing the request would make the tool
unusable exactly when it is most informative.

## Related

[ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md) (the
mechanism; amended into this ADR by name) ·
[ADR 0004](0004-one-aero-truth-per-aircraft.md) ·
[ADR 0018](0018-openvsp-import-scope-is-rc-scaling-inspiration.md) ·
domain rules BR-16, BR-17, BR-23, BR-64, BR-66, BR-74.
Evidence: commits `de22bcec` (gh-956), `91315e8b` (gh-672), `97153a8f` (gh-960),
`c0fa2b2e` (gh-819); `app/core/json_safe.py`; project memories
`feedback_design_error_feedback`, `feedback_aerobuildup_resolution`.
