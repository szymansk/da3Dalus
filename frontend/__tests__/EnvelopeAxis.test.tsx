/**
 * gh-897: EnvelopeAxis must not emit duplicate React keys when two speed
 * markers coincide (same value + kind, e.g. V_md == V_cruise). The colour
 * zones are derived from sorted markers; a coincident marker produces a
 * zero-width zone that previously collided on the `${kind}-${to}` key.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render } from "@testing-library/react";
import { EnvelopeAxis } from "@/components/workbench/metrics-dashboard/primitives";
import type { SpeedMarker } from "@/components/workbench/metrics-dashboard/metricsTypes";

function marker(
  symbol: string,
  value: number,
  kind: SpeedMarker["kind"] = "normal",
): SpeedMarker {
  return { symbol, label: symbol, value, kind };
}

// Two markers at the same value AND kind — the reported `normal-16.6` collision.
const COINCIDENT: SpeedMarker[] = [
  marker("V_stall", 11.0, "stall"),
  marker("V_md", 16.6, "normal"),
  marker("V_cruise", 16.6, "normal"),
  marker("V_ne", 30.0, "ne"),
];

describe("EnvelopeAxis — coincident markers (gh-897)", () => {
  afterEach(() => vi.restoreAllMocks());

  it("emits no React duplicate-key error when two markers share value+kind", () => {
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(<EnvelopeAxis markers={COINCIDENT} />);
    const dupKeyErrors = errSpy.mock.calls.filter((args) =>
      args.some((a) => typeof a === "string" && a.includes("same key")),
    );
    expect(dupKeyErrors).toEqual([]);
  });

  it("renders no zero-width colour zones", () => {
    const { container } = render(<EnvelopeAxis markers={COINCIDENT} />);
    // colour-zone divs carry opacity-25; markers do not
    const zones = Array.from(container.querySelectorAll<HTMLElement>(".opacity-25"));
    expect(zones.length).toBeGreaterThan(0);
    for (const z of zones) {
      expect(z.style.width).not.toBe("0%");
    }
  });
});
