/**
 * Tests for the SSE-stream parser used by the gh-737 progress bar.
 */

import { describe, expect, it } from "vitest";

import { parseSseStream } from "@/lib/sseStream";

function makeResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const c of chunks) controller.enqueue(encoder.encode(c));
      controller.close();
    },
  });
  return { body: stream } as Response;
}

describe("parseSseStream", () => {
  it("parses a single well-formed event", async () => {
    const resp = makeResponse([
      `event: progress\ndata: {"pct": 50}\n\n`,
    ]);
    const events: unknown[] = [];
    for await (const e of parseSseStream(resp)) events.push(e);
    expect(events).toEqual([
      { event: "progress", data: { pct: 50 } },
    ]);
  });

  it("parses multiple events from one chunk", async () => {
    const resp = makeResponse([
      `event: a\ndata: 1\n\n` +
      `event: b\ndata: 2\n\n` +
      `event: c\ndata: 3\n\n`,
    ]);
    const events: unknown[] = [];
    for await (const e of parseSseStream(resp)) events.push(e);
    expect(events.map((e) => (e as { event: string }).event)).toEqual(["a", "b", "c"]);
  });

  it("handles split chunks across the record boundary", async () => {
    // Split the event across two chunks — parser must keep state in
    // its internal buffer.
    const resp = makeResponse([
      `event: progress\ndata: {"p`,
      `ct": 25}\n\n`,
    ]);
    const events: unknown[] = [];
    for await (const e of parseSseStream(resp)) events.push(e);
    expect(events).toEqual([
      { event: "progress", data: { pct: 25 } },
    ]);
  });

  it("falls back to raw string when data is not JSON", async () => {
    const resp = makeResponse([
      `event: note\ndata: hello world\n\n`,
    ]);
    const events: unknown[] = [];
    for await (const e of parseSseStream(resp)) events.push(e);
    expect(events).toEqual([
      { event: "note", data: "hello world" },
    ]);
  });

  it("defaults event name to 'message' when omitted", async () => {
    const resp = makeResponse([
      `data: {"x": 1}\n\n`,
    ]);
    const events: unknown[] = [];
    for await (const e of parseSseStream(resp)) events.push(e);
    expect(events).toEqual([
      { event: "message", data: { x: 1 } },
    ]);
  });

  it("flushes a trailing record after the stream closes", async () => {
    // The server can close the stream without a final blank-line
    // separator. The parser flushes the buffered record on EOF.
    const resp = makeResponse([
      `event: done\ndata: {"ok": true}`,
    ]);
    const events: unknown[] = [];
    for await (const e of parseSseStream(resp)) events.push(e);
    expect(events).toEqual([
      { event: "done", data: { ok: true } },
    ]);
  });

  it("ignores empty records (keep-alive comments not yet emitted)", async () => {
    const resp = makeResponse([
      `event: a\ndata: 1\n\n` +
      `\n\n` +
      `event: b\ndata: 2\n\n`,
    ]);
    const events: unknown[] = [];
    for await (const e of parseSseStream(resp)) events.push(e);
    expect(events).toHaveLength(2);
  });
});
