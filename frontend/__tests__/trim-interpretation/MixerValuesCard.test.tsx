import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MixerValuesCard } from "@/components/workbench/trim-interpretation/MixerValuesCard";
import type { TrimEnrichment } from "@/hooks/useOperatingPoints";

const MOCK_ENRICHMENT: TrimEnrichment = {
  analysis_goal: "Test",
  result_summary: "",
  trim_method: "opti",
  trim_score: null,
  trim_residuals: {},
  deflection_reserves: {},
  design_warnings: [],
  effectiveness: {},
  stability_classification: null,
  mixer_values: {
    elevon: {
      symmetric_offset: 3.2,
      differential_throw: 5.1,
      role: "elevon",
    },
    flaperon: {
      symmetric_offset: -1.5,
      differential_throw: 8.0,
      role: "flaperon",
    },
  },
  aero_coefficients: {},
};

describe("MixerValuesCard", () => {
  it("renders mixer heading", () => {
    render(<MixerValuesCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("Mixer Setup")).toBeTruthy();
  });

  it("renders symmetric offset for each mixer group", () => {
    render(<MixerValuesCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("3.2°")).toBeTruthy();
    expect(screen.getByText("-1.5°")).toBeTruthy();
  });

  it("renders differential throw for each mixer group", () => {
    render(<MixerValuesCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("5.1°")).toBeTruthy();
    expect(screen.getByText("8.0°")).toBeTruthy();
  });

  it("renders role labels", () => {
    render(<MixerValuesCard enrichment={MOCK_ENRICHMENT} />);
    expect(screen.getByText("Elevon")).toBeTruthy();
    expect(screen.getByText("Flaperon")).toBeTruthy();
  });

  it("renders nothing when no mixer values", () => {
    const empty = { ...MOCK_ENRICHMENT, mixer_values: {} };
    const { container } = render(<MixerValuesCard enrichment={empty} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when enrichment is null", () => {
    const { container } = render(<MixerValuesCard enrichment={null} />);
    expect(container.firstChild).toBeNull();
  });
});
