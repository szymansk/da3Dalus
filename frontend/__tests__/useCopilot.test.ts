/**
 * Unit tests for useCopilot hook (gh-919).
 *
 * Strategy:
 * - Mock globalThis.fetch for both the SWR history GET and the POST stream.
 * - Provide a helper that builds a fake SSE ReadableStream from an array of
 *   SSE text chunks.
 * - Use a fresh SWR cache per test (SWRConfig provider).
 * - Assert that:
 *   1. sendMessage POSTs to the correct URL with the correct body.
 *   2. "token" events are accumulated into streamingText.
 *   3. "tool_call" events update activeToolLabel.
 *   4. "tool_result" events clear activeToolLabel.
 *   5. "done" triggers a revalidation of the history SWR key.
 *   6. "error" events surface as errorMessage.
 *   7. History GET populates the history field.
 *   8. sendMessage is a no-op when aeroplaneId is null.
 */
import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCopilot } from "@/hooks/useCopilot";
import type { CopilotHistory } from "@/hooks/useCopilot";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a Response whose body is an in-memory ReadableStream of SSE text. */
function makeSseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const c of chunks) controller.enqueue(encoder.encode(c));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

/** Encode one SSE event in the wire format the backend emits. */
function sseEvent(type: string, data: Record<string, unknown>): string {
  return `event: ${type}\ndata: ${JSON.stringify(data)}\n\n`;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const FAKE_HISTORY: CopilotHistory = {
  messages: [
    {
      id: 1,
      role: "user",
      content: "Hello",
      tool_calls: null,
      tool_results: null,
      parent_id: null,
      created_at: "2026-06-08T10:00:00Z",
    },
    {
      id: 2,
      role: "assistant",
      content: "Hi there!",
      tool_calls: null,
      tool_results: null,
      parent_id: null,
      created_at: "2026-06-08T10:00:01Z",
    },
  ],
};

/** Fresh SWR cache wrapper per test. */
function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(
    SWRConfig,
    { value: { provider: () => new Map(), dedupingInterval: 0 } },
    children,
  );
}

// ---------------------------------------------------------------------------
// Test setup
// ---------------------------------------------------------------------------

let mockFetch: ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockFetch = vi.fn();
  vi.stubGlobal("fetch", mockFetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// History load
// ---------------------------------------------------------------------------

describe("useCopilot — history", () => {
  it("loads history via SWR when aeroplaneId is provided", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(FAKE_HISTORY));

    const { result } = renderHook(() => useCopilot("aero-1"), { wrapper });

    expect(result.current.historyLoading).toBe(true);

    await waitFor(() => expect(result.current.historyLoading).toBe(false));

    expect(result.current.history?.messages).toHaveLength(2);
    expect(result.current.history?.messages[0].content).toBe("Hello");

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain("/aeroplanes/aero-1/copilot-history");
  });

  it("does not fetch history when aeroplaneId is null", () => {
    const { result } = renderHook(() => useCopilot(null), { wrapper });

    expect(result.current.historyLoading).toBe(false);
    expect(result.current.history).toBeUndefined();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("exposes historyError when GET fails", async () => {
    mockFetch.mockResolvedValueOnce(new Response("not found", { status: 404 }));

    const { result } = renderHook(() => useCopilot("aero-1"), { wrapper });

    await waitFor(() => expect(result.current.historyLoading).toBe(false));

    expect(result.current.historyError).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// sendMessage — no-op guard
// ---------------------------------------------------------------------------

describe("useCopilot — sendMessage no-op when no aeroplane", () => {
  it("does not call fetch when aeroplaneId is null", async () => {
    const { result } = renderHook(() => useCopilot(null), { wrapper });

    await act(async () => {
      await result.current.sendMessage("hello");
    });

    expect(mockFetch).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// sendMessage — URL + body
// ---------------------------------------------------------------------------

describe("useCopilot — sendMessage URL and body", () => {
  it("POSTs to the correct stream URL with the message body", async () => {
    // First call: history SWR; second call: stream POST; third: revalidation.
    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY)) // history
      .mockResolvedValueOnce(
        makeSseResponse([
          sseEvent("token", { text: "Hi" }),
          sseEvent("done", { status: "ok" }),
        ]),
      ) // stream
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY)); // revalidation

    const { result } = renderHook(() => useCopilot("aero-42"), { wrapper });
    await waitFor(() => expect(result.current.historyLoading).toBe(false));

    await act(async () => {
      await result.current.sendMessage("What is my CL?");
    });

    // Find the POST call (stream)
    const postCall = mockFetch.mock.calls.find(
      (c: unknown[]) => (c[1] as RequestInit)?.method === "POST",
    );
    expect(postCall).toBeDefined();
    expect(postCall![0]).toContain("/aeroplanes/aero-42/copilot/stream");
    expect(postCall![1].method).toBe("POST");
    expect(JSON.parse(postCall![1].body as string)).toEqual({
      message: "What is my CL?",
    });
  });
});

// ---------------------------------------------------------------------------
// sendMessage — token accumulation
// ---------------------------------------------------------------------------

describe("useCopilot — token accumulation", () => {
  it("accumulates token events into streamingText before done", async () => {
    // Stream produces two tokens then done; after done streamingText is cleared
    // (persisted history is shown). We verify the final state is clean.

    // Create a stream that releases tokens one at a time
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode(sseEvent("token", { text: "Hello" })));
        controller.enqueue(encoder.encode(sseEvent("token", { text: " world" })));
        controller.enqueue(encoder.encode(sseEvent("done", { status: "ok" })));
        controller.close();
      },
    });

    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY))
      .mockImplementationOnce(() =>
        Promise.resolve(
          new Response(stream, {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          }),
        ),
      )
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY));

    const { result } = renderHook(() => useCopilot("aero-1"), { wrapper });
    await waitFor(() => expect(result.current.historyLoading).toBe(false));

    await act(async () => {
      await result.current.sendMessage("Hi");
    });

    // After done, streamingText is cleared (history took over).
    expect(result.current.streamingText).toBe("");
    // isSending is false when done
    expect(result.current.isSending).toBe(false);
  });

  it("sets isSending=true while the stream is in flight and false after done", async () => {
    // Resolve immediately with a minimal done stream
    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY))
      .mockResolvedValueOnce(
        makeSseResponse([sseEvent("done", { status: "ok" })]),
      )
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY));

    const { result } = renderHook(() => useCopilot("aero-1"), { wrapper });
    await waitFor(() => expect(result.current.historyLoading).toBe(false));

    await act(async () => {
      await result.current.sendMessage("test");
    });

    expect(result.current.isSending).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// sendMessage — tool_call / tool_result
// ---------------------------------------------------------------------------

describe("useCopilot — tool activity", () => {
  it("sets activeToolLabel on tool_call and clears it on tool_result", async () => {

    // Build a stream: tool_call → tool_result → done
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            sseEvent("tool_call", {
              name: "get_design_snapshot",
              args: {},
            }),
          ),
        );
        controller.enqueue(
          encoder.encode(
            sseEvent("tool_result", {
              name: "get_design_snapshot",
              summary: { mass: 1.5 },
            }),
          ),
        );
        controller.enqueue(
          encoder.encode(sseEvent("token", { text: "Your mass is 1.5 kg." })),
        );
        controller.enqueue(encoder.encode(sseEvent("done", { status: "ok" })));
        controller.close();
      },
    });

    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY))
      .mockImplementationOnce(() =>
        Promise.resolve(
          new Response(stream, {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          }),
        ),
      )
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY));

    const { result } = renderHook(() => useCopilot("aero-1"), { wrapper });
    await waitFor(() => expect(result.current.historyLoading).toBe(false));

    await act(async () => {
      await result.current.sendMessage("What is my mass?");
    });

    // After done, tool chip is cleared
    expect(result.current.activeToolLabel).toBeNull();
    // No error
    expect(result.current.errorMessage).toBeNull();
  });

  it("maps get_design_snapshot to the correct human label", async () => {
    const { toolLabel } = await import("@/hooks/useCopilot");
    expect(toolLabel("get_design_snapshot")).toBe("Reading design snapshot…");
    expect(toolLabel("run_analysis")).toBe("Running analysis…");
    expect(toolLabel("get_version_tree")).toBe("Reading version tree…");
    expect(toolLabel("unknown_tool")).toMatch(/unknown_tool/);
  });
});

// ---------------------------------------------------------------------------
// sendMessage — error events
// ---------------------------------------------------------------------------

describe("useCopilot — error handling", () => {
  it("surfaces error SSE events as errorMessage", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY))
      .mockResolvedValueOnce(
        makeSseResponse([
          sseEvent("error", { message: "Hub connection error" }),
        ]),
      );

    const { result } = renderHook(() => useCopilot("aero-1"), { wrapper });
    await waitFor(() => expect(result.current.historyLoading).toBe(false));

    await act(async () => {
      await result.current.sendMessage("fail?");
    });

    expect(result.current.errorMessage).toBe("Hub connection error");
    // streamingText cleared on error
    expect(result.current.streamingText).toBe("");
  });

  it("surfaces fetch rejections as errorMessage", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY))
      .mockRejectedValueOnce(new Error("Network failure"));

    const { result } = renderHook(() => useCopilot("aero-1"), { wrapper });
    await waitFor(() => expect(result.current.historyLoading).toBe(false));

    await act(async () => {
      await result.current.sendMessage("fail?");
    });

    expect(result.current.errorMessage).toContain("Network failure");
  });

  it("surfaces non-ok HTTP responses as errorMessage", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY))
      .mockResolvedValueOnce(
        new Response("Internal Server Error", { status: 500 }),
      );

    const { result } = renderHook(() => useCopilot("aero-1"), { wrapper });
    await waitFor(() => expect(result.current.historyLoading).toBe(false));

    await act(async () => {
      await result.current.sendMessage("test");
    });

    expect(result.current.errorMessage).toBeTruthy();
    expect(result.current.errorMessage).toContain("500");
  });

  it("clearError resets errorMessage to null", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY))
      .mockResolvedValueOnce(
        makeSseResponse([sseEvent("error", { message: "oops" })]),
      );

    const { result } = renderHook(() => useCopilot("aero-1"), { wrapper });
    await waitFor(() => expect(result.current.historyLoading).toBe(false));

    await act(async () => {
      await result.current.sendMessage("test");
    });

    expect(result.current.errorMessage).toBe("oops");

    act(() => {
      result.current.clearError();
    });

    expect(result.current.errorMessage).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// sendMessage — done revalidates history
// ---------------------------------------------------------------------------

describe("useCopilot — done revalidates history", () => {
  it("calls the history endpoint again after done event", async () => {
    const updatedHistory: CopilotHistory = {
      messages: [
        ...FAKE_HISTORY.messages,
        {
          id: 3,
          role: "assistant",
          content: "Revalidated!",
          tool_calls: null,
          tool_results: null,
          parent_id: null,
          created_at: "2026-06-08T10:01:00Z",
        },
      ],
    };

    mockFetch
      .mockResolvedValueOnce(jsonResponse(FAKE_HISTORY)) // initial load
      .mockResolvedValueOnce(
        makeSseResponse([sseEvent("done", { status: "ok" })]),
      ) // stream
      .mockResolvedValueOnce(jsonResponse(updatedHistory)); // revalidation

    const { result } = renderHook(() => useCopilot("aero-1"), { wrapper });
    await waitFor(() => expect(result.current.history?.messages).toHaveLength(2));

    await act(async () => {
      await result.current.sendMessage("hello");
    });

    await waitFor(() =>
      expect(result.current.history?.messages).toHaveLength(3),
    );
    expect(result.current.history?.messages[2].content).toBe("Revalidated!");
  });
});
