# ai-copilot / proposal-adopt-discard — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).
> Branch mechanics: [`../../versioning/branch-model/design.md`](../../versioning/branch-model/design.md).

## Interface

| Symbol | Signature | Raises |
|---|---|---|
| `get_or_open_proposal` | `(db, live_aeroplane_id: int, message_id: int \| None = None) -> BranchModel` | propagates `versioning` errors |
| `_find_open_proposal` | `(db, live_aeroplane_id: int) -> BranchModel \| None` | — |
| `apply_edits` | `(db, proposal_aeroplane_uuid: str, ops: list[EditOp]) -> dict` | never for a single bad op |
| `discard_open_proposal` | `(db, live_aeroplane_id: int) -> bool` | propagates `discard_branch` errors |
| `compute_metrics_diff` | `(before: dict, after: dict) -> dict` | pure |
| `_COPILOT_BRANCH_PREFIX` | `= "copilot-proposal"` | |
| `_DIFF_KEYS` | 13 `(label, dot-path)` pairs | |

`apply_edits` returns `{"applied": [str], "rejected": [{op, error}], "metrics":
_metrics_payload(node)}`.
`_apply_design_edits` (the tool) returns `{"branch_id", "branch_uuid",
"applied", "rejected", "diff_proposal_branch", "diff_vs_live"}`.

## Main Flow

### F1 — `_apply_design_edits`, the tool-level orchestration 🟢

```
1  adapter = TypeAdapter(list[EditOp])
   validated_ops = adapter.validate_python(ops)
       except Exception -> return {"error": f"Invalid ops payload: {exc}"}   # NO branch opened

2  live_node = aeroplanes[aeroplane_id]        or return {"error": "Aeroplane ... not found"}

3  branch = get_or_open_proposal(db, aeroplane_id)
       except Exception -> logger.exception(...) ; return {"error": "Failed to open proposal branch: ..."}

4  proposal_node = aeroplanes[branch.head_id]  or return {"error": "Proposal branch head not found"}
   proposal_uuid = str(proposal_node.uuid)

5  pre_edit_metrics = _metrics_payload(proposal_node)     # baseline FROM THE CLONE
                                                          # (never the live node's stale context)

6  result = apply_edits(db, proposal_uuid, validated_ops)
       except Exception -> logger.exception(...) ; return {"error": "Failed to apply edits: ..."}

7  diff = compute_metrics_diff(pre_edit_metrics, result["metrics"])

8  return {branch_id, branch_uuid, applied, rejected,
           diff_proposal_branch: diff,
           diff_vs_live:        diff}          # 🟢 becomes a real live-vs-proposal diff (Q-CO-6)
```

Step 1 before step 3 is the ordering that matters: a malformed batch must not
leave an empty proposal branch behind. 🟢

### F2 — `get_or_open_proposal` 🟢

```
node    = aeroplanes[live_id]
root_id = node.root_id or node.id

branch = SELECT * FROM branches
         WHERE root_id = :root_id AND is_main = FALSE
           AND created_by = 'copilot' AND name LIKE 'copilot-proposal%'
         ORDER BY id DESC LIMIT 1
if branch: return branch                                   # reuse

name = _COPILOT_BRANCH_PREFIX + (f"-{message_id}" if message_id else "")
return create_branch(db, from_node_id=live_id, name=name, created_by="copilot")
```

`create_branch` (owned by `versioning`) performs the three-flush dance: clone the
live node into a **mutable** head with `predecessor_id = live_id`, insert the
`BranchModel` with `is_main=False`, then back-fill the head's `branch_id`. 🟢

🟢 Three latent problems lived in this query — all removed by the typed `branch_kind` column and the partial unique index (`Q-CO-12`):
`id DESC` + no uniqueness ⇒ duplicates are tolerated and older ones orphaned;
`created_by = 'copilot'` ⇒ a branch created with the documented `'ai'` would
never be found; `name LIKE 'copilot-proposal%'` ⇒ a human renaming the branch
detaches it and the next edit opens a second proposal.

### F3 — `apply_edits` 🟢

```
node = aeroplanes WHERE uuid = proposal_aeroplane_uuid
applied, rejected = [], []
wing_config_cache: dict[str, dict] = {}                 # per wing, MILLIMETRES

for op in ops:
    try:
        match op.type:
          "SetAssumption":
              design_assumptions_service.set_estimate(db, uuid, op.param, op.value)   # SI/deg
          "SetXsec":                                    # STATION index
              cfg = cache(op.wing)
              if 0 < op.index < n_segments: write BOTH seg[index-1].tip and seg[index].root
              elif op.index == 0:           write seg[0].root
              else:                         write seg[-1].tip
          "SetSegment":                                 # SEGMENT index
              cfg = cache(op.wing) ; update length_mm / sweep_mm / chord_tip_mm /
                                     dihedral_rel_deg / incidence_deg / tip airfoil
          "AddXsec":
              if op.at_index != n_xsecs: reject("mid-wing insertion is not supported; append
                                                 at the tip with at_index = n_xsecs")   🟢 mid-wing insert implemented (Q-CO-8)
              for seg in cfg.segments: seg.pop("tip_type", None)      # l.517-520 — MUST
              cfg.segments.append(new segment from chord/span/airfoil/twist/dihedral)
          "RemoveXsec":
              if not (1 <= op.index <= n_xsecs - 2): reject("interior stations only")
              merge seg[i-1] and seg[i]: length += length ; sweep += sweep    🟢 correct; comment wrong (Q-CO-7) (comment says
                                                                              "weighted avg")
          "SetWingParam":
              for seg in cfg.segments: seg.sweep_mm = op.sweep_mm ; seg.dihedral = op.dihedral
          "ReplaceWingConfig":
              validate WingConfigurationSchema(op.wing_config)
              put_wing_as_wingconfig(db, uuid, op.wing, op.wing_config, scale=0.001)  # NOW
              wing_config_cache.pop(op.wing, None)
              db.expire_all()
        applied.append(str(op))
    except Exception as exc:
        rejected.append({"op": op.model_dump(), "error": str(exc)})

for wing, cfg in wing_config_cache.items():
    put_wing_as_wingconfig(db, uuid, wing, cfg, scale=0.001)          # exactly once per wing

db.expire_all()          # put_* deletes-then-reinserts -> stale WingModel identities would
                         # make _metrics_payload (and a same-turn get_wing_geometry) read
                         # PRE-edit geometry

try:    recompute_assumptions(db, uuid)
except Exception as exc: logger.warning(...)                          # non-fatal

return {"applied": applied, "rejected": rejected, "metrics": _metrics_payload(node)}
```

The cache is what makes *"make the wing 10 % longer and taper it"* a single
coherent write instead of two competing ones. 🟢

### F4 — The `tip_type` strip 🟢

`create_wing_configuration()` processes segments in two passes: a middle pass for
segments whose `tip_type is None`, then a tip pass. If the old last segment keeps
`tip_type="flat"` when a new segment is appended, the **old** segment is
processed in the tip pass and the new winglet in the middle pass — physically
reordering the cross-sections. Stripping `tip_type` from every trailing segment
before the append restores the intended order. 🟢

### F5 — `discard_open_proposal` 🟢

```
branch = _find_open_proposal(db, live_id)
if branch is None: return False

db.flush()          # make pending state visible
db.expunge_all()    # detach EVERYTHING — otherwise the cascade delete raises
                    # InvalidRequestError: Can't attach instance <WingXSecSpareModel ...>;
                    # another instance with key (...) is already present in this session
branch = _find_open_proposal(db, live_id)      # re-resolve after the expunge
discard_branch(db, branch.id)                  # versioning: null inbound predecessors,
                                               # delete the branch row FIRST, then the nodes
return True
```

### F6 — `compute_metrics_diff` 🟢

```
_DIFF_KEYS = [("mass_kg", "total_mass_kg"),
              ("span_m",  "assumption_computation_context.span_m"),
              ("aspect_ratio", ...), ("cd0", ...), ("e_oswald", ...), ("ld_max", ...),
              ("x_np_m", ...), ("static_margin_pct", ...), ("v_stall_mps", ...),
              ("v_min_sink_mps", ...), ("v_cruise_mps", ...), ("cl_max", ...),
              ("wing_area_m2", ...)]                                   # 13

out = {}
for label, path in _DIFF_KEYS:
    b, a = navigate(before, path), navigate(after, path)
    if b is None and a is None: continue          # both missing -> omit
    if b == a:                  continue          # unchanged     -> omit
    out[label] = {"before": round6(b), "after": round6(a),
                  "delta": round6(a - b) if both numeric else None}
return out
```

### F7 — Adoption, which lives elsewhere 🟢

There is **no** adopt path in this module. The frontend's `useCopilotProposal`
(gh-939) detects the proposal by filtering the lineage tree for
`created_by === "copilot" && is_main === false`, and drives:

| Action | Call | Owner |
|---|---|---|
| adopt | `POST /branches/{id}/adopt` | `versioning` |
| discard | `DELETE /branches/{id}` | `versioning` |

Its docstring is explicit: *"Reuses `useLineageTree` and `useVersionActions` from
the shipped #907 versioning hooks — **no new API endpoints**."* 🟢

## Alternative Flows

- **Invalid ops payload:** error returned; **no branch opened**. 🟢
- **Live aeroplane missing:** `{"error": "Aeroplane <id> not found"}`. 🟢
- **`create_branch` fails:** logged with `logger.exception`, returned as an
  error dict. 🟢
- **Proposal head row missing** (a branch whose head was deleted):
  `{"error": "Proposal branch head not found"}`. 🟡
- **A single op fails:** collected into `rejected`; the batch continues. 🟢
- **All ops fail:** `applied` empty, `rejected` full, the branch still exists and
  an empty diff is returned. 🟡
- **Interior `AddXsec`:** implemented (`Q-CO-8`). 🟢
- **Out-of-range `RemoveXsec`:** rejected. 🟢
- **`ReplaceWingConfig` invalid:** rejected; the cache entry is untouched, so a
  previously cached edit for that wing is still written at the end. 🟡
- **Recompute fails:** warning; the apply result stands. 🟢
- **`discard_proposal` with no proposal:** `{"discarded": false}`. 🟢
- **Two proposal branches exist:** the newest is used and discarded; the older
  survives invisibly — impossible once the unique index lands (`Q-CO-12`). 🟢
- **The human renamed the branch:** the reuse query stops matching; the next edit
  opens a **second** proposal — prevented by the typed column plus unique index (`Q-CO-12`). 🟢
- **The human adopts while a turn is in flight:** the proposal becomes `main`
  and a subsequent tool call in the same turn reuses… nothing, because
  `is_main = False` no longer matches — so a **new** proposal is opened from the
  now-adopted design. 🟡 Not tested.

## Dependencies

- **`versioning`** — `create_branch`, `discard_branch`, `_metrics_payload`,
  `BranchModel`.
- **`wing-design`** — `put_wing_as_wingconfig(scale=0.001)` and
  `create_wing_configuration()`'s two-pass segment handling (the reason for the
  `tip_type` strip).
- **`mission-and-sizing`** — `design_assumptions_service` for `SetAssumption`
  and `recompute_assumptions` afterwards.
- **`app/schemas/copilot_edits.py`** — the validation gate.
- **`frontend-workbench`** — `useCopilotProposal` is the only adopt/discard UI.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| One disposable branch is the entire AI write surface | ADR 0007 | 🟢 |
| No adopt tool — the restriction is structural | `TOOL_REGISTRY` | 🟢 |
| Validate before opening the branch | `_apply_design_edits` step order | 🟢 |
| Reuse keys on the typed `branch_kind` column, one open proposal per root | `_find_open_proposal` | 🟢 (`Q-CO-12`) |
| Ops compose in a per-wing mm cache written once | `apply_edits` | 🟢 |
| `ReplaceWingConfig` bypasses the cache on purpose | its immediate write + evict | 🟢 |
| `expire_all` / `expunge_all` as correctness requirements | the two comments | 🟢 |
| The diff baseline comes from the clone, not the live node | step 5 comment | 🟢 |
| `diff_vs_live` carries a real live-vs-proposal diff | step 8 comment | 🟢 (`Q-CO-6`) |
| Adoption is delegated to the versioning REST surface and the UI | `useCopilotProposal` (gh-939) | 🟢 |

## Internal State

| State | Where | Lifetime |
|---|---|---|
| The proposal branch | `branches` (`created_by='copilot'`) | first write op → discard or adopt |
| The proposal head + its full subgraph | `aeroplanes` + 16 owned tables | a complete clone per proposal 🟡 (`Q-VS-2` owns retention) no size accounting |
| `wing_config_cache` | in-memory in `apply_edits` | one op batch |
| `pre_edit_metrics` | in-memory in `_apply_design_edits` | one tool call |

## Observability

- `logger.exception("_apply_design_edits: get_or_open_proposal failed")`. 🟢
- `logger.exception("_apply_design_edits: apply_edits failed")`. 🟢
- `logger.exception("_discard_proposal failed for aeroplane_id=%s")`. 🟢
- `logger.warning` on a failed post-apply recompute. 🟢
- `create_branch` / `discard_branch` log at INFO from `versioning`. 🟢
- 🔴 Nothing counts proposals opened, reused, discarded or adopted. **Not
  addressed by the validation interview**, and under ADR 0024 (single-user
  desktop) usage metrics have no consumer — left open rather than assumed away.
- 🟡 Rejected ops are not logged beyond the return value the model sees.
  `Q-CO-15` makes a **rejection with its reason** a first-class event in the
  compacted record, which covers the designer-facing half of this; the
  operator-facing log is not separately required at single-user scale.

## Risks and Gaps

**Four of these are one decision.** `Q-CO-12` (maintainer-answered) replaces the
`name LIKE 'copilot-proposal%'` string match with a typed
`branch_kind ∈ {main, manual, proposal}` column under a `CHECK` constraint
(`Q-CC-9`'s enforcement level), adds **at most one open proposal per `root_id`**
as a partial unique index — with direct precedent in the index already enforcing
one `is_main` per root — auto-closes empty proposals, and specifies the
adopt-during-turn rule.

- 🟢 **Duplicate proposals become impossible**, not merely tolerated: the partial
  unique index removes the "newest wins, older orphaned with its edits" failure
  entirely (`Q-CO-12`).
- 🟢 **A human rename is harmless.** The typed column replaces the `LIKE` query,
  so renaming a branch can no longer detach its proposal (`Q-CO-12`).
- 🟢 **`created_by='ai'` no longer interacts with reuse** — reuse keys on
  `branch_kind`, not on a `created_by` string (`Q-CO-12`; vocabulary fixed by
  `Q-CC-9` to `human` | `ai`).
- 🟢 **`message_id` is supplied and the provenance link is wired** (`Q-CO-1`,
  maintainer-answered). The copilot passes the turn's message id, so
  `provenance_message_id` and the branch-name suffix stop being inert and the
  version graph resolves back to the conversation turn. This is what makes
  ADR 0007's accountability real rather than intended.
- 🟢 **`diff_vs_live` gets a real live-vs-proposal diff** (`Q-CO-6`): the field
  is made to match its name rather than renamed, because a reviewing human needs
  exactly that comparison before adopting (ADR 0007). The system-prompt paragraph
  warning the model off it can then be deleted.
- 🟢 **Mid-wing `AddXsec` is implemented** (`Q-CO-8`). Not a convenience: a
  trailing-edge device is defined over a **segment**, so a wing built without
  control surfaces has no segment boundary where one is wanted, and only a
  mid-span insert can create one. A tip-append cannot.
- 🟢 **`RemoveXsec`'s sum is correct and the comment is wrong** (`Q-CO-7`,
  expert consensus endorsed by the maintainer): sweep is a chordwise *distance*
  along an invariant `xDir`, so merging two segments adds their sweeps. The
  comment saying "weighted avg" is corrected, not the code.
- 🟡 **Every proposal is a full subgraph clone** with no retention, prune or size
  accounting. `Q-VS-2` decided the growth policy for snapshots generally; the
  copilot compounds it by cloning per proposal. Carried as INFERRED here because
  the retention rule is owned by `versioning`, not decided in this unit.
- 🟢 **Adopt-during-turn is specified** and **an empty proposal auto-closes**
  (`Q-CO-12`), so the UI can no longer show a proposal containing no changes.
