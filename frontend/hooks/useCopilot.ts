"use client";

/**
 * useCopilot — streaming copilot hook for the CopilotStrip (gh-919).
 *
 * - History is loaded via SWR: GET /aeroplanes/{id}/copilot-history
 * - sendMessage POSTs to /aeroplanes/{id}/copilot/stream and consumes the
 *   SSE response via parseSseStream (same pattern as useOperatingPoints).
 * - Streaming state (in-progress text, current tool activity) is exposed
 *   so the strip can render tokens and tool chips live.
 * - On "done" we revalidate the SWR cache so persisted history is shown.
 * - Errors from "error" events are surfaced as errorMessage.
 */

import { useCallback, useState } from "react";
import useSWR from "swr";
import { API_BASE } from "@/lib/fetcher";
import { parseSseStream } from "@/lib/sseStream";

// ---------------------------------------------------------------------------
// Types — mirror app/schemas/copilot_history.py
// ---------------------------------------------------------------------------

export interface CopilotMessageRead {
  id: number;
  role: "user" | "assistant" | "tool";
  content: string;
  tool_calls: Record<string, unknown>[] | null;
  tool_results: Record<string, unknown>[] | null;
  parent_id: number | null;
  created_at: string;
}

export interface CopilotHistory {
  messages: CopilotMessageRead[];
}

// ---------------------------------------------------------------------------
// SSE event payloads
// ---------------------------------------------------------------------------

interface TokenEvent {
  text: string;
}

interface ToolCallEvent {
  name: string;
  args: Record<string, unknown>;
}

interface DoneEvent {
  status?: string;
  truncated?: boolean;
}

interface ErrorEvent {
  message: string;
}

// ---------------------------------------------------------------------------
// Tool label map — human-readable chip label per tool name
// ---------------------------------------------------------------------------

const TOOL_LABEL_MAP: Record<string, string> = {
  get_design_snapshot: "Reading design snapshot…",
  run_analysis: "Running analysis…",
  get_version_tree: "Reading version tree…",
};

export function toolLabel(name: string): string {
  return TOOL_LABEL_MAP[name] ?? `Calling ${name}…`;
}

// ---------------------------------------------------------------------------
// Hook return type
// ---------------------------------------------------------------------------

export interface UseCopilotReturn {
  /** Persisted history from the server (SWR). */
  history: CopilotHistory | undefined;
  historyLoading: boolean;
  historyError: Error | null;

  /** Accumulated assistant text while a response is streaming. */
  streamingText: string;

  /** Human-readable label of the currently active tool call (or null). */
  activeToolLabel: string | null;

  /** Error message from a "error" SSE event or a fetch failure. */
  errorMessage: string | null;

  /** True while a POST is in-flight (streaming). */
  isSending: boolean;

  /** Send a user message and stream the copilot response. */
  sendMessage: (text: string) => Promise<void>;

  /** Clear any error message. */
  clearError: () => void;
}

// ---------------------------------------------------------------------------
// useCopilot
// ---------------------------------------------------------------------------

export function useCopilot(aeroplaneId: string | null): UseCopilotReturn {
  const historyKey = aeroplaneId
    ? `${API_BASE}/aeroplanes/${encodeURIComponent(aeroplaneId)}/copilot-history`
    : null;

  const {
    data: history,
    isLoading: historyLoading,
    error: historyError,
    mutate: revalidateHistory,
  } = useSWR<CopilotHistory>(
    historyKey,
    async (url: string) => {
      const res = await fetch(url);
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`${res.status}: ${body}`);
      }
      return res.json() as Promise<CopilotHistory>;
    },
    { revalidateOnFocus: false },
  );

  const [streamingText, setStreamingText] = useState<string>("");
  const [activeToolLabel, setActiveToolLabel] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSending, setIsSending] = useState<boolean>(false);

  const clearError = useCallback(() => setErrorMessage(null), []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!aeroplaneId) return;

      setIsSending(true);
      setStreamingText("");
      setActiveToolLabel(null);
      setErrorMessage(null);

      try {
        const res = await fetch(
          `${API_BASE}/aeroplanes/${encodeURIComponent(aeroplaneId)}/copilot/stream`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text }),
          },
        );

        if (!res.ok) {
          const body = await res.text().catch(() => "");
          throw new Error(`Copilot error: ${res.status} ${body}`);
        }

        let accumulated = "";

        for await (const { event, data } of parseSseStream<unknown>(res)) {
          if (event === "token") {
            const payload = data as TokenEvent;
            accumulated += payload.text ?? "";
            setStreamingText(accumulated);
          } else if (event === "tool_call") {
            const payload = data as ToolCallEvent;
            setActiveToolLabel(toolLabel(payload.name ?? ""));
          } else if (event === "tool_result") {
            // Tool call is complete — clear the chip
            setActiveToolLabel(null);
          } else if (event === "done") {
            const payload = data as DoneEvent;
            setStreamingText("");
            setActiveToolLabel(null);
            if (payload?.truncated) {
              // Turn was cut off at the max-iterations guard — surface as info
              setErrorMessage(
                "Response was cut off (too many tool calls). See the Analysis tab for details.",
              );
            }
            // Revalidate so persisted history is shown
            await revalidateHistory();
          } else if (event === "error") {
            const payload = data as ErrorEvent;
            setErrorMessage(payload.message ?? "An error occurred.");
            setStreamingText("");
            setActiveToolLabel(null);
          }
        }
      } catch (err) {
        setErrorMessage(err instanceof Error ? err.message : String(err));
        setStreamingText("");
        setActiveToolLabel(null);
      } finally {
        setIsSending(false);
      }
    },
    [aeroplaneId, revalidateHistory],
  );

  return {
    history,
    historyLoading,
    historyError: historyError ?? null,
    streamingText,
    activeToolLabel,
    errorMessage,
    isSending,
    sendMessage,
    clearError,
  };
}
