/**
 * Tests for the PropertyEditDialog (gh#84).
 *
 * The property dialog edits a single PropertyDefinition (name, label, type,
 * and type-specific fields). It does NOT talk to the API — its job is to
 * return the edited property to the parent via onSave.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { X: icon, Check: icon };
});

import { PropertyEditDialog } from "@/components/workbench/PropertyEditDialog";
import type { PropertyDefinition } from "@/hooks/useComponentTypes";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PropertyEditDialog", () => {
  it("does not render when open=false", () => {
    render(
      <PropertyEditDialog
        open={false}
        initial={null}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.queryByText(/Property/i)).toBeNull();
  });

  it("renders blank form for new property (initial=null)", () => {
    const { container } = render(
      <PropertyEditDialog
        open={true}
        initial={null}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText(/Name \(snake_case\)/i)).toBeDefined();
    expect(screen.getByText(/^Label/i)).toBeDefined();
    expect(screen.getByText(/^Type/i)).toBeDefined();
    // Name input empty
    const nameInput = container.querySelector('input[type="text"]') as HTMLInputElement;
    expect(nameInput.value).toBe("");
  });

  it("pre-fills form when initial is provided", () => {
    const initial: PropertyDefinition = {
      name: "density_kg_m3",
      label: "Dichte",
      type: "number",
      unit: "kg/m³",
      required: true,
      min: 100,
      max: 20000,
    };
    const { container } = render(
      <PropertyEditDialog
        open={true}
        initial={initial}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    const inputs = container.querySelectorAll("input") as NodeListOf<HTMLInputElement>;
    const byPlaceholder = Array.from(inputs).map((i) => i.value);
    expect(byPlaceholder).toContain("density_kg_m3");
    expect(byPlaceholder).toContain("Dichte");
    expect(byPlaceholder).toContain("kg/m³");
  });

  it("shows min/max fields only for number type", () => {
    render(
      <PropertyEditDialog
        open={true}
        initial={{ name: "x", label: "X", type: "number" }}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText(/^Min/i)).toBeDefined();
    expect(screen.getByText(/^Max/i)).toBeDefined();
  });

  it("shows options field only for enum type", () => {
    render(
      <PropertyEditDialog
        open={true}
        initial={{ name: "x", label: "X", type: "enum", options: ["a", "b"] }}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText(/Options \(comma-separated\)/i)).toBeDefined();
    expect(screen.queryByText(/^Min/i)).toBeNull();
  });

  it("rejects non-snake_case names with an inline error", () => {
    const onSave = vi.fn();
    const { container } = render(
      <PropertyEditDialog
        open={true}
        initial={null}
        onSave={onSave}
        onCancel={vi.fn()}
      />,
    );
    const nameInput = container.querySelector('input[type="text"]') as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "BadName" } });
    fireEvent.click(screen.getByText(/^Apply$/i));
    expect(onSave).not.toHaveBeenCalled();
    // Error message appears (we know the text mentions snake_case — we
    // assert by getAllByText since the label "Name (snake_case) *" also
    // matches, and both being present is our "2 elements" expectation).
    expect(screen.getAllByText(/snake_case/i).length).toBeGreaterThanOrEqual(2);
  });

  it("Apply calls onSave with the edited property", () => {
    const onSave = vi.fn();
    const { container } = render(
      <PropertyEditDialog
        open={true}
        initial={null}
        onSave={onSave}
        onCancel={vi.fn()}
      />,
    );
    const inputs = container.querySelectorAll('input[type="text"]') as NodeListOf<HTMLInputElement>;
    fireEvent.change(inputs[0], { target: { value: "torque_kg_cm" } });
    fireEvent.change(inputs[1], { target: { value: "Drehmoment" } });

    fireEvent.click(screen.getByText(/^Apply$/));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "torque_kg_cm",
        label: "Drehmoment",
        type: "number",  // default
      }),
    );
  });

  it("Min/Max/Default row allows its inputs to shrink below intrinsic width", () => {
    // Regression test: <input type="number"> has an intrinsic min-width that,
    // without `min-w-0` on the flex items and `w-full` on the inputs, causes
    // the third input (Default, with a multi-digit value) to overflow the
    // modal. Captured visually on 2026-04-16 with a 4-digit default.
    const { container } = render(
      <PropertyEditDialog
        open={true}
        initial={{ name: "x", label: "X", type: "number", min: 1, max: 3000, default: 1000 }}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    // Each of the three number inputs must be in a wrapper that CAN shrink
    // (min-w-0 present), and the input itself carries w-full so the wrapper
    // drives its width.
    const numberInputs = container.querySelectorAll<HTMLInputElement>(
      'input[type="number"]',
    );
    expect(numberInputs.length).toBe(3);
    for (const input of Array.from(numberInputs)) {
      const wrapper = input.closest("div") as HTMLElement;
      expect(wrapper.className).toMatch(/min-w-0/);
      expect(input.className).toMatch(/w-full/);
    }
  });

  it("Cancel calls onCancel without onSave", () => {
    const onSave = vi.fn();
    const onCancel = vi.fn();
    render(
      <PropertyEditDialog
        open={true}
        initial={null}
        onSave={onSave}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByText(/^Cancel$/));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSave).not.toHaveBeenCalled();
  });
});
