# Architecture Decision Records — da3Dalus / cad-modelling-service

**How to use this index.** Scan the table before every feature. Read in full only the
ADRs your change touches — the *Area* column is the routing key. Each ADR carries the
decision and its consequences; the evidence behind it lives in
[`../questions.md`](../questions.md) (every `Q-id` has a filled `**Answer:**`), the
`../expert-consensus-*.md` files, [`../wave2-lookups.md`](../wave2-lookups.md) and
[`../wave3-lookups.md`](../wave3-lookups.md),
[`../architecture.md`](../architecture.md), [`../domain.md`](../domain.md),
[`../permissions.md`](../permissions.md) and
[`../code-analysis.md`](../code-analysis.md).

**⭐ Always review criteria, whatever the change touches:**
[0019](0019-implementation-details-must-not-leak-into-the-api.md) (no implementation
detail in the public API) and
[0022](0022-one-authority-per-user-facing-quantity.md) (one producer per user-facing
quantity). A violation of either is review-blocking.

## Index

| # | Title | Area | Status |
|---|---|---|---|
| [0001](0001-millimetres-in-cad-metres-in-db-and-aerosandbox.md) | Millimetres in the CAD topology, metres in the DB and AeroSandbox | units, converters | Accepted (+ amendment) |
| [0002](0002-cad-designer-is-frozen-new-creators-only.md) | `cad_designer/` is frozen: read-only topology, new Creators only | CAD engine, quality gates | Accepted |
| [0003](0003-aerosandbox-default-avl-exception.md) | AeroSandbox is the default solver; AVL is the exception | aerodynamics | Accepted |
| [0004](0004-one-aero-truth-per-aircraft.md) | One aero truth per aircraft: the cached computation context | aerodynamics, data model | Accepted |
| [0005](0005-cad-in-a-spawned-process-pool.md) | CAD runs in a spawned worker process (OCCT is not thread-safe) | concurrency | Accepted, inconsistently applied |
| [0006](0006-versioning-by-row-copy-not-json-snapshots.md) | Versioning by row copy: a DAG of aeroplane rows | persistence, versioning | Accepted (supersedes `design_versions`) |
| [0007](0007-copilot-proposes-human-adopts.md) | The AI copilot proposes on a branch; only a human adopts | AI, safety | Accepted (+ amendment: MCP writes) |
| [0008](0008-control-surface-roles-decompose-into-axes.md) | A control surface's *role* decomposes into control *axes* | flight dynamics | Accepted, open bug #955 |
| [0009](0009-get-db-owns-the-transaction-boundary.md) | `get_db()` owns the transaction boundary; services never commit | persistence | Accepted, one systematic violation |
| [0010](0010-design-assumptions-carry-estimate-and-calculated.md) | Every design parameter carries both an estimate and a calculation | design intent | Accepted (+ amendment: context contract) |
| [0011](0011-cg-is-a-top-down-design-target.md) | CG is a top-down design target, not the aggregate of component masses | design philosophy | Accepted |
| [0012](0012-design-warnings-instead-of-silent-fallbacks.md) | An unphysical result is a design warning, never a silent fallback | UX, correctness | Accepted (mechanism in 0020) |
| [0013](0013-one-components-table-with-a-data-driven-type-schema.md) | One `components` table with a user-extensible, data-driven type schema | data model | Accepted |
| [0014](0014-cots-ingestion-from-committed-snapshots.md) | COTS data is ingested from committed snapshots, never a live source | data pipeline | Accepted |
| [0015](0015-tiered-ci-fast-full-nightly.md) | Tiered CI: a fast PR gate, an opt-in full tier, a nightly everything | delivery | Accepted |
| [0016](0016-no-application-auth-the-tunnel-is-the-boundary.md) | No application-level authentication; the tunnel is the trust boundary | security | Accepted — **highest risk**, framing **corrected by 0024** |
| [0017](0017-optional-heavy-dependencies-probed-at-import.md) | Heavy native dependencies are optional, probed once, degrade to 503 | platform | Accepted |
| [0018](0018-openvsp-import-scope-is-rc-scaling-inspiration.md) | OpenVSP import is "RC-scaling inspiration": geometry and mass only | interoperability | Accepted |
| ⭐ [0019](0019-implementation-details-must-not-leak-into-the-api.md) | Implementation details must not leak into the public API | api | Accepted |
| [0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md) | One `DesignWarning` channel: no *undeclared* fallbacks | UX, correctness | Accepted (refines 0012) |
| [0021](0021-complete-but-unreachable-code-is-deleted-by-default.md) | Complete but unreachable code is deleted by default; "inert" is forbidden | code health | Accepted |
| ⭐ [0022](0022-one-authority-per-user-facing-quantity.md) | One authority per user-facing quantity | data model, correctness | Accepted (generalises 0004) |
| [0023](0023-engineering-constants-carry-provenance.md) | Engineering constants carry provenance and are validated at RC/UAV scale | domain methodology | Accepted |
| [0024](0024-single-user-desktop-operating-model.md) | Single-user desktop operating model | product, security | Accepted (**corrects 0016**) |
| [0025](0025-mcp-is-built-on-the-copilot-tool-layer.md) | MCP is built on the copilot tool layer, not by wrapping REST | agents, architecture | Accepted |

## Provenance

0001–0018 are **retroactive**, reconstructed from the code, 1 495 commits
(2022-07 → 2026-07), Alembic migrations and the project's `CLAUDE.md` files. The one
contemporaneous in-repo ADR,
`docs/decisions/2026-07-14-exclude-cad-designer-from-sonarcloud.md`, is summarised and
extended by [0002](0002-cad-designer-is-frozen-new-creators-only.md).
**0019–0024 are not retroactive** — they record decisions taken in the specification
validation interview (2026-08-13 → 2026-08-15), which also appended
`## Amendment — 2026-08-15` sections to 0001 (`Q-FD-2`), 0007 (`Q-MC-1`) and
0010 (`Q-CC-10`). Amendments extend; they never change the original decision.

## Reading order

- **Domain:** 0011 → 0010 → 0004 → 0012 → 0023
- **Geometry stack:** 0001 → 0002 → 0005 → 0018
- **Aero stack:** 0003 → 0004 → 0008
- **Persistence and change:** 0009 → 0006 → 0007
- **Risk before deploying anything:** **0024** → 0016 → 0009 → 0006
- **Cross-cutting rules the interview settled:** 0020 (warn) → 0021 (delete) →
  0022 (one producer) → 0023 (provenance) → 0024 (operating model)
