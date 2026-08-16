# frontend-workbench / data-fetching-swr — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).
> Endpoint inventory: [`../contracts.md`](../contracts.md).

## Interface

```ts
// lib/fetcher.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";
export async function fetcher<T>(path: string): Promise<T>
export async function putJson<T>(path: string, body: unknown): Promise<T>
export { API_BASE };

// lib/api.ts
export class ApiError extends Error {
  constructor(public status: number, message: string, public details?: unknown)
}
export async function fetchAPI<T>(path: string, init?: RequestInit): Promise<T>
export const api = { get, post, put, delete };

// lib/sseStream.ts
export interface SseEvent<T = unknown> { event: string; data: T }
export async function* parseSseStream<T>(response: Response): AsyncGenerator<SseEvent<T>, void, void>
```

## Main Flow

### F1 — `fetcher` and `putJson` 🟢

```ts
export async function fetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);   // plain Error 🔴
  }
  return res.json();                                               // would throw on 204 🟡
}

export async function putJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`PUT ${path} failed: ${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}
```

Note `fetcher` is **GET-only** and sets no headers; the raw body text is
embedded in the error message, which is how both backend envelopes end up in the
same string and why `parseApiError` has to re-parse it. 🔴

### F2 — `lib/api.ts` — the richer, less-used client 🟢

```ts
export async function fetchAPI<T>(path, init?) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, `${res.status} ${res.statusText}: ${path}`, body);
  }
  if (res.status === 204) return undefined as T;      // the case fetcher lacks
  return res.json();
}
```

🟡 The spread order means `init` can override the `Content-Type` header **and**
`headers` itself — `{ headers, ...init }` places `init.headers` after the merge,
so a caller passing `headers` replaces rather than extends. Reproduce as-is.

### F3 — The hook convention 🟢

```ts
export function useWings(aeroplaneId: string | null) {
  const path = aeroplaneId ? `/aeroplanes/${aeroplaneId}/wings` : null;  // null = disabled
  const { data, error, isLoading, mutate } = useSWR<WingSummary[]>(path, fetcher);
  return { wings: data, isLoading, error, mutate };                      // renamed
}
```

Roughly 30 of the 48 hooks use `useSWR` directly; the rest wrap actions
(`useVersionActions`, `useCopilot`, `useCopilotProposal`, …) and expose
`busy` / `error` plus imperative functions. 🟢

### F4 — Writes and invalidation 🟢

```ts
const { mutate: mutateGlobal } = useSWRConfig();

async function adopt(branchId: number) {
  await api.post(`/branches/${branchId}/adopt`);
  await mutate();                                       // this hook's own key
  await mutateGlobal(`/lineages/${rootId}/tree`);       // the exact literal path
  await mutateGlobal(`/aeroplanes`);                    // the picker list
}
```

Because keys are raw paths and no key module exists, every invalidation site
**duplicates the producing hook's string**. A typo produces a silent no-op. 🟡

### F5 — SSE 🟢

```ts
export async function* parseSseStream<T>(response: Response) {
  if (!response.body) throw new Error("Response has no readable body — cannot stream SSE.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const records = buffer.split("\n\n");
      buffer = records.pop() ?? "";           // keep the possibly-incomplete tail
      for (const record of records) {
        const parsed = parseRecord<T>(record);
        if (parsed) yield parsed;
      }
    }
    const trailing = parseRecord<T>(buffer);  // some backends omit the final blank line
    if (trailing) yield trailing;
  } finally {
    try { reader.releaseLock(); } catch { /* already closed */ }
  }
}

function parseRecord<T>(record) {
  // event: <name>   -> eventType (default "message")
  // data: <payload> -> multiple lines joined with "\n"
  // JSON.parse with a raw-string fallback; an empty payload yields null
}
```

The header comment states the constraint: *"The browser's built-in
`EventSource` only works with GET requests — the gh-737 backend stream is POST +
multipart, so we can't use it directly."* 🟢

Consumers:

| Consumer | Events |
|---|---|
| `useCopilot` | `token`, `tool_call`, `tool_result`, `done`, `error` |
| `ImportOpenVspButton` / `ImportProgressBar` (gh-737) | progress + warnings |

## Alternative Flows

- **Nothing selected:** key `null`; SWR does not fetch; `isLoading` is false and
  `data` is `undefined`. 🟢
- **Backend down:** `fetcher` throws; each panel renders its own error; there is
  no global handler and no retry policy beyond SWR's defaults. 🔴
- **A 204 through `fetcher`:** `res.json()` throws on an empty body. 🟡 (Only
  `lib/api.ts` handles it.)
- **A 4xx with the `{"error": {…}}` envelope:** the whole JSON string is embedded
  in the `Error` message and re-parsed by `parseApiError`. 🔴
- **A 4xx with `{"detail": …}`** (versioning, copilot history): the same path,
  different shape. 🔴
- **An SSE record split across chunks:** buffered until complete. 🟢
- **A stream closing without a final blank line:** the trailing record is
  flushed. 🟢
- **A non-JSON `data:` payload:** the raw string is yielded. 🟢
- **An invalidation key typo:** 🟢 becomes a compile-time error with the shared key module (`Q-FW-3`).
- **A backend field rename:** no runtime error until the field is read;
  `tsc` catches it only if a hand-written mirror or fixture disagrees. 🔴

## Dependencies

- `swr` — `useSWR`, `useSWRConfig`.
- `fetch` / `ReadableStream` / `TextDecoder` (browser APIs; jsdom under vitest).
- `lib/parseApiError.ts` for display normalisation.
- The FastAPI v2 surface — see [`../contracts.md`](../contracts.md).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| SWR as the only server-state layer; no Redux/Zustand/Jotai | 48 hooks | 🟢 |
| The SWR key **is** the request path | every hook | 🟢 |
| `null` key as the universal disabled state | every hook | 🟢 |
| Hooks rename `data` so components never couple to SWR | every hook | 🟢 |
| Cross-hook invalidation via `useSWRConfig().mutate(literal path)` | `useVersionActions` | 🟢 (a 🟡 duplication) |
| Two clients, kept because the SWR fetcher predates the typed one | `fetcher.ts` vs `api.ts` | 🟡 |
| Hand-rolled SSE because `EventSource` is GET-only | `sseStream.ts` header | 🟢 |
| Tolerate a missing final blank line and non-JSON payloads | `parseSseStream` | 🟢 |
| No global `SWRConfig` | — | 🟡 no rationale found |
| Hand-mirror response types instead of generating a client | `useCopilot.ts` comment | 🟢 (a 🟡 risk) |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| all server state | the SWR cache, keyed by path | per tab; revalidated on write, focus and reconnect (SWR defaults) |
| in-flight streaming text / current tool | `useCopilot` local state | until `done`, then replaced by revalidated history |
| `busy` flags | action hooks | per action |

## Observability

- 🟡 Errors surface per panel through each hook's `error` field.
- 🔴 No global `onError`, no error boundary, no client-side error reporting.
- 🔴 No request logging or timing on the client — a slow endpoint is
  indistinguishable from a slow render.

## Risks and Gaps

- 🟡 **The hooks migrate onto one typed client** (`Q-FW-2`, derived), which removes the second error shape and with it `lib/parseApiError.ts`. Previously two clients with two error shapes, bridged by
  `lib/parseApiError.ts` — itself only necessary because the **backend** emits
  two envelopes.
- 🔴 **No global `SWRConfig`**: no shared revalidation, retry or error policy
  across 48 hooks.
- 🔴 **Response types are hand-mirrored**; nothing is generated from
  `/openapi.json`, so backend drift is caught only by `tsc` against
  hand-written fixtures — the exact failure the CI note warns about.
- 🔴 **An invalidation key typo silently no-ops**, leaving stale data on screen.
- 🟢 **Deliberately not built** (`Q-FW-7`): telemetry for an audience of one is instrumentation without a consumer (ADR 0024). Previously.**
- 🟡 **`fetcher` cannot handle a 204** — only `lib/api.ts` can.
- 🟡 **`fetchAPI`'s spread order** lets `init` replace the `Content-Type` header
  it just set.
- 🟡 **Cross-hook invalidation duplicates key strings**; a shared key module
  would remove the class of bug.
