import { describe, it, expect } from "vitest";
import { buildStabilityTraces } from "@/components/workbench/stability-overlay/buildStabilityTraces";

const FULL = {
  x_np_m: 2.607,
  mac_m: 1.387,
  cg_agg_m: 2.510,
  target_static_margin: 0.12,
};

describe("buildStabilityTraces", () => {
  describe("complete data", () => {
    const traces = buildStabilityTraces(FULL);

    it("returns 5 traces: NP, CG SOLL, CG IST, SM band, delta link", () => {
      expect(traces).toHaveLength(5);
    });

    it("places NP at x_np_m (metres) along the x axis", () => {
      const np = traces.find((t) => t.name === "NP")!;
      expect((np.x as number[])[0]).toBeCloseTo(2.607, 3);
    });

    it("places CG SOLL at x_np_m − target_sm · mac_m (metres)", () => {
      const cgSoll = traces.find((t) => t.name === "CG (design)")!;
      const expected = 2.607 - 0.12 * 1.387;
      expect((cgSoll.x as number[])[0]).toBeCloseTo(expected, 3);
    });

    it("places CG IST at cg_agg_m (metres)", () => {
      const cgIst = traces.find((t) => t.name === "CG (actual)")!;
      expect((cgIst.x as number[])[0]).toBeCloseTo(2.510, 3);
    });

    it("uses orange #FF8400 for CG SOLL marker", () => {
      const cgSoll = traces.find((t) => t.name === "CG (design)")!;
      const marker = cgSoll.marker as { color?: string };
      expect(marker.color?.toUpperCase()).toBe("#FF8400");
    });

    it("renders SM band as a line between SOLL CG and NP", () => {
      const band = traces.find((t) => t.name === "Static Margin")!;
      expect((band.x as number[]).length).toBe(2);
      expect(band.mode).toBe("lines");
    });

    it("renders delta link only when |Δ|/MAC > 1%", () => {
      // FULL: SOLL = 2.607 - 0.12*1.387 ≈ 2.44056
      // |2.510 - 2.44056| / 1.387 ≈ 5.0% MAC → above threshold → link rendered
      const link = traces.find((t) => t.name === "Δ SOLL→IST");
      expect(link).toBeDefined();
    });
  });

  describe("graceful degradation", () => {
    it("omits CG IST trace when cg_agg_m is null", () => {
      const traces = buildStabilityTraces({ ...FULL, cg_agg_m: null });
      expect(traces.find((t) => t.name === "CG (actual)")).toBeUndefined();
      expect(traces.find((t) => t.name === "Δ SOLL→IST")).toBeUndefined();
    });

    it("returns empty array when x_np_m is null", () => {
      const traces = buildStabilityTraces({ ...FULL, x_np_m: null });
      expect(traces).toEqual([]);
    });

    it("omits SM band and CG SOLL when target_static_margin is null", () => {
      const traces = buildStabilityTraces({ ...FULL, target_static_margin: null });
      expect(traces.find((t) => t.name === "Static Margin")).toBeUndefined();
      expect(traces.find((t) => t.name === "CG (design)")).toBeUndefined();
      // IST still rendered (cg_agg_m present)
      expect(traces.find((t) => t.name === "CG (actual)")).toBeDefined();
      // NP always present
      expect(traces.find((t) => t.name === "NP")).toBeDefined();
    });

    it("does not render delta link when |Δ|/MAC ≤ 1%", () => {
      const cgIstAtSoll = 2.607 - 0.12 * 1.387; // exactly at SOLL → Δ = 0
      const traces = buildStabilityTraces({ ...FULL, cg_agg_m: cgIstAtSoll });
      expect(traces.find((t) => t.name === "Δ SOLL→IST")).toBeUndefined();
    });
  });

  describe("reference point (chord-line placement)", () => {
    it("places NP at the provided y/z when opts.referenceY/referenceZ given", () => {
      const traces = buildStabilityTraces(FULL, { referenceY: 0, referenceZ: 0.45 });
      const np = traces.find((t) => t.name === "NP")!;
      expect((np.y as number[])[0]).toBeCloseTo(0, 6);
      expect((np.z as number[])[0]).toBeCloseTo(0.45, 6);
    });

    it("places SM band endpoints at the provided z (line stays planar at refZ)", () => {
      const traces = buildStabilityTraces(FULL, { referenceY: 0, referenceZ: 0.45 });
      const band = traces.find((t) => t.name === "Static Margin")!;
      const zs = band.z as number[];
      expect(zs.every((z) => Math.abs(z - 0.45) < 1e-6)).toBe(true);
    });

    it("falls back to y=0, z=0 when opts is omitted", () => {
      const traces = buildStabilityTraces(FULL);
      const np = traces.find((t) => t.name === "NP")!;
      expect((np.y as number[])[0]).toBe(0);
      expect((np.z as number[])[0]).toBe(0);
    });
  });

  describe("hovertext", () => {
    const traces = buildStabilityTraces(FULL);

    it("NP trace hovertext includes the NP value in metres", () => {
      const np = traces.find((t) => t.name === "NP")!;
      expect(String(np.hovertext)).toContain("2.607");
    });

    it("CG IST trace hovertext includes Δ value with % MAC suffix", () => {
      const ist = traces.find((t) => t.name === "CG (actual)")!;
      const text = String(ist.hovertext);
      expect(text).toContain("% MAC");
      expect(text).toMatch(/Δ to target = [+-]\d+\.\d+ % MAC/);
    });
  });
});
