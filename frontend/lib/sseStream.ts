/**
 * Minimal Server-Sent-Events parser for ``fetch`` ``ReadableStream``
 * responses (gh-737).
 *
 * The browser's built-in ``EventSource`` only works with GET requests
 * — the gh-737 backend stream is POST + multipart, so we can't use it
 * directly. Instead we read ``response.body`` as a stream and parse
 * SSE-format chunks ourselves.
 *
 * SSE wire format (relevant subset):
 *
 *   event: <event-name>
 *   data: <single-line payload>
 *   <blank-line>
 *
 * Events are separated by blank lines (``\n\n``). The parser handles
 * partial chunks — the trailing incomplete block is kept in a buffer
 * until the next read brings the rest of it.
 */

export interface SseEvent<T = unknown> {
  event: string;
  data: T;
}

/** Decode one ``data:`` value: prefer JSON, fall back to raw string. */
function decodePayload(dataStr: string): unknown {
  if (!dataStr) return undefined;
  try {
    return JSON.parse(dataStr);
  } catch {
    return dataStr;
  }
}

/** Parse one SSE record into ``{event, data}`` or null if empty. */
function parseRecord<T>(record: string): SseEvent<T> | null {
  const trimmed = record.trim();
  if (!trimmed) return null;
  let eventType = "message";
  let dataStr = "";
  for (const line of trimmed.split("\n")) {
    if (line.startsWith("event:")) {
      eventType = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      // SSE allows multiple ``data:`` lines per event; the spec joins
      // them with newlines. The backend here uses a single line but
      // we stay tolerant.
      const piece = line.slice("data:".length).trim();
      dataStr = dataStr ? `${dataStr}\n${piece}` : piece;
    }
  }
  const data = decodePayload(dataStr);
  if (data === undefined) return null;
  return { event: eventType, data: data as T };
}

/**
 * Iterate SSE events from a ``Response`` whose body is an active stream.
 *
 * @param response — a ``fetch`` response with ``content-type:
 *   text/event-stream``. The caller is responsible for checking
 *   ``response.ok`` before passing it here.
 *
 * @yields one ``{event, data}`` per SSE block. ``data`` is JSON-parsed
 *   when possible, otherwise the raw string.
 */
export async function* parseSseStream<T = unknown>(
  response: Response,
): AsyncGenerator<SseEvent<T>, void, void> {
  if (!response.body) {
    throw new Error("Response has no readable body — cannot stream SSE.");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Split on the SSE record separator. The last fragment is kept
      // in the buffer because it may be an incomplete record.
      const records = buffer.split("\n\n");
      buffer = records.pop() ?? "";
      for (const record of records) {
        const parsed = parseRecord<T>(record);
        if (parsed) yield parsed;
      }
    }
    // Flush any trailing record after stream end (some backends close
    // the stream without a final blank-line separator).
    const trailing = parseRecord<T>(buffer);
    if (trailing) yield trailing;
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // Reader may already be closed by the stream completing.
    }
  }
}
