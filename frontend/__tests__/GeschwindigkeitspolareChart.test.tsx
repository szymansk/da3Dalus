/**
 * Unit tests for GeschwindigkeitspolareChart component (gh-841).
 *
 * Tests verify:
 * - Empty state when polar is null
 * - Loading state rendering
 * - Chart renders when data is provided
 * - Best-glide and min-sink markers present
 * - Tangent line present
 * - Disclaimer/title visible
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { GeschwindigkeitspolareChart } from "@/components/workbench/GeschwindigkeitspolareChart";
import type { AircraftSpeedPolar } from "@/hooks/useSpeedPolar";

// ---------------------------------------------------------------------------
// Test fixture
// ---------------------------------------------------------------------------

const MOCK_POLAR: AircraftSpeedPolar = {
  v_mps: [7.5, 8.0, 9.0, 10.0, 12.0, 14.0, 16.0, 20.0],
  sink_mps: [0.62, 0.58, 0.52, 0.50, 0.54, 0.62, 0.74, 1.1],
  cl: [1.4, 1.2, 0.95, 0.78, 0.54, 0.40, 0.31, 0.20],
  best_glide: { v_mps: 10.0, sink_mps: 0.50, cl: 0.78 },
  min_sink: { v_mps: 8.0, sink_mps: 0.58, cl: 1.2 },
  inputs: {
    mass_kg: 2.0,
    s_ref_m2: 0.40,
    ar: 8.0,
    e_oswald: 0.80,
    cd0: 0.025,
    rho: 1.225,
  },
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("GeschwindigkeitspolareChart", () => {
  it("renders empty state when polar is null", () => {
    render(<GeschwindigkeitspolareChart polar={null} />);
    expect(screen.getByTestId("speed-polar-empty")).toBeDefined();
  });

  it("renders loading state", () => {
    render(<GeschwindigkeitspolareChart polar={null} isLoading />);
    expect(screen.getByTestId("speed-polar-loading")).toBeDefined();
  });

  it("renders chart when polar data is provided", () => {
    render(<GeschwindigkeitspolareChart polar={MOCK_POLAR} />);
    expect(screen.getByTestId("geschwindigkeitspolare-chart")).toBeDefined();
  });

  it("renders the polar curve path", () => {
    render(<GeschwindigkeitspolareChart polar={MOCK_POLAR} />);
    expect(screen.getByTestId("speed-polar-curve")).toBeDefined();
  });

  it("renders best-glide marker", () => {
    render(<GeschwindigkeitspolareChart polar={MOCK_POLAR} />);
    expect(screen.getByTestId("speed-polar-best-glide-marker")).toBeDefined();
  });

  it("renders min-sink marker", () => {
    render(<GeschwindigkeitspolareChart polar={MOCK_POLAR} />);
    expect(screen.getByTestId("speed-polar-min-sink-marker")).toBeDefined();
  });

  it("renders best-glide tangent line", () => {
    render(<GeschwindigkeitspolareChart polar={MOCK_POLAR} />);
    expect(screen.getByTestId("speed-polar-best-glide-tangent")).toBeDefined();
  });

  it("shows chart title Geschwindigkeitspolare", () => {
    render(<GeschwindigkeitspolareChart polar={MOCK_POLAR} />);
    expect(screen.getByText(/Geschwindigkeitspolare/)).toBeDefined();
  });
});
