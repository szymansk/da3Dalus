# mcp-server / tool-registration

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

How 76 tools become an MCP server: a decorator that **records without wrapping**,
a module-level spec list, a frozen name tuple, and one installation function that
mounts everything onto a `FastMCP` instance at import time. 🟢

The pattern's value is that a tool remains an ordinary coroutine — testable,
importable and callable without any MCP machinery. 🟢

## Responsibilities

- Record `(name, description, handler)` triples as tools are declared. 🟢
- Freeze the name list as the introspection surface. 🟢
- Install every spec plus the two resource templates onto a `FastMCP` server. 🟢
- Memoise that server and expose it as an ASGI app for mounting. 🟢

## Business Rules

- **BR-MCP1 — Declaration ≠ installation.** 🟢 `@mcp_tool` only appends an
  `MCPToolSpec` to `TOOL_SPECS` and returns the function **unchanged**;
  `create_mcp_server()` performs the registration.
- **BR-MCP2 — The handler signature is the input schema.** 🟢 FastMCP derives
  the JSON schema from the coroutine parameters, so the Pydantic types are the
  contract and there is no hand-written schema anywhere in the module.
- **BR-MCP3 — `description=` is the only agent-visible prose.** 🟢 No tool
  function has a docstring.
- **BR-MCP4 — `MCP_TOOL_NAMES` is frozen at import.** 🟢
  `tuple(spec.name for spec in TOOL_SPECS)`, 76 entries.
- **BR-MCP5 — The server is a memoised import-time singleton.** 🟢
  `get_mcp()` caches into the module global; `mcp = get_mcp()` (l.1548) runs
  before `create_app()`.
- **BR-MCP18 — Endpoint imports live inside the tool bodies.** 🟢 This keeps
  `app.mcp_server` importable on a platform where a capability-gated router
  (CadQuery / AeroSandbox) does not exist; the failure surfaces at **call** time
  instead. 🟡
- **BR-MCP19 — Two resource templates are registered alongside the tools.** 🟢
  `img://{asset_id}` (`image/png`) and `data://{asset_id}`
  (`application/octet-stream`).

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | `@mcp_tool(name, description)` appends a spec and returns `fn` unchanged | Must | The decorated object is the original function |
| RF-02 | `TOOL_SPECS` accumulates in declaration order | Must | Order is stable across imports |
| RF-03 | `MCP_TOOL_NAMES` is a frozen tuple of 76 unique names | Must | No duplicates |
| RF-04 | `create_mcp_server()` builds `FastMCP(name="da3dalus-cad-tools")` | Must | Server name asserted |
| RF-05 | Every spec is registered with its name and description | Must | `tools/list` returns 76 |
| RF-06 | Both resource templates are registered with their MIME types | Must | `img://` → `image/png`, `data://` → `application/octet-stream` |
| RF-07 | `get_mcp()` memoises the server | Must | Two calls return the same object |
| RF-08 | `create_mcp_http_app(path)` returns a mountable ASGI app | Must | `app.mount("/mcp", …)` works |
| RF-09 | The server is constructed at import time | Must | `mcp` is not `None` after importing the module |
| RF-10 | Endpoint imports are local to each tool body | Should | The module imports on a platform without CadQuery |
| RF-11 | A standalone runner exists | Could | 🟢 scaffolding (`Q-MC-7`); `run_mcp_server()` (hard-coded bind) |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Testability | A tool must be callable without FastMCP | the decorator returns `fn` unchanged | 🟢 |
| Portability | The module must import even when heavy routers are absent | imports inside tool bodies | 🟢 |
| Discoverability | The tool set must be introspectable from Python | `MCP_TOOL_NAMES` | 🟢 |
| Maintainability | Adding a tool must be one decorator, not a registration edit | `TOOL_SPECS` append | 🟢 |
| Startup cost | Building 76 tool schemas happens once, at import | `mcp = get_mcp()` | 🟡 |
| Configurability | 🟡 The tool set is fixed before any configuration is read | import-time construction | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Recording

  Scenario: The decorator does not wrap
    Given a coroutine decorated with @mcp_tool("x", "does x")
    Then TOOL_SPECS gains one entry named "x" with that description
    And the decorated symbol is the original coroutine
    And calling it directly works without any MCP server

  Scenario: Names are frozen and unique
    Then MCP_TOOL_NAMES is a tuple of 76 names
    And len(set(MCP_TOOL_NAMES)) equals 76

Feature: Installation

  Scenario: Every spec is installed
    When create_mcp_server() runs
    Then the server is named "da3dalus-cad-tools"
    And every name in MCP_TOOL_NAMES is registered as a tool

  Scenario: Resource templates
    Then img://{asset_id} is registered with mime type image/png
    And data://{asset_id} is registered with mime type application/octet-stream

  Scenario: Memoisation
    When get_mcp() is called twice
    Then the same server object is returned

  Scenario: Import-time construction
    When app.mcp_server is imported
    Then the module global mcp is a FastMCP instance
    And this happens before create_app() runs

Feature: Schema derivation

  Scenario: The signature is the contract
    Given a tool whose parameter is annotated OperatingPointSchema
    Then the MCP input schema for that tool describes OperatingPointSchema
    And no hand-written JSON schema exists for it

Feature: Platform tolerance

  Scenario: Importing without CadQuery
    Given a platform where the cad router cannot be imported
    When app.mcp_server is imported
    Then the import succeeds
    And calling create_wing_loft_export fails at call time, not at import time
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| Non-wrapping decorator (RF-01) | Must | The entire test strategy depends on it |
| Frozen unique name tuple (RF-03) | Must | The tests' assertion surface |
| Full installation incl. resources (RF-04…RF-06) | Must | Otherwise binary tools have nowhere to point |
| Memoised singleton + mountable app (RF-07/RF-08) | Must | One process, one server |
| Signature-derived schemas (BR-MCP2) | Must | No duplicated schema maintenance |
| Local endpoint imports (RF-10) | Should | ADR 0017 tolerance |
| Import-time construction (RF-09) | Should | Reproduces the legacy; a lazy build would be an improvement |
| Standalone runner (RF-11) | Could | Convenience |
| Per-tool docstrings | Won't | The `description=` string is the documented mechanism |
| Dynamic / runtime tool registration | Won't | 🟡 the set is frozen at import; MCP clients read `tools/list` at connect time (ADR 0025) |
| Per-tool authorisation metadata | Won't | 🟢 no authorisation concept exists, by design (ADR 0024: single-user desktop) |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `app/mcp_server.py:64` | `MCPToolSpec` | 🟢 |
| `…:86` | `mcp_tool` | 🟢 |
| `…` | `TOOL_SPECS` (76 appends) | 🟢 |
| `…:1500` | `MCP_TOOL_NAMES` | 🟢 |
| `…:1503` | `create_mcp_server` | 🟢 |
| `…:1510-1522` | the two `mcp.resource(...)` registrations | 🟢 |
| `…:1530` | `get_mcp` | 🟢 |
| `…:1537` | `create_mcp_http_app` | 🟢 |
| `…:1542` | `run_mcp_server` | 🟢 🟡 |
| `…:1548` | `mcp = get_mcp()` | 🟢 |
| `app/tests/test_mcp_server_tools.py` · `_extended.py` · `_resources.py` | assert against `MCP_TOOL_NAMES` | 🟢 |
