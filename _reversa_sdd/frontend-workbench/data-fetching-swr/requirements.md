# frontend-workbench / data-fetching-swr

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Endpoint list and key conventions: [`../contracts.md`](../contracts.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

All server state lives in the SWR cache, reached through **48 hooks** that
follow one convention: the SWR key *is* the request path, `null` disables the
hook, and the hook returns domain-named fields rather than raw `data`. 🟢

Writes go through `putJson` / `lib/api.ts` and then revalidate — either the
hook's own `mutate()` or `useSWRConfig().mutate(key)` for cross-hook
invalidation. 🟢

Two structural gaps sit underneath: **two HTTP clients with two error shapes**,
and no global `SWRConfig` — 🟢 both added (`Q-FW-3`).

## Responsibilities

- Provide the three fetch wrappers (`fetcher`/`putJson`, `api`,
  `parseSseStream`). 🟢
- Provide 48 hooks, one per backend capability. 🟢
- Define the key, disabled-state and return-shape conventions. 🟢
- Invalidate after writes, including across hooks. 🟢
- Normalise the backend's two error envelopes for display. 🟢

## Business Rules

- **BR-FE5 — One base URL, inlined at build time.** 🟢
  `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"`.
- **BR-FE6 — The key is the literal path; `null` disables.** 🟢
  ```ts
  const path = id !== null ? `/lineages/${id}/tree` : null;
  const { data, error, isLoading, mutate } = useSWR<TreeOut>(path, fetcher);
  return { tree: data, isLoading, error, mutate };
  ```
- **BR-FE29 — Query parameters are part of the key.** 🟢 A different filter is a
  different cache entry (`/construction-plans?plan_type={}`,
  `/airfoils/db/suitability?{}`, `/aeroplanes/{}/matching-chart?{}`).
- **BR-FE30 — Hooks never expose `data`.** 🟢 They return domain-named fields
  (`tree`, `wings`, `plans`, `history`), so a rename in the hook does not ripple
  through components.
- **BR-FE7 — Write, then revalidate.** 🟢 `putJson` / `api.*` followed by
  `mutate()`; cross-hook invalidation uses `useSWRConfig().mutate(key)` with the
  **exact same literal path** — there is no shared key module, so the string must
  be reproduced. 🟡
- **BR-FE8 — 🟡 The hooks migrate onto one typed client (`Q-FW-2`), which removes the second error shape. Previously:
  | | `lib/fetcher.ts` | `lib/api.ts` |
  |---|---|---|
  | Used by | **all SWR hooks** | non-SWR call sites |
  | Error | plain `Error("<status> <statusText>: <body>")` | typed `ApiError(status, message, details)` |
  | `Content-Type` | only on `putJson` | always |
  | `204` | would throw on `res.json()` | returns `undefined` |
  `lib/parseApiError.ts` bridges them.
- **BR-FE10 — 🟢 A global `SWRConfig` plus a shared key module (`Q-FW-3`, maintainer-answered). Previously none: No shared `refreshInterval`,
  `revalidateOnFocus`, retry policy or `onError`; each hook decides for itself.
- **BR-FE11 — 🟡 TypeScript client generation is scheduled (`Q-CC-11`), after the ADR 0019 cleanups. Previously hand-mirrored: Only `types/versioning.ts`
  and `types/versionGraph.ts` are shared; everything else is redeclared inside
  its hook. Nothing is generated from `/openapi.json`, so a backend schema change
  surfaces only through `tsc` against hand-written fixtures — which is exactly
  why `npx tsc --noEmit` is a **separate** CI gate.
- **BR-FE9 — SSE is hand-parsed over POST.** 🟢 `parseSseStream` buffers partial
  records, joins multiple `data:` lines with `\n`, falls back to the raw string
  for non-JSON payloads, and flushes a trailing record after stream end.
- **BR-FE31 — The client must tolerate both backend error envelopes.** 🟢
  `{"error": {code, message, details}}` from the global handlers and
  `{"detail": …}` from the versioning and copilot-history routers.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Resolve the base URL from `NEXT_PUBLIC_API_URL` | Must | Default `http://localhost:8001` |
| RF-02 | `fetcher(path)` performs a GET and throws on non-2xx | Must | Message contains status, statusText and body |
| RF-03 | `putJson(path, body)` sends JSON with `Content-Type` | Must | Parses the JSON response |
| RF-04 | `fetchAPI` throws `ApiError` and returns `undefined` on 204 | Must | Both behaviours |
| RF-05 | Use a `null` key to disable a hook | Must | No request when nothing is selected |
| RF-06 | Use the literal request path as the SWR key | Must | Including query parameters |
| RF-07 | Return renamed fields plus `isLoading`, `error`, `mutate` | Must | Never raw `data` |
| RF-08 | Revalidate after a write | Must | UI updates without a reload |
| RF-09 | Invalidate related keys across hooks | Must | A version action revalidates the tree **and** the aeroplanes list |
| RF-10 | Parse SSE from a POST response | Must | Copilot + OpenVSP import |
| RF-11 | Buffer partial SSE records | Must | A split record yields one event |
| RF-12 | Tolerate a non-JSON SSE payload | Must | Raw string returned |
| RF-13 | Flush a trailing SSE record after stream end | Must | Last event not lost |
| RF-14 | Release the SSE reader lock | Must | In `finally`, tolerating an already-closed reader |
| RF-15 | Normalise both backend error envelopes | Must | `parseApiError` handles both |
| RF-16 | Provide a global revalidation/retry/error policy | Should | 🟡 **not met** |
| RF-17 | Derive response types from the backend schema | Should | 🟡 **not met** — hand-mirrored |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Efficiency | No request may fire before an aircraft is selected | the `null`-key idiom in every hook | 🟢 |
| Consistency | 48 hooks share one shape, so a component can consume any of them the same way | the hook convention | 🟢 |
| Freshness | A write is followed by a revalidation of every affected key | `mutate` / `useSWRConfig().mutate` | 🟢 |
| Resilience | 🟡 No shared retry or error policy; a failing hook degrades only its own panel | no `SWRConfig` | 🟡 |
| Type safety | 🟡 Backend drift is caught only by `tsc` against hand-written mirrors | `useCopilot.ts` comment | 🟡 |
| Robustness | 🟡 `fetcher` would throw on a 204 | `lib/fetcher.ts` | 🟡 |
| Maintainability | 🟡 Cross-hook invalidation duplicates key strings | no key module | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Hook conventions

  Scenario: A disabled hook is silent
    Given no aircraft is selected
    Then the hook's key is null and no request is made

  Scenario: Renamed return fields
    Given any of the 48 hooks
    Then it returns domain-named fields plus isLoading, error and mutate
    And it never returns a field called data

  Scenario: Query parameters are part of the key
    Given two calls with different plan_type values
    Then two distinct cache entries exist

Feature: Writes

  Scenario: Revalidate after a write
    When I save a wing config
    Then the wing hook's mutate() is called
    And the panel shows the saved values without a reload

  Scenario: Cross-hook invalidation
    When I adopt a branch
    Then the lineage tree key and the aeroplanes list key are both revalidated

Feature: Errors

  Scenario: The SWR client's error shape
    Given the backend returns 404 with {"detail": "Aeroplane not found"}
    When fetcher runs
    Then it throws Error("404 Not Found: {\"detail\":\"Aeroplane not found\"}")

  Scenario: The typed client's error shape
    Given the same response through fetchAPI
    Then it throws ApiError with status 404 and the body in details

  Scenario: Both envelopes are displayable
    Given one error body {"error": {"code": "not_found", "message": "Wing not found"}}
    And another {"detail": "Branch not found"}
    Then parseApiError produces a human-readable message for both

  Scenario: 204 handling
    Given a DELETE returning 204
    When called through api.delete
    Then the result is undefined
    When called through fetcher
    Then it throws

Feature: SSE

  Scenario: POST stream
    When I POST to /aeroplanes/{id}/copilot/stream
    Then parseSseStream yields token, tool_call, tool_result and done events

  Scenario: Split record
    Given one record arrives across two chunks
    Then exactly one event is yielded

  Scenario: Multiple data lines
    Given an event with two data: lines
    Then they are joined with a newline before parsing

  Scenario: Non-JSON payload
    Given a data line that is not JSON
    Then the raw string is yielded and nothing throws

  Scenario: Trailing record
    Given the stream closes without a final blank line
    Then the last record is still yielded

  Scenario: Reader release
    When iteration ends or throws
    Then releaseLock is attempted and an already-closed reader is tolerated
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| The three wrappers (RF-01…RF-04) | Must | Every request goes through one of them |
| The `null`-key idiom (RF-05) | Must | Otherwise every page fires requests with no aircraft |
| Literal-path keys (RF-06) | Must | Cross-hook invalidation depends on exact strings |
| Renamed returns (RF-07) | Must | The shared consumption contract across 48 hooks |
| Write + revalidate incl. cross-hook (RF-08/RF-09) | Must | Stale UI otherwise |
| SSE parsing (RF-10…RF-14) | Must | `EventSource` cannot POST |
| Error normalisation (RF-15) | Must | The backend emits two envelopes |
| A global `SWRConfig` policy (RF-16) | Should | 🟡 none exists |
| Generated types from `/openapi.json` (RF-17) | Should | 🟡 hand-mirrored today |
| A shared key module | Could | 🟡 keys are duplicated at invalidation sites |
| One HTTP client | Could | 🟡 two exist, bridged by `parseApiError` |
| Optimistic updates | Won't | Not used anywhere |
| Offline / persistent SWR cache | Won't | Not implemented |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `frontend/lib/fetcher.ts` | `API_BASE`, `fetcher`, `putJson` | 🟢 |
| `frontend/lib/api.ts` | `ApiError`, `fetchAPI`, `api` | 🟢 🟡 |
| `frontend/lib/sseStream.ts` | `SseEvent`, `parseSseStream`, `parseRecord`, `decodePayload` | 🟢 |
| `frontend/lib/parseApiError.ts` | the envelope bridge | 🟡 |
| `frontend/hooks/` (48 files, ~30 using `useSWR` directly) | the hook convention | 🟢 |
| `frontend/hooks/useVersioning.ts` | `useLineageTree`, `useVersionActions` — the cross-hook invalidation example | 🟢 |
| `frontend/hooks/useCopilot.ts` | SWR history + SSE send | 🟢 |
| `frontend/types/versioning.ts`, `types/versionGraph.ts` | the only shared types | 🟢 🟡 |
