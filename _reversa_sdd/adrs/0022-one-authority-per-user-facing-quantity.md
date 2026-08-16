# ADR 0022 — One authority per user-facing quantity

- **Status:** Accepted — generalises [ADR 0004](0004-one-aero-truth-per-aircraft.md). **Always a review criterion.**
- **Decided:** 2026-08-13 → 2026-08-14, during the specification validation interview
- **Deciders:** Marc Szymanski (maintainer); the sizing rulings ratified by the domain-expert round
- **Confidence:** 🟢 CONFIRMED (fifteen catalogued instances with code references, commit provenance and measured divergences)

## Context

ADR 0004 already says one aircraft has exactly one aerodynamic truth, and states
the rationale in one line: **it is not the computation that diverges, it is the
definition.** But it scopes the rule to four aerodynamic scalars. The same defect
recurs across the whole system: at least **fifteen** separate questions turn out to
be one sentence — *two code paths produce the same user-facing number, and nothing
decides which is right.*

The mechanism is a process failure, not a design one (`Q-MB-1`): `weight_items`
arrived 2026-04-12 in a **bulk scaffold commit implementing six unrelated resources
at once**, whose "ticket" identifiers are pencil.dev wireframe element IDs rather
than GitHub issues; the properly ticketed `component_tree` arrived two days later
with 13 tests, and neither commit references the other. The same scaffold produced
the five dead `design-versions` routes. **Wireframe-driven bulk scaffolds are a
recurring generator of ownerless surfaces that a properly designed feature later
supersedes.**

**The confirmed instances and their resolutions:**

| Quantity | Question | The divergence | Resolution |
|---|---|---|---|
| Aircraft **mass** | `Q-MB-1` | `weight_items` and the component tree both write `design_assumptions["mass"].calculated_value` with no arbitration — **the same edits in a different order yield a different mass**, and a battery in both places is double-counted | The component tree is authoritative; `weight_items` becomes a read-only view and is retired |
| **`cd0`** | `Q-AA-1` | `recompute_assumptions` writes the parasite split; `stability_service._auto_populate_cd0` (`:257-281`) writes total `result.CD` on a different trigger — on a cambered wing this collapses (L/D)max from ~24 to ~17, read by nine consumers | `_auto_populate_cd0` deleted outright |
| **Control-surface names** | `Q-WD-1` (bug #955) | The gh-772 canonical `[{role}]{axis}_{wing_key}_{xsec_index}` versus the raw TED name from the DB, keyed on by three consumers | `control_surface_mixing` owns a resolver that trim, retrim and stability are **required** to call |
| **Settings / version** | `Q-CC-4` | Two classes named `Settings` on the same `.env`, with three settings escaping both via bare `os.getenv` (`SQLALCHEMY_DATABASE_URL`, `LOG_LEVEL`, `DISPLAY_CONSTRUCTION_STEP`); a module singleton **and** an `lru_cache`d `get_settings()` returning a *different object*; three version strings — `1.0.0`, `0.1.0` (`/health`), `2.0.0` (OpenAPI) | One class, one instance, one version source derived from `pyproject.toml` |
| **Component taxonomy** | `Q-PT-13` ④ | `_VALID_COMPONENT_TYPES` (`cots_import.py:26-40`) duplicates `DEFAULT_SEED_TYPES` (`component_type_service.py:331`) — 12 names maintained by hand twice | The importer reads the registry from the database at runtime |
| **Landing distance**, **`t_static_N`** | `Q-MS-2` | Roskam §3.4 on `GET /field-lengths` versus the gh-477 energy balance — **35.5 m against 52.5 m for the same 1.5 kg trainer, 48 % apart, both labelled "landing distance"**; `t_static_N` lives in both `mission_objectives` and a same-named assumption | The energy balance is authoritative and `GET /field-lengths` delegates to it; `mission_objectives.t_static_N` wins and the assumption row is deleted (`matching_chart.py:83` re-pointed) |
| **`target_static_margin`** | `Q-MS-14` | Three defaults: `0.12` seeded, an inline `0.10` in `sm_suggestions.py:74`, and whatever the active mission preset wrote | Seeded default becomes `0.10`; precedence *user edit > mission preset > seeded default* is the documented contract; the inline fallback is deleted |
| **`created_by`** | `Q-CC-9` | Four writers, three vocabularies — the column comment documents `'human' \| 'ai'`, `copilot_apply_service` writes `'copilot'`, legacy rows are `NULL`. **A UI filter on `'ai'` misses every copilot branch** | Class/detail split: `created_by ∈ {human, ai}` plus a separate `created_by_agent`, with DB `CHECK` constraints |
| **`power_to_weight`** | `Q-MS-1` | The catalogue says W/kg (default `220.0`); seven of nine presets carry T/W-shaped `0.0`–`1.4`, so `trainer` declares a **0.5 W/kg** aircraft where a real trainer is 100–150 W/kg | W/kg is canonical; the seven presets are **re-authored**, not converted (T/W and W/kg are not inter-convertible without propeller efficiency and airspeed) |
| **RC sizing defaults** | `Q-PT-8` | `e 0.75 / AR 7.0 / S_ref 0.25` in the solution space versus `e 0.8 / AR 8.0 / S_ref 0.5` in the catalog sweep — one module sizing the same context-less aircraft two ways | Both sets are removed rather than reconciled; a missing key emits an `error`-severity `DesignWarning` |
| **`g`, `ρ`** | `Q-MB-8`, `Q-PT-9` | `GRAVITY = 9.81` against `G = 9.80665`; `RHO = 1.225` duplicated and *"kept in sync by comment"*; `_air_density = 1.225·exp(−h/8500)` duplicated again | One physical-constants module, one value per constant |
| **Mass aggregation** | `Q-MB-9` | The same aggregation twice — rounded to 6 dp in `weight_items_service`, unrounded in `mass_cg_service` — agreeing today with nothing testing that they still do; plus two "empty" conventions (`0` vs `null`) | Disappears with the `weight_items` retirement; the surviving empty convention is `null` |
| **Main-wing rule** | `Q-CT-3` | `aeroplane_schema_to_asb_airplane` picks the largest planform (fixed under gh-788); `AirplaneConfiguration._main_wing_index = 0` still carries the "first wing" assumption that made every coefficient ≈8× wrong | The second entry point is deleted rather than fixed twice |
| **Total mass** | `Q-MB-7` | `GET /total_mass_kg` (gating the `AirplaneConfiguration` export) versus the `mass` design assumption (driving every sizing surface) | **Open** — no verdict yet |

## Decision

**For any quantity a user can see, exactly one code path produces it. Every other
path that exposes it is a read-only view.**

Corollaries, each earned by an instance above:

1. **When two producers already exist, one is designated and the other is deleted or
   made derived.** Keeping both and warning on divergence is explicitly rejected in
   `Q-MB-1`: it *"leaves the number order-dependent"*. A warning tells the user the
   system does not know the answer; it does not supply one. This is where ADR 0020
   stops and this ADR starts.
2. **Rewriting the second producer to agree is not a fix.** `Q-AA-1` rejects it: two
   producers *"must then agree on `e` and `AR` or diverge again, only more
   quietly"*.
3. **Ownership follows generation.** The layer that *creates* a name owns resolving
   it — hence `control_surface_mixing` exports the resolver.
4. **A required call site beats a fixed call site.** Patching the three consumers
   resolves #955 today; the next consumer keying on the raw DB name reintroduces it.
   A mandatory resolver makes the divergence **structurally impossible**.
5. **The mission preset is the single author of mission-shaped defaults**
   (`Q-MS-14`). `PARAMETER_DEFAULTS` carries only values with no mission dependence
   (ρ, g); cruise speed, g-limit, CL_max, power-to-weight and static margin belong
   to the preset alone.

**The standard test** is the producer/consumer contract test adopted in `Q-CC-10`:
an assertion that every key the consumers read is a key the producer actually
writes. It would have caught `Q-AA-1`, `Q-PT-8` and `Q-MS-8` before they shipped.

## Consequences

- Order-dependence disappears by construction — `Q-MB-1`'s defect is not mitigated,
  it ceases to be expressible. Each resolution **removes** code rather than adding
  arbitration, and double-counting solves itself once the tree is the only mass
  writer.
- **Several resolutions require data migrations**: `weight_items` rows become tree
  nodes with a ×1000 m→mm conversion (the
  [ADR 0001](0001-millimetres-in-cad-metres-in-db-and-aerosandbox.md) boundary); the
  seven `power_to_weight` presets need re-authored values; `created_by` needs a
  backfill of legacy `NULL`s to `'human'`.
- **Designating a winner discards a capability**, at least on paper — `weight_items`
  was the only place a bare point mass could be entered. The decision rests on the
  maintainer's argument that a point mass is a *"fake component without dimensions"
  (L×B×H = 0,0,0)* that needs a position anyway, so the tree already expresses it.
  Likewise, deleting `_auto_populate_cd0` means an aeroplane never recomputed no
  longer gets `cd0` incidentally seeded — an improvement under ADR 0020, but a
  visible behaviour change.
- **The rule does not tell you which producer wins.** Each instance needed its own
  argument: git provenance for mass, physics for `cd0`, generation-ownership for
  control names, calibration regime for landing distance
  ([ADR 0023](0023-engineering-constants-carry-provenance.md)).
- This **generalises** ADR 0004; it does not supersede it. `Q-MB-7` is recorded here
  as **open**.

**Rejected:** keeping both producers and warning on divergence (leaves the number
order-dependent; ADR 0020's channel covers *degraded* numbers, not *contested* ones);
summing or reconciling with a dedup key (makes double-counting permanent machinery);
fixing the second producer so it agrees (corollary 2); patching current consumers and
moving on (corollary 4 — already done for #955, which is why the bug is still open).

## Related

- [ADR 0004](0004-one-aero-truth-per-aircraft.md) — the aerodynamic special case
  this generalises.
- [ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md) — a warning
  declares a degraded number, it does not arbitrate between two.
- [ADR 0011](0011-cg-is-a-top-down-design-target.md) — the mass/CG philosophy that
  makes the component tree the natural authority.
- [ADR 0019](0019-implementation-details-must-not-leak-into-the-api.md) — same
  argumentative shape: one defect repeatedly rediscovered under different names.
- [`../questions.md`](../questions.md) §Q-MB-1 · Q-AA-1 · Q-WD-1 · Q-CC-4 · Q-CC-9 ·
  Q-CC-10 · Q-CT-3 · Q-PT-8 · Q-PT-9 · Q-PT-13 · Q-MS-1 · Q-MS-2 · Q-MS-14 ·
  Q-MB-7 · Q-MB-8 · Q-MB-9 · Q-VS-3.
