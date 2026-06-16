// frontend/__tests__/SparSizingPanel.test.tsx
// gh-1008: Unit tests for the SparSizingPanel component.
// Tests the pure UI logic: collapse/expand, material dropdown (mocked),
// shape-adaptive inputs, feasibility flags, g_limit warning.

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SparSizingPanel } from "@/components/workbench/SparSizingPanel";
import type { SparSizingResult, SparSizingStation } from "@/hooks/useSparSizing";
import type { SparSizingPanelProps } from "@/components/workbench/SparSizingPanel";

// Mock useComponents so tests don't need a real API
vi.mock("@/hooks/useComponents", () => ({
  useComponents: () => ({
    components: [
      {
        id: 1,
        name: "Carbon Fiber (structural)",
        component_type: "material",
        manufacturer: null,
        description: null,
        mass_g: null,
        bbox_x_mm: null,
        bbox_y_mm: null,
        bbox_z_mm: null,
        model_ref: null,
        specs: {
          density_kg_m3: 1600,
          allowable_bending_stress_mpa: 500,
          youngs_modulus_gpa: 120,
        },
        created_at: "2025-01-01T00:00:00",
        updated_at: "2025-01-01T00:00:00",
      },
      {
        id: 2,
        name: "Pine (structural)",
        component_type: "material",
        manufacturer: null,
        description: null,
        mass_g: null,
        bbox_x_mm: null,
        bbox_y_mm: null,
        bbox_z_mm: null,
        model_ref: null,
        specs: {
          density_kg_m3: 500,
          allowable_bending_stress_mpa: 39,
          youngs_modulus_gpa: 11,
        },
        created_at: "2025-01-01T00:00:00",
        updated_at: "2025-01-01T00:00:00",
      },
      {
        id: 3,
        name: "PLA (3D print)",
        component_type: "material",
        manufacturer: null,
        description: null,
        mass_g: null,
        bbox_x_mm: null,
        bbox_y_mm: null,
        bbox_z_mm: null,
        model_ref: null,
        specs: { density_kg_m3: 1240 }, // no σ_allow → should NOT appear
        created_at: "2025-01-01T00:00:00",
        updated_at: "2025-01-01T00:00:00",
      },
    ],
    total: 3,
    error: null,
    isLoading: false,
    mutate: vi.fn(),
  }),
}));

// ---- Fixtures --------------------------------------------------------------

function makeStation(overrides: Partial<SparSizingStation> = {}): SparSizingStation {
  return {
    y_m: 0.0,
    chord_m: 0.4,
    profile_thickness_mm: 48.0,
    outer_mm: 38.4,
    tc_ratio: 0.12,
    tc_fallback: false,
    m_design_Nm: 4500.0,
    required_W_mm3: 9000.0,
    solved_mm: 2.5,
    feasible: true,
    infeasibility_reason: null,
    cross_section_area_mm2: 120.0,
    ...overrides,
  };
}

function makeResult(overrides: Partial<SparSizingResult> = {}): SparSizingResult {
  const st = makeStation();
  return {
    surface_name: "main_wing",
    shape: "tube",
    material_name: "Carbon Fiber (structural)",
    sigma_allow_mpa: 500,
    density_kg_m3: 1600,
    g_limit: 4.0,
    g_limit_fallback: false,
    safety_factor_j: 1.5,
    packing_factor: 0.8,
    stations: [st],
    root_station: st,
    spar_mass_half_kg: 0.045,
    spar_mass_full_kg: 0.09,
    tc_fallback_warning: null,
    ...overrides,
  };
}

function renderPanel(props: Partial<SparSizingPanelProps> = {}) {
  const onCompute = vi.fn();
  render(
    <SparSizingPanel
      sizingResults={null}
      isRunning={false}
      error={null}
      onCompute={onCompute}
      {...props}
    />,
  );
  return { onCompute };
}

// ---- Tests -----------------------------------------------------------------

describe("SparSizingPanel", () => {
  it("renders collapsed by default", () => {
    renderPanel();
    expect(screen.getByText("Spar Sizing")).toBeInTheDocument();
    expect(screen.queryByTestId("spar-material-select")).not.toBeInTheDocument();
  });

  it("expands when header is clicked", async () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => {
      expect(screen.getByTestId("spar-material-select")).toBeInTheDocument();
    });
  });

  it("shows only structural materials (with σ_allow) in dropdown", async () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => {
      expect(screen.getByTestId("spar-material-select")).toBeInTheDocument();
    });
    const select = screen.getByTestId("spar-material-select") as HTMLSelectElement;
    const options = Array.from(select.options).map((o) => o.text);
    expect(options).toContain("Carbon Fiber (structural)");
    expect(options).toContain("Pine (structural)");
    // PLA has no σ_allow → must NOT appear
    expect(options).not.toContain("PLA (3D print)");
  });

  it("auto-fills σ_allow when material is selected", async () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => screen.getByTestId("spar-material-select"));

    const select = screen.getByTestId("spar-material-select");
    fireEvent.change(select, { target: { value: "1" } }); // Carbon Fiber id=1

    const sigmaInput = screen.getByTestId("spar-sigma-input") as HTMLInputElement;
    expect(sigmaInput.value).toBe("500");
  });

  it("shows cap width input only for capped shape", async () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => screen.getByTestId("spar-shape-select"));

    // Default shape=tube → no cap width
    expect(screen.queryByTestId("spar-capwidth-input")).not.toBeInTheDocument();

    // Switch to capped
    fireEvent.change(screen.getByTestId("spar-shape-select"), {
      target: { value: "capped" },
    });
    expect(screen.getByTestId("spar-capwidth-input")).toBeInTheDocument();

    // Switch to rod → cap width disappears
    fireEvent.change(screen.getByTestId("spar-shape-select"), {
      target: { value: "rod" },
    });
    expect(screen.queryByTestId("spar-capwidth-input")).not.toBeInTheDocument();
  });

  it("compute button is disabled when no material selected", async () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => screen.getByTestId("spar-compute-button"));
    const btn = screen.getByTestId("spar-compute-button") as HTMLButtonElement;
    expect(btn).toBeDisabled();
  });

  it("compute button enabled after material selected", async () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => screen.getByTestId("spar-material-select"));
    fireEvent.change(screen.getByTestId("spar-material-select"), { target: { value: "1" } });
    const btn = screen.getByTestId("spar-compute-button") as HTMLButtonElement;
    expect(btn).not.toBeDisabled();
  });

  it("calls onCompute with inputs when button clicked", async () => {
    const { onCompute } = renderPanel();
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => screen.getByTestId("spar-material-select"));
    fireEvent.change(screen.getByTestId("spar-material-select"), { target: { value: "2" } }); // Pine
    fireEvent.click(screen.getByTestId("spar-compute-button"));
    expect(onCompute).toHaveBeenCalledOnce();
    const [inputs] = onCompute.mock.calls[0];
    expect(inputs.materialId).toBe(2);
    expect(inputs.shape).toBe("tube");
  });

  it("shows error when error prop is set", async () => {
    renderPanel({ error: "Material not found" });
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => screen.getByTestId("spar-error"));
    expect(screen.getByTestId("spar-error")).toHaveTextContent("Material not found");
  });

  it("shows results when sizingResults provided", async () => {
    const result = makeResult();
    renderPanel({ sizingResults: [result] });
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => screen.getByTestId("spar-results"));
    expect(screen.getByTestId("spar-results")).toBeInTheDocument();
    // Should contain surface name
    expect(screen.getByText("main_wing")).toBeInTheDocument();
  });

  it("shows g_limit fallback warning", async () => {
    const result = makeResult({ g_limit: 3.0, g_limit_fallback: true });
    renderPanel({ sizingResults: [result] });
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => screen.getByTestId("g-limit-fallback-warning"));
    expect(screen.getByTestId("g-limit-fallback-warning")).toBeInTheDocument();
    expect(screen.getByTestId("g-limit-fallback-warning")).toHaveTextContent("default");
  });

  it("shows tc fallback warning", async () => {
    const result = makeResult({
      tc_fallback_warning: "t/c=0.12 fallback applied at y=1.50 m",
    });
    renderPanel({ sizingResults: [result] });
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => screen.getByTestId("tc-fallback-warning"));
    expect(screen.getByTestId("tc-fallback-warning")).toHaveTextContent("1.50");
  });

  it("displays 'Computing…' when isRunning", async () => {
    renderPanel({ isRunning: true });
    fireEvent.click(screen.getByTestId("spar-sizing-toggle"));
    await waitFor(() => screen.getByTestId("spar-compute-button"));
    expect(screen.getByTestId("spar-compute-button")).toHaveTextContent("Computing…");
  });
});
