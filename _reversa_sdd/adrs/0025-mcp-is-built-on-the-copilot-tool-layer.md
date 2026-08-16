# ADR 0025 — MCP is built on the copilot tool layer, not by wrapping REST

- **Status:** Accepted — direction for the next MCP iteration
- **Decided:** 2026-08-15, during the specification validation interview
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (both layers read; the defect it explains is measured)

## Context

Two independent tool surfaces exist for the same system.

**`copilot_tools`** — purpose-built for an LLM consumer. `copilot_service` dispatches
`copilot_tools.execute(tool_name, db, aeroplane_id, **args)`; numbers are computed
server-side and deterministically, granularity is domain-shaped, and the module
contains **no MCP reference at all**. The in-app copilot does **not** use MCP.

**`app/mcp_server.py`** — 76 tools produced by mechanically wrapping REST endpoints
through `_call_endpoint`. Its surface is therefore *"whatever endpoints exist"* rather
than *"what an agent needs"*.

The wrapping is not merely inelegant; it is the direct cause of the module's headline
defect. `_call_endpoint` must open its own session because a REST endpoint expects one
— and that is where the commit was lost, so ~40 write tools returned a convincing
payload and persisted nothing (`Q-MC-1`). The `request=None` plumbing has the same
origin. Neither problem exists in `copilot_tools`, whose signature already carries the
session.

## Decision

**When the MCP surface is next worked on, it is built on `copilot_tools` — not carried
forward as a REST→MCP conversion.**

- **One tool implementation, two transports:** the in-app copilot and external MCP
  agents call the same layer. ADR 0022 applied to the tool layer.
- The MCP surface is designed as an **agent capability set**, not derived from the
  route table.
- Standalone MCP mode (an external agent connecting without the app) is the *purpose*
  of MCP and is retained as scaffolding — currently unused, marked as not part of the
  supported surface (`Q-MC-7`).

**Not deferred:** the `Q-MC-1` transaction fix still lands on the current wrapper.
~40 tools that report success and write nothing cannot stand pending a rebuild. With
`MCP_ALLOW_WRITES` defaulting to off, writes are inert by default; if the rebuild
lands first, the wrapper is replaced rather than repaired.

## Consequences

- The existing REST→MCP conversion becomes dead code **once the rebuild lands** — not
  before. It is today the only MCP surface that exists, so `P-DEAD-0` does not yet
  apply to it.
- The tool contract stops tracking the REST contract. This is deliberate: the two have
  different consumers, and coupling them is what produced a 76-tool surface nobody
  designed.
- Tool schema drift stops being a concern in the way `Q-CC-12` framed it, since MCP
  clients read `tools/list` at connect time and the tools become first-class rather
  than derived.

## Related

- [ADR 0022](0022-one-authority-per-user-facing-quantity.md) — one implementation per
  capability; this is that rule applied to tools.
- [ADR 0007](0007-copilot-proposes-human-adopts.md) — the copilot's write semantics,
  which an MCP transport would inherit rather than reinvent.
- [ADR 0019](0019-implementation-details-must-not-leak-into-the-api.md) — the MCP
  surface is a contract too; the mm-vs-SI split in `get_wing_geometry` is an instance
  (`Q-CO-11`).
- [`../questions.md`](../questions.md) §Q-MC-7 (the direction), §Q-MC-1 (the defect it
  explains), §Q-CO-11 (tool-schema units).
