# ADR 0006 — Versioning by row copy: a DAG of aeroplane rows, not JSON snapshots

- **Status:** Accepted — in force; supersedes the `design_versions` JSON system
- **Decided:** 2026-06-08 (epic gh-901; sub-issues gh-903/904/905, commit `019b4f7b`)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (design spec, migration, commit body)

## Context

An earlier `design_versions` table stored history as JSON snapshots. The gh-901
commit records the verdict in one clause: *"retire `design_versions` (no
back-migration of incomplete JSON)"* — the snapshots could not be restored into the
current schema at all, so the `down` migration recreates the table **empty**. The
requirement was a Git-like mental model (branch an idea, compare it, keep or
discard) and, once the copilot arrived, a place for the machine to write that is not
the live design. The aeroplane aggregate spans 17 tables, and serialising that into
a *continuously migrating* schema is exactly what failed the first time.

## Decision

**A version is a real `aeroplanes` row with its own full subgraph.** Versioning is
row copy, not serialisation.

```
root_id         → the lineage root (the root points at ITSELF)
predecessor_id  → self-referential: the node this one was forked from
branch_id       → FK to branches.id
is_immutable    → True = frozen snapshot; False = editable head
```

plus `version_label`, `version_note`, `created_by`, `provenance_message_id`,
`preview_png`, and a `branches` table `(root_id, head_id, name, is_main,
created_by, created_at)`.

1. **Every aeroplane is a node.** `create_aeroplane` bootstraps `root_id = self`, a
   `main` branch and `branch_id`; the migration backfilled the identical shape using
   `INSERT … RETURNING id`, because `lastrowid` is `None` on PostgreSQL.
2. **Exactly one `main` per lineage**, enforced by a **partial unique index**
   declared identically in the model and the migration so `create_all` (tests) and a
   migrated DB agree. `adopt_branch` must demote-then-flush.
3. **A snapshot is inserted *behind* the head**, not in front of it — the head keeps
   its id, UUID and every inbound reference, so the UI never re-points.
4. **The clone registry must be exhaustive.** Every table with a transitive FK to
   `aeroplanes` appears in exactly one of `CLONED_TABLES` (17) or `EXCLUDED_TABLES`
   (18), asserted by a coverage test that also checks disjointness and a non-empty
   reason per exclusion.
5. **Internal references are re-keyed; shared references are kept.**
   `loading_scenarios.component_overrides` are remapped through a `weight_id_map`
   (unmapped values pass through — they are COTS UUIDs); `flight_profile_id` and
   `servo.component_id` are shared library references; STEP paths are nulled.
6. **Exclusions are justified by category:** shared library, transient/recomputed,
   conversation, versioning meta, file-backed artefacts, caches.
7. **Never mutate destructively without a recovery point** (gh-1058): a destructive
   spar commit auto-snapshots first and **aborts the commit if the snapshot fails**.

## Consequences

- A version is *always* loadable because it is the same shape as a live aircraft:
  every endpoint, service and converter works on it unchanged, and schema migrations
  apply to history automatically.
- 🔴 **No storage-growth control** — every snapshot is a full row copy, taken
  automatically, with no retention policy or size accounting.
- **The FK graph is circular** (`aeroplanes.branch_id ↔ branches.root_id/head_id`),
  requiring `use_alter=True` on four constraints, a three-step flush dance on create,
  and a carefully ordered `discard_branch`, because SQLite has no deferrable FKs.
- 🔴 **The coverage test has a blind spot**: it introspects SQLAlchemy `ForeignKey`
  objects, so tables whose aeroplane reference is a plain `String`
  (`component_tree`, `construction_plans`, `construction_parts`) are invisible and
  must be maintained by hand.
- 🔴 **Immutability is not enforced on the CRUD path** — `_guard_immutable` has
  exactly one call site, so ordinary `PUT`s can mutate a frozen node. Fixed by
  `Q-VS-1` (a `get_aeroplane_for_write` resolver plus a `before_flush` guard).
- 🔴 Six further surface defects (lineage truncation in `discard_branch`, orphans
  invisible to `list_tree`, `compare` not diffing, integer-PK/UUID duality, the five
  dead `/design-versions` routes still mounted, `preview_png` never written) are
  catalogued in [`../code-analysis.md`](../code-analysis.md).

**Rejected:** copy-on-write with structural sharing — it would reduce storage but
break the property that makes this design work, namely that a version is a *plain*
aircraft every existing query already handles.

## Related

[ADR 0007](0007-copilot-proposes-human-adopts.md) ·
[`../state-machines.md`](../state-machines.md) §2–§4 · domain rules BR-35 … BR-42 ·
[`../questions.md`](../questions.md) §Q-VS-1, §Q-VS-3.
Evidence: commits `019b4f7b` (gh-901), `9faed52a` (gh-1058);
`alembic/versions/15f45e64a7c0_gh903_versioning_db_model.py`.
