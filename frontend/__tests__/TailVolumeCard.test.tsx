import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

// Mock the hook before importing the component
vi.mock("@/hooks/useTailSizing", async () => {
  const actual = await vi.importActual("@/hooks/useTailSizing");
  return {
    ...actual,
    useTailSizing: vi.fn(),
  };
});

import { TailVolumeCard } from "@/components/workbench/TailVolumeCard";
import { useTailSizing } from "@/hooks/useTailSizing";

const MOCK_RESULT_IN_RANGE = {
  v_h_current: 0.62,
  v_v_current: 0.042,
  l_h_m: 4.97,
  l_h_eff_from_aft_cg_m: 4.80,
  s_h_recommended_mm2: 270000,
  s_v_recommended_mm2: 50000,
  classification: "in_range" as const,
  classification_h: "in_range" as const,
  classification_v: "in_range" as const,
  aircraft_class_used: "rc_trainer",
  cg_aware: true,
  v_h_target_min: 0.55,
  v_h_target_max: 0.70,
  v_v_target_min: 0.040,
  v_v_target_max: 0.050,
  v_h_citation: "Lennon Ch.5",
  v_v_citation: "Lennon Ch.5",
  warnings: [],
};

const MOCK_RESULT_BELOW = {
  ...MOCK_RESULT_IN_RANGE,
  v_h_current: 0.40,
  classification: "below_range" as const,
  classification_h: "below_range" as const,
  warnings: ["V_H = 0.400 below target 0.55–0.70 for rc_trainer"],
};

const MOCK_RESULT_NOT_APPLICABLE = {
  ...MOCK_RESULT_IN_RANGE,
  classification: "not_applicable" as const,
  classification_h: "not_applicable" as const,
  classification_v: "not_applicable" as const,
  v_h_current: null,
  v_v_current: null,
};

function setupMock(
  data: typeof MOCK_RESULT_IN_RANGE | null,
  opts: { isLoading?: boolean } = {}
) {
  const recomputeOnce = vi.fn().mockResolvedValue(undefined);
  (useTailSizing as ReturnType<typeof vi.fn>).mockReturnValue({
    data,
    isLoading: opts.isLoading ?? false,
    error: null,
    mutate: vi.fn(),
    recomputeOnce,
  });
  return { recomputeOnce };
}

describe("TailVolumeCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the card with V_H and V_V values when in_range", () => {
    setupMock(MOCK_RESULT_IN_RANGE);
    render(<TailVolumeCard aeroplaneId="test-id" />);

    expect(screen.getByTestId("tail-volume-card")).toBeInTheDocument();
    expect(screen.getByTestId("tail-volume-row-V_H")).toBeInTheDocument();
    expect(screen.getByTestId("tail-volume-row-V_V")).toBeInTheDocument();
  });

  it("shows current V_H value", () => {
    setupMock(MOCK_RESULT_IN_RANGE);
    render(<TailVolumeCard aeroplaneId="test-id" />);

    expect(screen.getByText("0.620")).toBeInTheDocument();
  });

  it("shows target range with citation for V_H", () => {
    setupMock(MOCK_RESULT_IN_RANGE);
    render(<TailVolumeCard aeroplaneId="test-id" />);

    expect(screen.getByText(/0.550–0.700/)).toBeInTheDocument();
    // Lennon Ch.5 appears for both V_H and V_V rows
    expect(screen.getAllByText(/Lennon Ch.5/).length).toBeGreaterThanOrEqual(1);
  });

  it("shows recommended S_H with pencil button", () => {
    setupMock(MOCK_RESULT_IN_RANGE);
    render(<TailVolumeCard aeroplaneId="test-id" />);

    const btn = screen.getByTestId("tail-volume-apply-V_H");
    expect(btn).toBeInTheDocument();
    // 270000 mm² → "270,000 mm²"
    expect(btn.textContent).toMatch(/270/);
  });

  it("hides card when classification is not_applicable", () => {
    setupMock(MOCK_RESULT_NOT_APPLICABLE);
    const { container } = render(<TailVolumeCard aeroplaneId="test-id" />);
    expect(container.firstChild).toBeNull();
  });

  it("shows warning text when below_range", () => {
    setupMock(MOCK_RESULT_BELOW);
    render(<TailVolumeCard aeroplaneId="test-id" />);

    expect(
      screen.getByText(/below target 0.55/i),
    ).toBeInTheDocument();
  });

  it("shows 'no polar' badge when cg_aware is false", () => {
    const data = { ...MOCK_RESULT_IN_RANGE, cg_aware: false };
    setupMock(data);
    render(<TailVolumeCard aeroplaneId="test-id" />);

    expect(screen.getByText(/no polar/i)).toBeInTheDocument();
  });

  it("calls recomputeOnce exactly once when pencil-action is clicked", async () => {
    const onApplySh = vi.fn();
    const { recomputeOnce } = setupMock(MOCK_RESULT_IN_RANGE);
    render(
      <TailVolumeCard
        aeroplaneId="test-id"
        onApplySh={onApplySh}
      />,
    );

    fireEvent.click(screen.getByTestId("tail-volume-apply-V_H"));

    await waitFor(() => {
      expect(onApplySh).toHaveBeenCalledWith(270000);
      // Exactly ONE recompute — no cascade
      expect(recomputeOnce).toHaveBeenCalledTimes(1);
    });
  });

  it("shows l_H (wing-AC) and l_H eff (aft-CG) secondary metrics", () => {
    setupMock(MOCK_RESULT_IN_RANGE);
    render(<TailVolumeCard aeroplaneId="test-id" />);

    expect(screen.getByText(/wing-AC → tail-AC/i)).toBeInTheDocument();
    expect(screen.getByText(/aft-CG → tail-AC/i)).toBeInTheDocument();
    expect(screen.getByText(/4.970 m/)).toBeInTheDocument();
    expect(screen.getByText(/4.800 m/)).toBeInTheDocument();
  });

  it("shows loading state", () => {
    setupMock(null, { isLoading: true });
    render(<TailVolumeCard aeroplaneId="test-id" />);

    expect(screen.getByText(/Computing/i)).toBeInTheDocument();
  });
});
