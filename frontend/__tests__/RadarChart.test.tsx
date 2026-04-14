import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RadarChart, polarToCartesian, buildPolygonPoints } from "@/components/workbench/RadarChart";

const AXES = [
  { key: "payload", label: "Payload" },
  { key: "flight_time", label: "Flight Time" },
  { key: "speed", label: "Cruise Speed" },
  { key: "range", label: "Range" },
  { key: "ceiling", label: "Ceiling" },
];

const TARGET = { payload: 0.5, flight_time: 0.7, speed: 0.6, range: 0.4, ceiling: 0.8 };
const ANALYSIS = { payload: 0.3, flight_time: 0.5, speed: 0.8, range: 0.6, ceiling: 0.4 };

describe("RadarChart", () => {
  it("renders all 5 axis labels", () => {
    render(<RadarChart axes={AXES} target={TARGET} />);
    for (const axis of AXES) {
      expect(screen.getByText(axis.label)).toBeDefined();
    }
  });

  it("renders grid rings", () => {
    render(<RadarChart axes={AXES} target={TARGET} />);
    const rings = screen.getAllByTestId("grid-ring");
    expect(rings.length).toBe(3);
  });

  it("renders target polygon", () => {
    render(<RadarChart axes={AXES} target={TARGET} />);
    const poly = screen.getByTestId("target-polygon");
    expect(poly.getAttribute("stroke")).toBe("var(--color-primary)");
    expect(poly.getAttribute("fill")).toBe("#FF840030");
  });

  it("does not render analysis polygon when null", () => {
    render(<RadarChart axes={AXES} target={TARGET} analysis={null} />);
    expect(screen.queryByTestId("analysis-polygon")).toBeNull();
  });

  it("renders analysis polygon when provided", () => {
    render(<RadarChart axes={AXES} target={TARGET} analysis={ANALYSIS} />);
    const poly = screen.getByTestId("analysis-polygon");
    expect(poly.getAttribute("stroke")).toBe("var(--color-success)");
    expect(poly.getAttribute("fill")).toBe("#30A46C30");
  });

  it("handles all-zero target values", () => {
    const zeros = { payload: 0, flight_time: 0, speed: 0, range: 0, ceiling: 0 };
    expect(() => render(<RadarChart axes={AXES} target={zeros} />)).not.toThrow();
  });

  it("handles all-max target values", () => {
    const maxes = { payload: 1, flight_time: 1, speed: 1, range: 1, ceiling: 1 };
    expect(() => render(<RadarChart axes={AXES} target={maxes} />)).not.toThrow();
  });

  it("uses custom size in viewBox", () => {
    render(<RadarChart axes={AXES} target={TARGET} size={300} />);
    const svg = screen.getByTestId("radar-chart");
    expect(svg.getAttribute("viewBox")).toContain("300");
  });
});

describe("polarToCartesian", () => {
  it("returns center at r=0", () => {
    const pt = polarToCartesian(100, 100, 0, Math.PI);
    expect(pt.x).toBeCloseTo(100);
    expect(pt.y).toBeCloseTo(100);
  });
});

describe("buildPolygonPoints", () => {
  it("returns space-separated coordinate pairs", () => {
    const angles = [0, Math.PI / 2];
    const result = buildPolygonPoints(0, 0, 10, [1, 1], angles);
    expect(result.split(" ").length).toBe(2);
    expect(result).toContain(",");
  });
});
