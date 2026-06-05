/**
 * Unit tests for the useSpeedPolar hook type definitions (gh-841).
 *
 * The hook itself is a thin SWR wrapper — we verify the TypeScript interface
 * shapes are correct rather than mocking fetch (integration covered by E2E).
 */

import { describe, it, expect } from "vitest";
import type { AircraftSpeedPolar, SpeedPolarPoint } from "@/hooks/useSpeedPolar";

// ---------------------------------------------------------------------------
// Type-level smoke tests — verify the interface is correct
// ---------------------------------------------------------------------------

describe("AircraftSpeedPolar interface (gh-841)", () => {
  it("accepts a fully-populated speed polar", () => {
    const pt: SpeedPolarPoint = { v_mps: 10.0, sink_mps: 0.5, cl: 0.8 };
    const polar: AircraftSpeedPolar = {
      v_mps: [8.0, 10.0, 14.0, 20.0],
      sink_mps: [0.65, 0.50, 0.55, 0.85],
      cl: [1.2, 0.8, 0.5, 0.25],
      best_glide: pt,
      min_sink: { v_mps: 8.0, sink_mps: 0.65, cl: 1.2 },
      inputs: {
        mass_kg: 2.0,
        s_ref_m2: 0.4,
        ar: 8.0,
        e_oswald: 0.8,
        cd0: 0.025,
        rho: 1.225,
      },
    };
    expect(polar.v_mps.length).toBe(4);
    expect(polar.best_glide.v_mps).toBe(10.0);
    expect(polar.inputs.cd0).toBe(0.025);
  });

  it("SpeedPolarPoint has required numeric fields", () => {
    const pt: SpeedPolarPoint = { v_mps: 12.3, sink_mps: 0.48, cl: 0.71 };
    expect(pt.v_mps).toBeGreaterThan(0);
    expect(pt.sink_mps).toBeGreaterThan(0);
    expect(pt.cl).toBeGreaterThan(0);
  });
});
