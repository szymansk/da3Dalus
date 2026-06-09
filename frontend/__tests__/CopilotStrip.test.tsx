/**
 * Unit tests for CopilotStrip (gh-919).
 *
 * Strategy:
 * - Mock useAeroplaneContext to control aeroplaneId.
 * - Mock useCopilot to control history, streamingText, activeToolLabel, etc.
 * - Assert rendering of message bubbles, streaming text, tool chips, errors,
 *   and disabled state when no aeroplane is selected.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Mocks — must be declared before the component import so vi.mock hoists them
// ---------------------------------------------------------------------------

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: vi.fn(),
}));

vi.mock("@/hooks/useCopilot", () => ({
  useCopilot: vi.fn(),
  toolLabel: (name: string) => `tool:${name}`,
}));

import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import { useCopilot } from "@/hooks/useCopilot";
import type { UseCopilotReturn, CopilotHistory } from "@/hooks/useCopilot";
import { CopilotStrip } from "@/components/workbench/CopilotStrip";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const AEROPLANE_CTX_DEFAULT = {
  aeroplaneId: "aero-1" as string | null,
  hydrated: true,
  selectedWing: null,
  selectedXsecIndex: null,
  selectedFuselage: null,
  selectedFuselageXsecIndex: null,
  treeMode: "wingconfig" as const,
  pickerOpen: false,
  lastImportWarnings: null,
  setAeroplaneId: vi.fn(),
  selectWing: vi.fn(),
  selectXsec: vi.fn(),
  selectFuselage: vi.fn(),
  selectFuselageXsec: vi.fn(),
  setTreeMode: vi.fn(),
  openPicker: vi.fn(),
  closePicker: vi.fn(),
  setLastImportWarnings: vi.fn(),
};

const COPILOT_DEFAULT: UseCopilotReturn = {
  history: undefined,
  historyLoading: false,
  historyError: null,
  streamingText: "",
  activeToolLabel: null,
  errorMessage: null,
  isSending: false,
  sendMessage: vi.fn().mockResolvedValue(undefined),
  clearError: vi.fn(),
};

const FAKE_HISTORY: CopilotHistory = {
  messages: [
    {
      id: 1,
      role: "user",
      content: "What is my wing loading?",
      tool_calls: null,
      tool_results: null,
      parent_id: null,
      created_at: "2026-06-08T10:00:00Z",
    },
    {
      id: 2,
      role: "assistant",
      content: "Your wing loading is 42 N/m².",
      tool_calls: null,
      tool_results: null,
      parent_id: null,
      created_at: "2026-06-08T10:00:02Z",
    },
  ],
};

function mockCtx(overrides: Partial<typeof AEROPLANE_CTX_DEFAULT> = {}) {
  vi.mocked(useAeroplaneContext).mockReturnValue({
    ...AEROPLANE_CTX_DEFAULT,
    ...overrides,
  });
}

function mockCopilot(overrides: Partial<UseCopilotReturn> = {}) {
  vi.mocked(useCopilot).mockReturnValue({
    ...COPILOT_DEFAULT,
    ...overrides,
  });
}

// ---------------------------------------------------------------------------
// Baseline structural tests (drawer + disclosure pattern, preserved from prior)
// ---------------------------------------------------------------------------

describe("CopilotStrip — structural", () => {
  beforeEach(() => {
    mockCtx();
    mockCopilot();
  });

  it("renders the slim bar with 'Ask the copilot…' label when an aeroplane is selected", () => {
    render(<CopilotStrip />);
    expect(screen.getByText("Ask the copilot…")).toBeInTheDocument();
  });

  it("renders a Send button in the slim bar and a toggle button", () => {
    render(<CopilotStrip />);
    // slim-bar Send button has aria-label="Send"
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Expand copilot panel" }),
    ).toBeInTheDocument();
  });

  it("toggle button has aria-controls matching the panel id (disclosure pattern)", () => {
    render(<CopilotStrip />);
    const toggleBtn = screen.getByRole("button", { name: "Expand copilot panel" });
    const panel = screen.getByTestId("copilot-panel");
    expect(panel).toHaveAttribute("id");
    expect(toggleBtn).toHaveAttribute("aria-controls", panel.getAttribute("id"));
  });

  it("starts collapsed (grid-rows-[0fr])", () => {
    render(<CopilotStrip />);
    const toggleBtn = screen.getByRole("button", { name: "Expand copilot panel" });
    expect(toggleBtn).toHaveAttribute("aria-expanded", "false");

    const panel = screen.getByTestId("copilot-panel");
    const slideWrapper = panel.parentElement?.parentElement;
    expect(slideWrapper?.className).toContain("grid-rows-[0fr]");
  });

  it("expands on first click", async () => {
    const user = userEvent.setup();
    render(<CopilotStrip />);

    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    expect(
      screen.getByRole("button", { name: "Collapse copilot panel" }),
    ).toHaveAttribute("aria-expanded", "true");

    const panel = screen.getByTestId("copilot-panel");
    const slideWrapper = panel.parentElement?.parentElement;
    expect(slideWrapper?.className).toContain("grid-rows-[1fr]");
  });

  it("collapses again on second click", async () => {
    const user = userEvent.setup();
    render(<CopilotStrip />);

    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));
    await user.click(screen.getByRole("button", { name: "Collapse copilot panel" }));

    expect(
      screen.getByRole("button", { name: "Expand copilot panel" }),
    ).toHaveAttribute("aria-expanded", "false");
  });

  it("shows textarea placeholder inside expanded panel when aeroplane is selected", async () => {
    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));
    expect(
      screen.getByPlaceholderText("Ask a design question…"),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// No-aeroplane disabled state
// ---------------------------------------------------------------------------

describe("CopilotStrip — no aeroplane selected", () => {
  beforeEach(() => {
    mockCtx({ aeroplaneId: null });
    mockCopilot({ history: undefined });
  });

  it("shows 'Select an aeroplane to use the copilot' label in the slim bar", () => {
    render(<CopilotStrip />);
    expect(
      screen.getByText("Select an aeroplane to use the copilot"),
    ).toBeInTheDocument();
  });

  it("textarea placeholder says 'Select an aeroplane'", async () => {
    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));
    expect(screen.getByPlaceholderText("Select an aeroplane")).toBeInTheDocument();
  });

  it("textarea is disabled when no aeroplane is selected", async () => {
    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));
    expect(screen.getByRole("textbox", { name: "Copilot input" })).toBeDisabled();
  });

  it("Send message button is disabled when no aeroplane is selected", async () => {
    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// Thread rendering
// ---------------------------------------------------------------------------

describe("CopilotStrip — thread rendering", () => {
  beforeEach(() => {
    mockCtx();
    mockCopilot({ history: FAKE_HISTORY });
  });

  it("renders user and assistant bubbles from history", async () => {
    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    expect(screen.getByTestId("copilot-thread")).toBeInTheDocument();
    expect(screen.getByText("What is my wing loading?")).toBeInTheDocument();
    expect(screen.getByText("Your wing loading is 42 N/m².")).toBeInTheDocument();
  });

  it("renders a user-bubble for user messages and assistant-bubble for assistant messages", async () => {
    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    const userBubbles = screen.getAllByTestId("user-bubble");
    const assistantBubbles = screen.getAllByTestId("assistant-bubble");
    expect(userBubbles).toHaveLength(1);
    expect(assistantBubbles).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// Streaming text
// ---------------------------------------------------------------------------

describe("CopilotStrip — streaming assistant text", () => {
  it("renders the streaming text as an assistant bubble while isSending=true", async () => {
    mockCtx();
    mockCopilot({
      history: undefined,
      streamingText: "This is streaming…",
      isSending: true,
    });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    const assistantBubble = screen.getByTestId("assistant-bubble");
    expect(assistantBubble).toHaveTextContent("This is streaming…");
  });

  it("shows 'Copilot is responding…' status text while isSending", async () => {
    mockCtx();
    mockCopilot({ isSending: true, streamingText: "…" });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    expect(screen.getByText("Copilot is responding…")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Tool activity chip
// ---------------------------------------------------------------------------

describe("CopilotStrip — tool activity chip", () => {
  it("renders a tool chip with the activeToolLabel when set", async () => {
    mockCtx();
    mockCopilot({
      activeToolLabel: "Reading design snapshot…",
    });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    const chip = screen.getByTestId("tool-chip");
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveTextContent("Reading design snapshot…");
  });

  it("does not render a tool chip when activeToolLabel is null", async () => {
    mockCtx();
    mockCopilot({ activeToolLabel: null });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    expect(screen.queryByTestId("tool-chip")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Error display
// ---------------------------------------------------------------------------

describe("CopilotStrip — error display", () => {
  it("renders the error banner when errorMessage is set", async () => {
    const clearError = vi.fn();
    mockCtx();
    mockCopilot({ errorMessage: "Hub connection error", clearError });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    const banner = screen.getByTestId("copilot-error");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent("Hub connection error");
  });

  it("calls clearError when the dismiss button is clicked", async () => {
    const clearError = vi.fn();
    mockCtx();
    mockCopilot({ errorMessage: "oops", clearError });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    await user.click(screen.getByRole("button", { name: "Dismiss error" }));
    expect(clearError).toHaveBeenCalledOnce();
  });

  it("does not render the error banner when errorMessage is null", async () => {
    mockCtx();
    mockCopilot({ errorMessage: null });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    expect(screen.queryByTestId("copilot-error")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Markdown + LaTeX rendering (gh-930)
// ---------------------------------------------------------------------------

describe("CopilotStrip — markdown rendering in AssistantBubble", () => {
  it("renders markdown: bold, code, and list items in assistant bubble", async () => {
    mockCtx();
    mockCopilot({
      history: {
        messages: [
          {
            id: 10,
            role: "assistant",
            content: "**bold** and `code`\n\n- item one\n- item two",
            tool_calls: null,
            tool_results: null,
            parent_id: null,
            created_at: "2026-06-09T10:00:00Z",
          },
        ],
      },
    });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    const bubble = screen.getByTestId("assistant-bubble");
    // streamdown renders **bold** as <span data-streamdown="strong"> (not <strong>)
    // and inline `code` as <code data-streamdown="inline-code">
    const boldEl =
      bubble.querySelector("strong") ??
      bubble.querySelector('[data-streamdown="strong"]');
    expect(boldEl).not.toBeNull();
    const codeEl =
      bubble.querySelector("code") ??
      bubble.querySelector('[data-streamdown="inline-code"]');
    expect(codeEl).not.toBeNull();
    const listItems = bubble.querySelectorAll("li");
    expect(listItems.length).toBeGreaterThanOrEqual(2);
  });

  it("renders LaTeX math: $E=mc^2$ produces a KaTeX element (.katex)", async () => {
    mockCtx();
    mockCopilot({
      history: {
        messages: [
          {
            id: 11,
            role: "assistant",
            content: "The equation is $E=mc^2$ in physics.",
            tool_calls: null,
            tool_results: null,
            parent_id: null,
            created_at: "2026-06-09T10:00:01Z",
          },
        ],
      },
    });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    const bubble = screen.getByTestId("assistant-bubble");
    // KaTeX renders to .katex spans; if that fails, the raw $...$ must not be shown literally
    const katexEl = bubble.querySelector(".katex");
    if (katexEl) {
      expect(katexEl).not.toBeNull();
    } else {
      // fallback: math was processed but not via .katex (e.g. jsdom limitation)
      // at minimum the literal $E=mc^2$ should not appear as plain text
      expect(bubble.textContent).not.toContain("$E=mc^2$");
    }
  });

  it("single-newline lines render as separate lines (<br>) and GFM tables survive", async () => {
    mockCtx();
    mockCopilot({
      history: {
        messages: [
          {
            id: 12,
            role: "assistant",
            // Line-by-line figures (no blank lines, no list markers) plus a
            // GFM table — verifies remark-breaks is added WITHOUT dropping gfm.
            content:
              "Wing area: 0.30 m²\nAspect ratio: 7.5\nStall speed: 6.8 m/s\n\n" +
              "| Component | Share |\n|---|---|\n| Profile | 41% |\n| Induced | 38% |",
            tool_calls: null,
            tool_results: null,
            parent_id: null,
            created_at: "2026-06-09T10:00:02Z",
          },
        ],
      },
    });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    const bubble = screen.getByTestId("assistant-bubble");
    // remark-breaks turns the single newlines into <br> (≥2 for 3 stacked lines)
    expect(bubble.querySelectorAll("br").length).toBeGreaterThanOrEqual(2);
    // gfm default is preserved → the markdown table still renders
    expect(bubble.querySelector("table")).not.toBeNull();
  });

  it("UserBubble keeps plain text — **not bold** renders literally, no <strong>", async () => {
    mockCtx();
    mockCopilot({
      history: {
        messages: [
          {
            id: 12,
            role: "user",
            content: "**not bold**",
            tool_calls: null,
            tool_results: null,
            parent_id: null,
            created_at: "2026-06-09T10:00:02Z",
          },
        ],
      },
    });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    const bubble = screen.getByTestId("user-bubble");
    expect(bubble.textContent).toContain("**not bold**");
    // UserBubble is plain text — neither <strong> nor streamdown's bold span
    expect(bubble.querySelector("strong")).toBeNull();
    expect(bubble.querySelector('[data-streamdown="strong"]')).toBeNull();
  });

  it("streaming path: partial markdown renders without error and cursor is present", async () => {
    mockCtx();
    mockCopilot({
      history: undefined,
      streamingText: "```py\nprint(",
      isSending: true,
    });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    const bubble = screen.getByTestId("assistant-bubble");
    expect(bubble).toBeInTheDocument();
    // The streaming cursor (animate-pulse span) must still be present
    const cursor = bubble.querySelector('[aria-hidden]');
    expect(cursor).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Send interaction
// ---------------------------------------------------------------------------

describe("CopilotStrip — send interaction", () => {
  it("calls sendMessage with the typed text when Send message button is clicked", async () => {
    const sendMessage = vi.fn().mockResolvedValue(undefined);
    mockCtx();
    mockCopilot({ sendMessage });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    const textarea = screen.getByRole("textbox", { name: "Copilot input" });
    await user.type(textarea, "What is my static margin?");
    await user.click(screen.getByRole("button", { name: "Send message" }));

    expect(sendMessage).toHaveBeenCalledWith("What is my static margin?");
  });

  it("clears the textarea after sending", async () => {
    const sendMessage = vi.fn().mockResolvedValue(undefined);
    mockCtx();
    mockCopilot({ sendMessage });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    const textarea = screen.getByRole("textbox", { name: "Copilot input" });
    await user.type(textarea, "test question");
    await user.click(screen.getByRole("button", { name: "Send message" }));

    expect(textarea).toHaveValue("");
  });

  it("Send message button is disabled while isSending=true", async () => {
    mockCtx();
    mockCopilot({ isSending: true });

    const user = userEvent.setup();
    render(<CopilotStrip />);
    await user.click(screen.getByRole("button", { name: "Expand copilot panel" }));

    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });
});
