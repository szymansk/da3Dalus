# gh-1151 — deleting an aeroplane follows the version lineage and really deletes

| | |
|---|---|
| Issue | [#1151](https://github.com/szymansk/da3Dalus/issues/1151) |
| PR | [#1196](https://github.com/szymansk/da3Dalus/pull/1196) |
| Merged | adf8cd3a, 2026-10-24 |

## Vigência

Vigente desde 2026-10-24.

## Summary

`DELETE /aeroplanes/{id}` answered 200 while the commit in `get_db()` (after the
response) failed, so nothing was deleted. Causes: branch rows nulled instead of deleted
(`branches.root_id/head_id` NOT NULL), `flight_envelopes` without delete cascade, and rows
without ORM cascade (operating points and sets, component tree, construction parts,
tessellation cache) surviving and being inherited by the next aeroplane that reuses the
integer id.

Delete now follows the node's place in the lineage:

| Node | Result |
|---|---|
| head of the **main** branch | whole lineage removed: all branches, all nodes with that root, everything they own |
| head of a **side** branch | `discard_branch` (same implementation) |
| lineage root no longer on the main branch | 409 |
| immutable snapshot | 409 |
| row without branch (pre-versioning) | the single node |

One implementation of what a node owns: `aeroplane_version_service.delete_nodes` with
`aeroplane_purge.purge_node_dependents`, used by `delete_aeroplane`, `discard_branch` and
`delete_lineage`. The service flushes inside its try-block so a failure is returned as an
error response.

## Impacto por artefato da extração

| Unit | Section | Tipo | Delta |
|---|---|---|---|
| `state-machines.md` | lines 134 and 164 (versioning transitions) | `regra-alterada` | `MutableHead --> Deleted : delete_aeroplane()` is no longer "ORM cascade + STEP cleanup" for a single node: main head deletes the lineage, side head is `discard_branch`, a root off main and any snapshot answer 409. |
| `aeroplane-core/aeroplane-crud/requirements.md` | BR-AC5 | `regra-alterada` | The cascade list also covers flight envelopes, operating points and sets, component tree, construction parts and tessellation cache, and the lineage rows above. |
| `versioning/` (BR-VR9 ordering) | `discard_branch` | `regra-alterada` | The same branch-first ordering now also applies to the aeroplane delete; `discard_branch` additionally purges the non-cascading rows. |
| REST contract | `DELETE /aeroplanes/{id}` | `delta-de-contrato-externo` | New 409 responses (snapshot, root off main); a main head removes its whole lineage. |

## Decisions now implemented

- Maintainer answer **A** on #1151, 2026-10-22:
  https://github.com/szymansk/da3Dalus/issues/1151#issuecomment-6340052195
  `app/services/aeroplane_service.py` (`_delete_node_with_versioning`),
  `app/services/aeroplane_version_service.py` (`delete_nodes`, `delete_lineage`),
  `app/services/aeroplane_purge.py`.

## Approved departures

- `state-machines.md:134` and `:164` (single-node delete with ORM cascade) no longer hold →
  superseded by **`Q-VS-9`** (`questions.md`): maintainer answer A on #1151 (2026-10-22) and the
  confirmation of the 409 for a lineage root off main (2026-10-24).

## Marker candidates for the next re-extraction

A hint, not an authority. 🟢 candidates: the table in Summary (read from the code,
exercised by `app/tests/test_delete_aeroplane_persistence.py`).
