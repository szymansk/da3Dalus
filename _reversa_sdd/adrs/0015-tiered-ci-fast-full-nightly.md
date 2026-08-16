# ADR 0015 — Tiered CI: a fast PR gate, an opt-in full tier, a nightly everything

- **Status:** Accepted — in force
- **Decided:** 2026-05-13 (gh-504, commit `57c156fe`)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (workflow file, commit body with measured before/after)

## Context

The suite is large for a single-maintainer project — ~516 test files against
~1 180 source files — and much of it is genuinely heavy: CadQuery lofts (~13 s
each), AeroSandbox sweeps, AVL subprocesses, Playwright E2E. By May 2026 a pull
request took **~34 minutes** of CI on a 3.11 + 3.12 matrix, running sequentially.
At that latency the maintainer stops waiting for CI, which defeats it. The
complication: only ~76 of ~3 238 tests carried markers (~2 %), and marking three
thousand tests by hand was not a realistic prerequisite.

## Decision

**Split the backend suite into three tiers by marker, and derive the markers
automatically from file names.**

| Tier | Trigger | Marker filter | Python | Coverage |
|---|---|---|---|---|
| `fast` | every PR + push to `main` | `not slow and not e2e and not requires_cadquery and not requires_aerosandbox and not requires_avl` | 3.12 | yes, `--cov-fail-under=70` |
| `full` | PR label `ci-full` or manual dispatch | `not slow and not e2e` | 3.12 | no |
| `nightly` | cron `0 3 * * *` + dispatch | **all markers** | 3.11 **and** 3.12 | yes |
| `frontend` | frontend path changes | — | Node 22 | yes → `lcov.info` |
| `sonarcloud` | after `fast` + `frontend` | — | — | consumes both artefacts |

1. **`dorny/paths-filter`** decides whether the backend job, the frontend job or
   both run.
2. **`pytest_collection_modifyitems`** auto-tags tests by filename, taking marker
   coverage from ~2 % to ~370 heavy tests — and `test_marker_auto_tagging.py`
   **pins the file→marker mapping** with 18 parametrised cases, so a rename cannot
   silently move a test to a different tier.
3. **`pytest-xdist`** with `-n auto --dist worksteal` in the fast tier only.
4. **Nightly runs sequentially on purpose** — the memory-heavy CAD/aero tests
   cannot be parallelised — with a 3 000 s timeout, `--timeout-method=signal` to
   preempt native code and `faulthandler_timeout = 300` to dump native CAD hangs.
5. **The frontend job runs three gates**: `npm run lint`, **`npx tsc --noEmit`** and
   `test:unit --coverage`. `tsc` is there because it catches what vitest and eslint
   miss — e.g. adding a required field to a response interface breaks existing
   test-fixture literals.

## Consequences

- PR wall time went from **~34 min to a ~5–8 min target** (documented ceiling
  12 min), so the fast tier is a genuine gate; heavy fidelity coverage moves to
  nightly, where 3.11 is also exercised; the auto-tagging test makes the tiering a
  tested property rather than a convention.
- 🔴 **The fast tier runs *without* CadQuery, AeroSandbox and AVL**, and it feeds
  SonarCloud's `new_coverage` gate (80 % on new code). Aero- and CAD-dependent
  service code is only *counted* when it has **mocked fast tests that stub the
  solver boundary**. This has shaped the code — the spar solver is deliberately
  CAD-free decision logic behind a thin seam, the powertrain solution space
  deliberately pure Python — which is arguably good architectural pressure, but it
  is *test infrastructure* driving design.
- **Real integration regressions can reach `main` and surface the next morning.**
  The `ci-full` label exists but must be remembered.
- 🔴 **Path-filtered CI skips the ruff/fast job for scripts-only changes**, so
  unlinted code can land on `main` and break the next PR's fast job.
- **Node 22 is mandatory for the frontend**: Node ≥ 24 breaks jsdom `localStorage`
  and produces spurious failures — a documented local-run trap.
- **The coverage floor (70 %) is below the project's own target (>80 %)**, so the
  gate and the goal disagree.
- Two disabled workflows and a stale `azure-pipelines.yml` remain in the tree, so
  "what is CI" is not answerable from the file list alone.

**Rejected:** marking every test by hand (~3 238 tests); one tier plus
parallelisation (`-n auto` alone would not remove the CadQuery/ASB/AVL install and
runtime cost from every PR). 3.11 was moved to nightly rather than dropped.

## Related

[ADR 0002](0002-cad-designer-is-frozen-new-creators-only.md) (Sonar exclusions) ·
[ADR 0003](0003-aerosandbox-default-avl-exception.md) ·
[ADR 0017](0017-optional-heavy-dependencies-probed-at-import.md).
Evidence: commits `57c156fe` (gh-504), `cbfbbf3d`, `bea733bc`, `937991d3`;
`.github/workflows/test.yml`; `pyproject.toml` pytest section; project memories
`feedback_ci_coverage_no_aerosandbox`, `feedback_slow_tests_no_parallel`,
`feedback_frontend_test_node_version`, `feedback_frontend_tsc_noemit_before_push`,
`feedback_scripts_only_pr_skips_lint`.
