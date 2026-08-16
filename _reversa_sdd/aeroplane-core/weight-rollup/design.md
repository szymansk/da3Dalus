# weight-rollup — Technical Design

> Use-case design, nested under the module [`aeroplane-core`](../design.md).
> Focuses on HOW the use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full module-level endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Service surface — `app/services/component_tree_service.py` 🟢

| Symbol | Signature / purpose | Line |
|---|---|---|
| `_calculate_own_weight` | `(node, …) -> tuple[float \| None, str]` — precedence chain → `(grams, source)` | l.461-474 |
| COTS branch | `component.mass_g × quantity` | l.432-439 |
| Calculated branch | density formula, print-type dependent | l.442-458 |
| `_roll_up_weights` | post-order total + status ladder | l.82-120 |
| own-weight pre-computation | one `id → (grams, source)` dict built before the recursion | l.133-137 |
| `get_aircraft_total_weight_kg` | `(db, aeroplane_uuid) -> float \| None` — sum over roots, grams → kg | l.381-403 |
| `_sync_aircraft_mass` | `(db, aeroplane_uuid) -> None` — fire-and-forget push into `mass_cg_service` | l.362-378 |

### REST surface 🟢

| Method | Path | Operation | Status codes |
|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/component-tree/weight` | aircraft total weight in kg | 200 · 404 · 500 |

The computed weight fields also ride on `GET /aeroplanes/{id}/component-tree`,
whose route is owned by
[`component-tree`](../component-tree/design.md).

### Computed read-only fields 🟢

| Field | Unit | Rule |
|---|---|---|
| `own_weight_g` | grams | precedence chain: `override` → `cots` → `calculated` → `none` |
| `weight_source` | — | `"override"` \| `"cots"` \| `"calculated"` \| `"none"` |
| `total_weight_g` | grams | own + Σ children (post-order) |
| `weight_status` | — | `"valid"` \| `"partial"` \| `"invalid"` per the ladder below |
| `total_weight_kg` (route only) | kilograms | Σ roots ÷ 1000, or `null` for an empty tree |

### Input fields consumed 🟢

`weight_override_g` (grams), `component_id` + `quantity` (COTS),
`volume_mm3` / `area_mm2`, `material_id` (→ `density_kg_m3`), `print_type`
(`"volume"` \| `"surface"`), `print_resolution_mm` (default **0.4**),
`scale_factor`.

## Main Flow

### F1 — Own-weight resolution (`_calculate_own_weight`, l.461-474) 🟢

Strict precedence, first match wins:

```
1. weight_override_g is not None
       -> (weight_override_g, "override")

2. node is COTS with a resolvable component            (l.432-439)
       -> (component.mass_g * quantity, "cots")

3. node is a CAD shape with a material density         (l.442-458)
       surface print:  area_mm2 * print_resolution_mm * density_kg_m3 / 1e6 * scale_factor
       volume  print:  volume_mm3                     * density_kg_m3 / 1e6 * scale_factor
       print_resolution_mm defaults to 0.4
       -> (grams, "calculated")

4. otherwise
       -> (None, "none")
```

The `/ 1e6` divisor is the unit bridge: mm³ × kg/m³ ÷ 1e6 = grams. Both formulas
end with `× scale_factor`. 🟢

### F2 — Pre-computation (`get_tree`, l.133-137) 🟢

Before any traversal, one pass over the loaded rows builds

```
own = { node.id: _calculate_own_weight(node) for node in rows }
```

so `_roll_up_weights` performs **no database access at all**. This is what makes
the tree read a constant number of statements regardless of node count. 🟢

### F3 — Roll-up (`_roll_up_weights`, l.82-120) 🟢

Post-order traversal — children are resolved before their parent:

```
total_weight_g(node) = (own_weight_g or 0) + Σ total_weight_g(children)

weight_status:
  leaf      -> "valid"   if own source != "none"
               "invalid" otherwise

  non-leaf  -> all children valid   -> "valid"
               all children invalid -> "partial" if own weight present
                                       "invalid" otherwise
               mixed                -> "partial"
```

Note the asymmetry that makes the ladder honest: a missing own weight
contributes `0` to the arithmetic but never upgrades the status. A `valid` total
therefore means "every contributing node had a real source", not merely "the sum
is a number". 🟢

### F4 — Aircraft total (`get_aircraft_total_weight_kg`, l.381-403) 🟢

1. Load the tree for the aeroplane UUID.
2. Sum own + recursive children weights over every `parent_id IS NULL` root, in
   grams.
3. Divide by 1000.
4. **Return `None` for an empty tree** — so the caller clears the mass
   `calculated_value` instead of writing a zero (ADR 0012).

### F5 — Mass sync (`_sync_aircraft_mass`, l.362-378) 🟢

```
def _sync_aircraft_mass(db, aeroplane_uuid):
    try:
        from app.services import mass_cg_service      # lazy: breaks the import cycle
        mass_cg_service.sync_component_tree_to_mass(db, aeroplane_uuid)
    except Exception:
        logger.exception(...)                          # swallowed by design
```

Two deliberate properties, both documented in the docstring:

- the **lazy import** breaks the `component_tree_service ↔ mass_cg_service`
  cycle — `mass_cg_service` imports this module at module level;
- the **bare except** guarantees a failed sync never blocks tree CRUD.

It is called from every structural write in
[`component-tree`](../component-tree/design.md): create, update, delete and move.

## Alternative Flows

- **Aeroplane not found:** `NotFoundError` → **404** with the `not_found`
  envelope via `_raise_http_from_domain`.
- **Empty tree on `GET /weight`:** **200** with `total_weight_kg = null` — not
  `0`, and not a 404. 🟢
- **Node with no usable weight source:** `(None, "none")`; the node is `invalid`
  and drags its parent to `partial`, without raising. 🟢
- **COTS node whose component is missing or has no `mass_g`:** falls through the
  chain to `(None, "none")` rather than raising. 🟡 INFERRED from the
  first-match-wins structure.
- **CAD shape without a `material_id` or density:** the calculated branch does
  not fire, so the node falls through to `"none"`. 🟡
- **Mass sync failure on a tree write:** caught in `_sync_aircraft_mass`, logged,
  the CRUD response is unaffected. 🟢
- **Unexpected exception in the weight route:** defensive
  `except Exception → 500`. 🟢

## Dependencies

- **[`component-tree`](../component-tree/design.md)** — supplies the assembled,
  ordered hierarchy this use case decorates, and calls `_sync_aircraft_mass` from
  every write.
- **`components` catalogue** — `component.mass_g` for COTS nodes and
  `density_kg_m3` for the material referenced by `material_id`.
- **`mass-and-balance` (`mass_cg_service`)** — pulled in via a **lazy import
  inside the function** to break the import cycle; receives the tree weight as
  the mass assumption's `calculated_value`.
- **`app/db/session.py` (`get_db`)** — owns the transaction (ADR 0009).
- **ADR 0012** — design warnings instead of silent fallbacks; the source of the
  `null`-not-`0` rule and of the `weight_status` ladder's existence.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Own weight is a precedence chain with an explicit provenance label, not a single nullable column | `_calculate_own_weight:461-474` | 🟢 |
| An absent value is reported as `null`, never as a fabricated `0` | `get_aircraft_total_weight_kg:381-403`; ADR 0012 | 🟢 |
| Incompleteness is carried by a separate `weight_status` rather than by nulling the total | `_roll_up_weights:82-120` | 🟢 |
| Totals and statuses are computed at read time, never persisted | `_roll_up_weights:82-120` (no writes) | 🟢 |
| Own weights are pre-computed into a dict so the recursion is query-free | `component_tree_service.py:133-137` | 🟢 |
| Best-effort side effects never fail the primary operation | `_sync_aircraft_mass:362-378` | 🟢 |
| The service↔service import cycle is broken by a lazy import rather than by extracting a third module | `_sync_aircraft_mass:362-378` | 🟢 |
| Grams inside the tree, kilograms only at the aircraft boundary | `get_aircraft_total_weight_kg:381-403` | 🟢 |
| `print_resolution_mm` defaults to 0.4 rather than being required | `_calculate_own_weight:442-458` | 🟢 |

## Internal State

The use case holds **no** state of its own. It reads the weight-bearing columns
of `component_tree` and derives everything else per request:

- `own_weight_g`, `weight_source`, `total_weight_g`, `weight_status` and
  `total_weight_kg` are all computed and discarded after serialisation;
- the only *write* it causes is indirect — the mass `calculated_value` inside
  `mass-and-balance`, via the fire-and-forget sync.

## Observability

- `logger.exception` inside `_sync_aircraft_mass` on the swallowed failure — this
  is the **only** place a mass-sync problem becomes visible. 🟢
- `logger.exception` on 5xx from the weight route; 4xx are logged at INFO by the
  global handler (`app/main.py`). 🟢
- No metrics, traces or structured event emission. In particular, there is **no**
  counter for how often a tree read produces `partial` or `invalid` statuses,
  so silent BoM incompleteness is only visible in the payload. 🟡

## Risks and Gaps

- 🟢 **Read-side depth limiting is added** (`Q-AC-3`). `_roll_up_weights`
  assumes acyclicity and the `move_node` write guard alone is not sufficient;
  a cycle from direct SQL or a future bulk endpoint currently causes unbounded
  recursion on every read.
- 🟡 **A failing mass sync emits a `DesignWarning` instead of being swallowed**
  (`Q-AC-7`), while still not blocking tree CRUD. A bare `except Exception:`
  with only a log line is the undeclared degradation `P-WARN-0` forbids, and a
  stale mass model is a substituted value the user is never told about. Derived
  from the policy rather than decided directly, so INFERRED.
- 🟡 **`GET /weight` declares an incomplete tree through the shared `warnings`
  channel**, not a bespoke coverage field (`Q-AC-8`). The kilogram total alone
  cannot distinguish a fully-specified aircraft from one whose tree is mostly
  `invalid`; `weight_status` exists only on the full tree read today. Derived
  from `P-WARN-0` with `Q-MB-1`, so INFERRED.
- 🟡 **Zero-mass and missing-mass COTS components are indistinguishable** once a
  component with `mass_g = 0` is referenced: the node reports `0 g` with source
  `"cots"` and status `valid`.
- 🟡 **`scale_factor` and `quantity` are unbounded.** Nothing in the chain
  rejects a negative `scale_factor` or `quantity`, which would produce a negative
  contribution to the total.
