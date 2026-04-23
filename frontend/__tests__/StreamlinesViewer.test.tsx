/**
 * Unit tests for the StreamlinesViewer component.
 *
 * Mocks the useStreamlines hook and plotly.js to test the form UI,
 * button states, and placeholder messages in isolation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

// Mock plotly.js dynamic import - must be before component import
vi.mock("plotly.js-gl3d-dist-min", () => ({
  default: { react: vi.fn(), purge: vi.fn() },
}));

// Mock the hook
const mockComputeStreamlines = vi.fn();
const mockHookReturn = {
  figure: null as Record<string, unknown> | null,
  isComputing: false,
  error: null as string | null,
  computeStreamlines: mockComputeStreamlines,
};

vi.mock("@/hooks/useStreamlines", () => ({
  useStreamlines: () => mockHookReturn,
}));

// Mock lucide-react Loader2 to a simple span
vi.mock("lucide-react", () => ({
  Loader2: (props: Record<string, unknown>) =>
    React.createElement("span", { "data-testid": "loader", ...props }),
}));

// Import AFTER mocks
const { StreamlinesViewer } = await import(
  "../components/workbench/StreamlinesViewer"
);

describe("StreamlinesViewer", () => {
  beforeEach(() => {
    mockHookReturn.figure = null;
    mockHookReturn.isComputing = false;
    mockHookReturn.error = null;
    mockComputeStreamlines.mockClear();
  });

  it("renders four input fields for velocity, alpha, beta, altitude", () => {
    render(<StreamlinesViewer aeroplaneId="aero-1" />);

    const inputs = screen.getAllByRole("spinbutton");
    expect(inputs).toHaveLength(4);

    expect(screen.getByText("Velocity (m/s)")).toBeDefined();
    expect(screen.getByText(/Alpha/)).toBeDefined();
    expect(screen.getByText(/Beta/)).toBeDefined();
    expect(screen.getByText("Altitude (m)")).toBeDefined();
  });

  it("renders a Compute button", () => {
    render(<StreamlinesViewer aeroplaneId="aero-1" />);

    const button = screen.getByRole("button", { name: /Compute/i });
    expect(button).toBeDefined();
    expect(button.textContent).toBe("Compute");
  });

  it("shows placeholder text when no figure, not computing, and no error", () => {
    render(<StreamlinesViewer aeroplaneId="aero-1" />);

    expect(
      screen.getByText("Set parameters and click Compute"),
    ).toBeDefined();
  });

  it("disables the Compute button when aeroplaneId is null", () => {
    render(<StreamlinesViewer aeroplaneId={null} />);

    const button = screen.getByRole("button", { name: /Compute/i });
    expect(button).toHaveProperty("disabled", true);
  });

  it("disables the Compute button while isComputing is true", () => {
    mockHookReturn.isComputing = true;

    render(<StreamlinesViewer aeroplaneId="aero-1" />);

    const button = screen.getByRole("button", { name: /Comput/i });
    expect(button).toHaveProperty("disabled", true);
  });

  it("shows computing state with loader when isComputing is true", () => {
    mockHookReturn.isComputing = true;

    render(<StreamlinesViewer aeroplaneId="aero-1" />);

    expect(screen.getByText(/Computing streamlines/)).toBeDefined();
    // The button text should change
    const button = screen.getByRole("button");
    expect(button.textContent).toContain("Computing");
  });

  it("shows error message when error is set", () => {
    mockHookReturn.error = "Streamlines failed: 500 Internal Server Error";

    render(<StreamlinesViewer aeroplaneId="aero-1" />);

    expect(
      screen.getByText("Streamlines failed: 500 Internal Server Error"),
    ).toBeDefined();
  });

  it("does not show placeholder when error is present", () => {
    mockHookReturn.error = "Something went wrong";

    render(<StreamlinesViewer aeroplaneId="aero-1" />);

    expect(
      screen.queryByText("Set parameters and click Compute"),
    ).toBeNull();
  });

  it("does not show placeholder when figure is present", () => {
    mockHookReturn.figure = { data: [], layout: {} };

    render(<StreamlinesViewer aeroplaneId="aero-1" />);

    expect(
      screen.queryByText("Set parameters and click Compute"),
    ).toBeNull();
  });

  it("renders inputs with correct default values", () => {
    render(<StreamlinesViewer aeroplaneId="aero-1" />);

    const inputs = screen.getAllByRole("spinbutton") as HTMLInputElement[];
    // Default params: velocity=20, alpha=5, beta=0, altitude=0
    const values = inputs.map((i) => Number.parseFloat(i.value));
    expect(values).toEqual([20, 5, 0, 0]);
  });
});
