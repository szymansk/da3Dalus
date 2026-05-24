/**
 * Unit tests for ImportScaleInputs (gh-695, Variante A).
 *
 * Covers the three-mode radio group and the numeric inputs that
 * surface only for their respective mode. Validates the discriminated-
 * union shape passed to onChange so the parent (AeroplanePickerHost)
 * can encode it correctly into the import endpoint query params.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ImportScaleInputs } from "@/components/workbench/ImportScaleInputs";
import type { ScaleOption } from "@/components/workbench/ImportOpenVspButton";

const noneOpt: ScaleOption = { mode: "none" };
const spanOpt: ScaleOption = { mode: "target_span", target_span_m: 1.5 };
const factorOpt: ScaleOption = { mode: "scale_factor", scale_factor: 0.05 };

describe("ImportScaleInputs", () => {
  it("renders three radio options with the legend", () => {
    render(<ImportScaleInputs value={noneOpt} onChange={vi.fn()} />);
    expect(screen.getByText(/optional: scale on import/i)).toBeInTheDocument();
    expect(screen.getByTestId("scale-mode-none")).toBeInTheDocument();
    expect(screen.getByTestId("scale-mode-target-span")).toBeInTheDocument();
    expect(screen.getByTestId("scale-mode-scale-factor")).toBeInTheDocument();
  });

  it("checks the 'none' radio when value.mode === 'none'", () => {
    render(<ImportScaleInputs value={noneOpt} onChange={vi.fn()} />);
    expect(screen.getByTestId("scale-mode-none")).toBeChecked();
    expect(screen.getByTestId("scale-mode-target-span")).not.toBeChecked();
    expect(screen.getByTestId("scale-mode-scale-factor")).not.toBeChecked();
  });

  it("checks the 'target_span' radio + shows its value", () => {
    render(<ImportScaleInputs value={spanOpt} onChange={vi.fn()} />);
    expect(screen.getByTestId("scale-mode-target-span")).toBeChecked();
    expect(screen.getByTestId("scale-target-span-input")).toHaveValue(1.5);
  });

  it("checks the 'scale_factor' radio + shows its value", () => {
    render(<ImportScaleInputs value={factorOpt} onChange={vi.fn()} />);
    expect(screen.getByTestId("scale-mode-scale-factor")).toBeChecked();
    expect(screen.getByTestId("scale-factor-input")).toHaveValue(0.05);
  });

  it("emits { mode: 'none' } when 'none' radio is clicked from another mode", () => {
    const onChange = vi.fn();
    render(<ImportScaleInputs value={spanOpt} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("scale-mode-none"));
    expect(onChange).toHaveBeenCalledWith({ mode: "none" });
  });

  it("seeds target_span_m to 1.5 when switching from 'none' to target_span", () => {
    const onChange = vi.fn();
    render(<ImportScaleInputs value={noneOpt} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("scale-mode-target-span"));
    expect(onChange).toHaveBeenCalledWith({
      mode: "target_span",
      target_span_m: 1.5,
    });
  });

  it("seeds scale_factor to 1 when switching from 'none' to scale_factor", () => {
    const onChange = vi.fn();
    render(<ImportScaleInputs value={noneOpt} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("scale-mode-scale-factor"));
    expect(onChange).toHaveBeenCalledWith({
      mode: "scale_factor",
      scale_factor: 1,
    });
  });

  it("emits new target_span_m on numeric input change", () => {
    const onChange = vi.fn();
    render(<ImportScaleInputs value={spanOpt} onChange={onChange} />);
    fireEvent.change(screen.getByTestId("scale-target-span-input"), {
      target: { value: "2.4" },
    });
    expect(onChange).toHaveBeenCalledWith({
      mode: "target_span",
      target_span_m: 2.4,
    });
  });

  it("emits new scale_factor on numeric input change", () => {
    const onChange = vi.fn();
    render(<ImportScaleInputs value={factorOpt} onChange={onChange} />);
    fireEvent.change(screen.getByTestId("scale-factor-input"), {
      target: { value: "0.12" },
    });
    expect(onChange).toHaveBeenCalledWith({
      mode: "scale_factor",
      scale_factor: 0.12,
    });
  });

  it("ignores non-numeric input on target_span field", () => {
    const onChange = vi.fn();
    render(<ImportScaleInputs value={spanOpt} onChange={onChange} />);
    fireEvent.change(screen.getByTestId("scale-target-span-input"), {
      target: { value: "abc" },
    });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("ignores non-numeric input on scale_factor field", () => {
    const onChange = vi.fn();
    render(<ImportScaleInputs value={factorOpt} onChange={onChange} />);
    fireEvent.change(screen.getByTestId("scale-factor-input"), {
      target: { value: "xyz" },
    });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("disables target_span input when mode is not target_span", () => {
    render(<ImportScaleInputs value={noneOpt} onChange={vi.fn()} />);
    expect(screen.getByTestId("scale-target-span-input")).toBeDisabled();
  });

  it("disables scale_factor input when mode is not scale_factor", () => {
    render(<ImportScaleInputs value={noneOpt} onChange={vi.fn()} />);
    expect(screen.getByTestId("scale-factor-input")).toBeDisabled();
  });

  it("disables the entire fieldset when disabled prop is true", () => {
    render(
      <ImportScaleInputs value={noneOpt} onChange={vi.fn()} disabled={true} />,
    );
    const fieldset = screen.getByTestId("import-scale-inputs") as HTMLFieldSetElement;
    expect(fieldset).toBeDisabled();
  });

  it("warns about masses not being scaled", () => {
    render(<ImportScaleInputs value={noneOpt} onChange={vi.fn()} />);
    expect(screen.getByText(/masses are not scaled/i)).toBeInTheDocument();
  });
});
