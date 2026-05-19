/**
 * Parse a non-ok `fetch` response into a user-readable error message.
 *
 * The backend returns a structured JSON envelope for `ServiceException`
 * subclasses — `{ "error": { "code": "...", "message": "...", "details": ... } }`
 * (see `app/main.py` error handler). Raw `await res.text()` dumps the
 * whole envelope into the UI; this helper extracts the human message and
 * tags the HTTP status class so the caller can render an actionable
 * sentence.
 *
 * gh-577 review item.
 */

function pickString(...candidates: unknown[]): string | undefined {
  for (const c of candidates) {
    if (typeof c === "string" && c.length > 0) return c;
  }
  return undefined;
}

function extractMessageFromJson(payload: unknown): string | undefined {
  if (typeof payload !== "object" || payload === null) return undefined;
  const obj = payload as Record<string, unknown>;
  // Custom envelope: { error: { message | detail, ... } }
  if (typeof obj.error === "object" && obj.error !== null) {
    const err = obj.error as Record<string, unknown>;
    const fromError = pickString(err.message, err.detail);
    if (fromError) return fromError;
  }
  // FastAPI default HTTPException: { detail: "..." }
  return pickString(obj.detail);
}

async function bodyToMessage(res: Response): Promise<string | undefined> {
  // Try JSON first; if the body isn't JSON, fall back to plain text.
  try {
    const payload: unknown = await res.clone().json();
    const fromJson = extractMessageFromJson(payload);
    if (fromJson) return fromJson;
  } catch {
    // not JSON — fall through to text
  }
  try {
    const text = await res.text();
    return text || undefined;
  } catch {
    return undefined;
  }
}

function formatByStatus(
  status: number,
  prefix: string,
  detail: string,
): string {
  if (status === 404) return `${prefix} — not found: ${detail}`;
  if (status === 422) return `${prefix} — invalid request: ${detail}`;
  return `${prefix} failed (${status}): ${detail}`;
}

export async function parseApiError(
  res: Response,
  fallbackPrefix: string,
): Promise<string> {
  const fromBody = await bodyToMessage(res);
  const detail = fromBody ?? res.statusText ?? `status ${res.status}`;
  return formatByStatus(res.status, fallbackPrefix, detail);
}
