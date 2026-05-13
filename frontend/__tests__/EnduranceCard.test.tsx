/**
 * Unit tests for EnduranceCard component — gh-490.
 * Mocks the useEndurance hook to avoid SWR/fetch plumbing.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import type { EnduranceData } from "@/hooks/useEndurance";

// ── Hook mock ────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    AlertTriangle: icon,
    Battery: icon,
    Gauge: icon,
    Loader2: icon,
    Navigation: icon,
  };
});

let hookReturn: {
  data: EnduranceData | null | undefined;
  error: Error | null;
  isLoading: boolean;
  mutate: ReturnType<typeof vi.fn>;
};

vi.mock("@/hooks/useEndurance", () => ({
  useEndurance: () => hookReturn,
}));

import { EnduranceCard } from "@/components/workbench/EnduranceCard";

// ── Test data ────────────────────────────────────────────────────

const MOCK_COMPUTED: EnduranceData = {
  t_endurance_max_s: 600,
  range_max_m: 8000,
  p_req_at_v_md_w: 42.3,
  p_req_at_v_min_sink_w: 28.1,
  p_margin: 0.79,
  p_margin_class: "comfortable",
  battery_mass_g_predicted: 411.1,
  confidence: "computed",
  warnings: [],
};

const MOCK_ESTIMATED: EnduranceData = {
  ...MOCK_COMPUTED,
  confidence: "estimated",
  warnings: ["Endurance derived from fallback e=0.8 — polar fit unreliable."],
};

const MOCK_INFEASIBLE: EnduranceData = {
  ...MOCK_COMPUTED,
  p_margin: -0.33,
  p_margin_class: "infeasible — motor underpowered",
};

describe("EnduranceCard", () => {
  beforeEach(() => {
    hookReturn = { data: undefined, error: null, isLoading: false, mutate: vi.fn() };
  });

  it("renders null when aeroplaneId is null", () => {
    const { container } = render(<EnduranceCard aeroplaneId={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows loading state when isLoading is true", () => {
    hookReturn = { data: undefined, error: null, isLoading: true, mutate: vi.fn() };
    render(<EnduranceCard aeroplaneId="abc-123" />);
    expect(screen.getByText(/computing endurance/i)).toBeInTheDocument();
  });

  it("shows error state when fetch fails", () => {
    hookReturn = { data: null, error: new Error("Network error"), isLoading: false, mutate: vi.fn() };
    render(<EnduranceCard aeroplaneId="abc-123" />);
    expect(screen.getByText(/endurance unavailable/i)).toBeInTheDocument();
  });

  it("shows endurance mode by default", () => {
    hookReturn = { data: MOCK_COMPUTED, error: null, isLoading: false, mutate: vi.fn() };
    render(<EnduranceCard aeroplaneId="abc-123" />);
    expect(screen.getByText("10.0 min")).toBeInTheDocument();
    // "Max Endurance" text appears in both the mode button and the label
    const maxEnduranceElements = screen.getAllByText(/Max Endurance/);
    expect(maxEnduranceElements.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/at V_min_sink/)).toBeInTheDocument();
  });

  it("shows range when Max Range mode is clicked", async () => {
    hookReturn = { data: MOCK_COMPUTED, error: null, isLoading: false, mutate: vi.fn() };
    render(<EnduranceCard aeroplaneId="abc-123" />);

    const rangeBtn = screen.getByRole("button", { name: /max range/i });
    await userEvent.click(rangeBtn);

    expect(screen.getByText("8.0 km")).toBeInTheDocument();
    expect(screen.getByText(/at V_md/)).toBeInTheDocument();
  });

  it("shows computed confidence chip", () => {
    hookReturn = { data: MOCK_COMPUTED, error: null, isLoading: false, mutate: vi.fn() };
    render(<EnduranceCard aeroplaneId="abc-123" />);
    expect(screen.getByText("Computed")).toBeInTheDocument();
  });

  it("shows estimated chip and warning when confidence=estimated", () => {
    hookReturn = { data: MOCK_ESTIMATED, error: null, isLoading: false, mutate: vi.fn() };
    render(<EnduranceCard aeroplaneId="abc-123" />);
    expect(screen.getByText("Estimated")).toBeInTheDocument();
    expect(screen.getByText(/polar fit unreliable/i)).toBeInTheDocument();
  });

  it("shows p_margin_class chip", () => {
    hookReturn = { data: MOCK_COMPUTED, error: null, isLoading: false, mutate: vi.fn() };
    render(<EnduranceCard aeroplaneId="abc-123" />);
    expect(screen.getByText("comfortable")).toBeInTheDocument();
  });

  it("shows infeasible p_margin_class", () => {
    hookReturn = { data: MOCK_INFEASIBLE, error: null, isLoading: false, mutate: vi.fn() };
    render(<EnduranceCard aeroplaneId="abc-123" />);
    expect(screen.getByText(/infeasible/i)).toBeInTheDocument();
  });

  it("returns null when data is undefined and not loading", () => {
    hookReturn = { data: undefined, error: null, isLoading: false, mutate: vi.fn() };
    const { container } = render(<EnduranceCard aeroplaneId="abc-123" />);
    // Should render nothing (data is undefined, not loading, no error)
    expect(container.firstChild).toBeNull();
  });
});
