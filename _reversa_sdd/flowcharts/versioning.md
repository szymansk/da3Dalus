# Flowcharts — versioning

## 1. The data model — a DAG of real aeroplane rows

```mermaid
erDiagram
    AEROPLANES ||--o{ AEROPLANES : "predecessor_id (self FK)"
    AEROPLANES ||--o{ AEROPLANES : "root_id (self FK, root points at ITSELF)"
    BRANCHES }o--|| AEROPLANES : "root_id -> lineage root"
    BRANCHES }o--|| AEROPLANES : "head_id -> the mutable node"
    AEROPLANES }o--|| BRANCHES : "branch_id (NULL = legacy row)"
    AEROPLANES }o--o| COPILOT_MESSAGES : "provenance_message_id (AI cursor)"

    AEROPLANES {
        int id PK
        uuid uuid
        int branch_id FK "use_alter"
        int predecessor_id FK "use_alter, self"
        int root_id FK "use_alter, self"
        bool is_immutable "False = editable head"
        string version_label
        text version_note
        string created_by "human | ai | copilot"
        int provenance_message_id FK
        text preview_png "never written"
    }
    BRANCHES {
        int id PK
        int root_id FK
        int head_id FK
        string name "no DB uniqueness"
        bool is_main "exactly ONE True per root_id"
        string created_by
        datetime created_at
    }
```

The four FKs between `aeroplanes` and `branches` form a **cycle**, which is why
all of them are declared `use_alter=True` (emitted as separate `ALTER TABLE`
statements). SQLite has no deferrable FKs, so `discard_branch` must NULL
inbound `predecessor_id` references by hand.

## 2. Lineage bootstrap — every aeroplane is a node

```mermaid
sequenceDiagram
    participant API as POST /aeroplanes
    participant SVC as aeroplane_service.create_aeroplane
    participant DB as DB

    API->>SVC: name
    SVC->>DB: INSERT aeroplanes (name, is_immutable=False)
    SVC->>DB: flush -> obtain id
    SVC->>DB: UPDATE aeroplanes SET root_id = id   (points at ITSELF)
    SVC->>DB: INSERT branches (root_id=id, head_id=id,<br/>name='main', is_main=True, created_by='human')
    SVC->>DB: flush -> obtain branch.id
    SVC->>DB: UPDATE aeroplanes SET branch_id = branch.id
    Note over DB: The gh-903 migration backfilled EXACTLY this shape<br/>for every pre-existing aeroplane, using<br/>INSERT ... RETURNING id (lastrowid is None on PostgreSQL).
```

## 3. `snapshot` — the counter-intuitive one

```mermaid
flowchart LR
    subgraph BEFORE["before"]
        P0["[old_pred]"] --> H0["[head] id=H<br/>mutable"]
    end
    subgraph AFTER["after"]
        P1["[old_pred]"] --> S1["[snapshot] id=S<br/>is_immutable=True<br/>version_label, note,<br/>provenance_message_id,<br/>created_by='human'"]
        S1 --> H1["[head] id=H — UNCHANGED<br/>predecessor_id = S"]
    end
    BEFORE ==> AFTER
```

The frozen copy is inserted **behind** the head, so the head keeps its `id`,
`uuid` and every inbound reference — the UI never has to re-point after a
snapshot.

```mermaid
flowchart TD
    A["snapshot(db, node_id, label, note, provenance_message_id)"] --> B{"node exists?"}
    B -->|no| B1["NotFoundError -> 404"]
    B -->|yes| C{"node.is_immutable?"}
    C -->|yes| C1["ValidationError -> 422<br/>'Cannot mutate an immutable snapshot node'"]
    C -->|no| D["resolved_root_id = head.root_id or head.id"]
    D --> E["clone_aeroplane_subgraph(head,<br/>immutable=True,<br/>branch_id=head.branch_id,<br/>predecessor_id=head.predecessor_id,  <-- INHERITS the old chain<br/>root_id=resolved_root_id)"]
    E --> F["set version_label / note / provenance_message_id<br/>created_by = 'human'  (HARD-CODED)"]
    F --> G["flush -> snapshot.id"]
    G --> H["head.predecessor_id = snapshot.id ; flush"]

    style B1 fill:#511,color:#fff
    style C1 fill:#511,color:#fff
```

## 4. Branch / adopt / restore / discard

```mermaid
flowchart TD
    subgraph CB["create_branch(from_node_id, name, created_by)"]
        C1["root_id = source.root_id or source.id"] --> C2["clone(immutable=False,<br/>branch_id=None,<br/>predecessor_id=source.id, root_id)"]
        C2 --> C3["new_head.created_by = created_by ; flush"]
        C3 --> C4["INSERT branches(root_id, head_id=new_head.id,<br/>name, is_main=False, created_by)"]
        C4 --> C5["back-fill new_head.branch_id = branch.id"]
    end

    subgraph AD["adopt_branch(branch_id)"]
        A1{"branch.is_main?"} -->|yes| A2["ConflictError -> 409<br/>'already the main branch'"]
        A1 -->|no| A3["find current main WHERE root_id = ? AND is_main"]
        A3 --> A4["current_main.is_main = False ; FLUSH"]
        A4 --> A5["branch.is_main = True ; flush"]
        A6["DEMOTE FIRST so the partial unique index<br/>uq_branches_one_main_per_root never sees two True"]
        A4 -.- A6
    end

    subgraph RS["restore(snapshot_node_id, name, created_by)"]
        R1{"node.is_immutable?"} -->|no| R2["ValidationError -> 422<br/>'restore() requires an immutable snapshot'"]
        R1 -->|yes| R3["create_branch(from snapshot)<br/>default name = 'restore/&lt;version_label&gt;'"]
    end

    subgraph DC["discard_branch(branch_id)"]
        D1{"is_main?"} -->|yes| D2["ConflictError -> 409"]
        D1 -->|no| D3{"sibling branch count <= 1?"}
        D3 -->|yes| D4["ConflictError -> 409<br/>'only branch of a lineage root'"]
        D3 -->|no| D5["collect nodes WHERE branch_id = ?"]
        D5 --> D6["UPDATE aeroplanes SET predecessor_id = NULL<br/>WHERE predecessor_id IN (those ids)"]
        D6 --> D7["db.delete(branch) FIRST<br/>else SQLAlchemy nulls branches.head_id (NOT NULL) via the relationship"]
        D7 --> D8["db.delete(node) for each — ORM cascade removes the subgraph"]
    end

    style A2 fill:#511,color:#fff
    style R2 fill:#511,color:#fff
    style D2 fill:#511,color:#fff
    style D4 fill:#511,color:#fff
```

## 5. The clone engine — 17 tables, ordered and re-keyed

```mermaid
flowchart TD
    S["clone_aeroplane_subgraph(source, immutable, branch_id,<br/>predecessor_id, root_id)"] --> T1

    T1["1. aeroplanes — NEW uuid4<br/>KEEP flight_profile_id (shared library ref)<br/>deep-copy xyz_ref + assumption_computation_context<br/>version_label/note/created_by/provenance/preview = None"]
    T1 --> T2["2. weight_items  -> builds weight_id_map old_id -> new_id"]
    T2 --> T3["3. wings -> wing_xsecs -> wing_xsec_details<br/>-> spares, turbulator (1:1), TED -> ted_servo<br/>KEEP servo.component_id (shared COTS ref)"]
    T3 --> T4["4. fuselages -> fuselage_xsecs<br/>step_path / solid_step_path -> NULL (regenerated)"]
    T4 --> T5["5. mission_objective (1:1)"]
    T5 --> T6["6. design_assumptions (estimate + calculated + active_source)"]
    T6 --> T7["7. aircraft_computation_config (1:1)"]
    T7 --> T8["8. stability_results (incl. computed_at, geometry_hash)"]
    T8 --> T9["9. loading_scenarios — component_overrides REMAPPED"]
    T9 --> T10["10. component_tree — aeroplane_id = str(clone.uuid)<br/>parent_id remapped (2-pass)"]
    T10 --> F["db.flush() ; return clone  (NO commit — get_db owns it)"]

    T9 -.-> RM["_remap_component_overrides:<br/>walk toggles / mass_overrides / position_overrides,<br/>rewrite component_uuid via weight_id_map.<br/>Unmapped values pass through — they are shared COTS UUIDs."]
    T10 -.-> CT["_clone_component_tree:<br/>pass 1 = insert ALL with parent_id=None, collect id_map<br/>pass 2 = UPDATE parent_id from id_map<br/>parent NOT in map -> stays None + WARNING naming both ids<br/>(explicitly chosen over silent data loss)"]
```

## 6. Clone coverage registry

```mermaid
flowchart LR
    subgraph CL["CLONED_TABLES (17)"]
        direction TB
        L1["aeroplanes · wings · wing_xsecs · wing_xsec_details"]
        L2["wing_xsec_spares · ..._trailing_edge_devices · ..._turbulators · ..._ted_servos"]
        L3["fuselages · fuselage_xsecs · weight_items · mission_objectives"]
        L4["design_assumptions · aircraft_computation_config · stability_results"]
        L5["loading_scenarios · component_tree (STRING FK)"]
    end
    subgraph EX["EXCLUDED_TABLES (18, each with a mandatory reason)"]
        direction TB
        E1["shared library: rc_flight_profiles, components, component_types,<br/>airfoils, airfoil_low_re, rc_flight_profile_entries, mission_presets"]
        E2["transient: operating_points, operating_pointsets, flight_envelopes"]
        E3["conversation: copilot_messages"]
        E4["versioning meta: branches"]
        E5["construction (string FK, file-backed): construction_plans, construction_parts"]
        E6["caches: tessellation_cache, avl_geometry_files"]
        E7["non-tables: avl_geometry_events, stability_events, alembic_version"]
    end

    T["test_aeroplane_clone_coverage.py"] -->|"BFS over SQLAlchemy ForeignKey objects<br/>every discovered table MUST be classified<br/>sets must be DISJOINT<br/>every exclusion needs a non-empty reason"| CL
    T --> EX

    BS["BLIND SPOT: the BFS cannot see STRING aeroplane refs.<br/>component_tree / construction_plans / construction_parts<br/>are registered BY HAND. A new string-FK table will NOT be caught."]
    T -.- BS
```

## 7. Provenance — who created this node

```mermaid
flowchart TD
    subgraph W["Writers of created_by"]
        W1["aeroplane_service.create_aeroplane -> 'human'"]
        W2["aeroplane_version_service.snapshot -> 'human' (hard-coded)"]
        W3["BranchRequest.created_by -> 'human' default<br/>schema documents 'human' | 'ai'"]
        W4["copilot_apply_service.get_or_open_proposal -> 'copilot'"]
    end
    W1 --> G["created_by column — NO enum, NO constraint"]
    W2 --> G
    W3 --> G
    W4 --> G
    G --> BUG["A UI filtering on 'ai' misses every copilot branch."]
    style BUG fill:#511,color:#fff
```

### The AI proposal-branch lifecycle (detail belongs to Cluster E)

```mermaid
sequenceDiagram
    participant U as User
    participant CP as copilot_apply_service
    participant VS as aeroplane_version_service
    participant DB as DB

    U->>CP: copilot proposes an edit
    CP->>CP: root_id = node.root_id or node.id
    CP->>DB: SELECT branches WHERE root_id=? AND NOT is_main<br/>AND created_by='copilot' AND name LIKE 'copilot-proposal%'
    alt an open proposal exists
        DB-->>CP: reuse it (ONE open proposal per lineage)
    else none
        CP->>VS: create_branch(live_head, 'copilot-proposal-<msg_id>', created_by='copilot')
        VS->>DB: clone subgraph + INSERT branches
    end
    CP->>CP: apply_edits(proposal_uuid, ops) -> recompute_assumptions
    CP->>CP: _metrics_payload(after) for the before/after diff

    alt user rejects
        CP->>CP: db.flush() ; db.expunge_all()
        Note over CP: expunge is REQUIRED — put_wing_as_wingconfig does<br/>delete-then-reinsert in the same session; the stale<br/>WingXSecSpareModel instances break the cascade delete with<br/>"Can't attach instance ... already present in this session"
        CP->>VS: discard_branch(proposal_branch_id)
    else user accepts
        CP->>VS: adopt_branch(proposal_branch_id) — old main demoted
    end
```

## 8. Auto-snapshot before a destructive edit (gh-1058)

```mermaid
flowchart TD
    A["POST spar insert (dry_run=False)"] --> B{"destructive?<br/>segment SPLIT or spare REPLACE"}
    B -->|yes| C["aeroplane_version_service.snapshot(db, aeroplane.id,<br/>label='Before spar insert')"]
    C --> D{"snapshot succeeded?"}
    D -->|no| E["EXCEPTION PROPAGATES -> get_db() rolls back<br/>'never mutate without a recovery point'"]
    D -->|yes| F["_persist_front_split / _persist_spares"]
    F --> G["SparInsertResponse.snapshot_id -> UI one-click revert"]
    B -->|no| F

    style E fill:#511,color:#fff
```

## 9. REST surface + the retired parallel system

```mermaid
flowchart TD
    subgraph LIVE["ACTIVE — gh-905 (integer PK addressed)"]
        V1["POST /aeroplanes/{id}/snapshot -> 201 VersionNode"]
        V2["POST /aeroplanes/{id}/branch -> 201 BranchOut"]
        V3["POST /branches/{id}/adopt -> 200"]
        V4["POST /aeroplanes/{snapshot_id}/restore -> 201"]
        V5["PATCH /branches/{id} (rename) -> 200"]
        V6["DELETE /branches/{id} -> 204"]
        V7["GET /lineages/{root_id}/tree -> TreeOut (+ computed is_head)"]
        V8["GET /aeroplanes/compare?a=&b= -> CompareOut"]
        V9["GET /aeroplanes?heads_only=true (DEFAULT)<br/>heads + legacy branch_id IS NULL rows<br/>+ branch_name, is_main_branch"]
    end

    subgraph DEAD["RETIRED but STILL MOUNTED (aeroplane/__init__.py:41)"]
        D1["GET/POST /aeroplanes/{uuid}/design-versions"]
        D2["GET/DELETE /aeroplanes/{uuid}/design-versions/{vid}"]
        D3["GET .../{a}/diff/{b}"]
        D4["ALL five call design_version_service stubs that<br/>unconditionally raise NotFoundError -> a misleading 404"]
        D1 --> D4
        D2 --> D4
        D3 --> D4
    end

    M["gh-903 migration DROPPED the design_versions table<br/>(downgrade re-creates it EMPTY — snapshots were never back-migrated)"]
    M -.- DEAD

    ID["ID DUALITY: every versioning route takes an INTEGER PK<br/>while the rest of v2 addresses aeroplanes by UUID.<br/>_get_node_by_uuid exists in the service and has NO caller."]
    LIVE -.- ID

    style DEAD fill:#511,color:#fff
```
