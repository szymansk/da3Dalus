/**
 * Unit tests for MarkerDetailBox component (gh-423).
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// ── Mocks ─────────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { X: icon };
});

import { MarkerDetailBox, type MarkerInfo } from "@/components/workbench/MarkerDetailBox";

// ── Test data ─────────────────────────────────────────────────────

const npMarker: MarkerInfo = {
  type: "np",
  neutral_point_x: 0.25,
  Cma: -1.2,
  stability_class: "stable",
  solver: "avl",
};

const cgMarker: MarkerInfo = {
  type: "cg",
  cg_x_used: 0.20,
  static_margin_pct: 33.3,
  source: "estimate",
};

const rangeMarker: MarkerInfo = {
  type: "range",
  cg_range_forward: 0.17,
  cg_range_aft: 0.24,
};

// ── Tests ─────────────────────────────────────────────────────────

describe("MarkerDetailBox", () => {
  it("renders NP details when type is np", () => {
    render(<MarkerDetailBox marker={npMarker} onClose={vi.fn()} />);
    expect(screen.getByText("Neutral Point")).toBeInTheDocument();
    expect(screen.getByText("0.250 m")).toBeInTheDocument();
    expect(screen.getByText("-1.200")).toBeInTheDocument();
    expect(screen.getByText("stable")).toBeInTheDocument();
    expect(screen.getByText("avl")).toBeInTheDocument();
  });

  it("renders CG details when type is cg", () => {
    render(<MarkerDetailBox marker={cgMarker} onClose={vi.fn()} />);
    expect(screen.getByText("Center of Gravity")).toBeInTheDocument();
    expect(screen.getByText("0.200 m")).toBeInTheDocument();
    expect(screen.getByText("33.3%")).toBeInTheDocument();
  });

  it("renders range details when type is range", () => {
    render(<MarkerDetailBox marker={rangeMarker} onClose={vi.fn()} />);
    expect(screen.getByText("CG Range")).toBeInTheDocument();
    expect(screen.getByText("0.170 m")).toBeInTheDocument();
    expect(screen.getByText("0.240 m")).toBeInTheDocument();
    expect(screen.getByText("0.070 m")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<MarkerDetailBox marker={npMarker} onClose={onClose} />);
    await user.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
