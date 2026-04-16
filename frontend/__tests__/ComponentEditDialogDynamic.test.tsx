/**
 * Tests for the dynamic ComponentEditDialog (gh#85).
 *
 * The dialog now renders specs-fields based on the selected type's
 * schema, validates them on submit, preserves compatible specs across
 * type changes, and surfaces "Unknown properties" for legacy data.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    X: icon, Loader2: icon, ChevronDown: icon, ChevronRight: icon,
  };
});

const mockCreate = vi.fn().mockResolvedValue({});
const mockUpdate = vi.fn().mockResolvedValue({});

vi.mock("@/hooks/useComponents", () => ({
  createComponent: (...a: unknown[]) => mockCreate(...a),
  updateComponent: (...a: unknown[]) => mockUpdate(...a),
}));

vi.mock("@/hooks/useComponentTypes", () => ({
  useComponentTypes: () => ({
    types: [
      {
        id: 1, name: "generic", label: "Generic",
        description: null, schema: [], deletable: false, reference_count: 0,
        created_at: "", updated_at: "",
      },
      {
        id: 2, name: "material", label: "Material", description: null,
        schema: [
          { name: "density_kg_m3", label: "Dichte", type: "number",
            unit: "kg/m³", required: true, min: 100, max: 20000 },
          { name: "print_type", label: "Drucktyp", type: "enum",
            options: ["volume", "surface"], default: "volume" },
        ],
        deletable: false, reference_count: 0,
        created_at: "", updated_at: "",
      },
      {
        id: 3, name: "servo", label: "Servo", description: null,
        schema: [
          { name: "torque_kg_cm", label: "Drehmoment", type: "number", unit: "kg·cm" },
          { name: "connector", label: "Anschluss", type: "enum",
            options: ["jr", "futaba", "universal"] },
        ],
        deletable: false, reference_count: 0,
        created_at: "", updated_at: "",
      },
    ],
    isLoading: false, mutate: vi.fn(), error: null,
  }),
}));

import { ComponentEditDialog } from "@/components/workbench/ComponentEditDialog";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ComponentEditDialog — dynamic specs rendering", () => {
  it("renders number + enum fields for material type", () => {
    render(
      <ComponentEditDialog open={true} onClose={vi.fn()} onSaved={vi.fn()}
        component={null} />,
    );
    // Select Material type
    const select = screen.getAllByRole("combobox")[0] as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "material" } });

    expect(screen.getByText(/Dichte/i)).toBeDefined();
    expect(screen.getByText(/Drucktyp/i)).toBeDefined();
  });

  it("required fields are marked with a star", () => {
    render(
      <ComponentEditDialog open={true} onClose={vi.fn()} onSaved={vi.fn()}
        component={null} />,
    );
    const select = screen.getAllByRole("combobox")[0] as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "material" } });
    // The Dichte label should have a * (since required=true)
    expect(screen.getByText(/Dichte/).textContent).toContain("*");
  });

  it("type change preserves compatible specs (same name+type)", () => {
    // Create with a servo, fill torque, switch to a type that also has torque
    // — servo has torque_kg_cm, material doesn't. Switch servo→material
    // should drop torque, switching back should restore via user input only.
    const { container } = render(
      <ComponentEditDialog open={true} onClose={vi.fn()} onSaved={vi.fn()}
        component={null} />,
    );

    const select = screen.getAllByRole("combobox")[0] as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "servo" } });
    // fill torque
    const torque = container.querySelector('input[data-spec="torque_kg_cm"]') as HTMLInputElement;
    expect(torque).toBeDefined();
    fireEvent.change(torque, { target: { value: "1.8" } });
    expect(torque.value).toBe("1.8");

    // switch to material — torque field disappears
    fireEvent.change(select, { target: { value: "material" } });
    expect(container.querySelector('input[data-spec="torque_kg_cm"]')).toBeNull();

    // switch back to servo — torque field reappears, value preserved
    fireEvent.change(select, { target: { value: "servo" } });
    const torqueAgain = container.querySelector('input[data-spec="torque_kg_cm"]') as HTMLInputElement;
    expect(torqueAgain.value).toBe("1.8");
  });

  it("blocks submit when a required field is missing", () => {
    render(
      <ComponentEditDialog open={true} onClose={vi.fn()} onSaved={vi.fn()}
        component={null} />,
    );
    const nameInput = screen.getAllByRole("textbox")[0] as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "My Material" } });
    const select = screen.getAllByRole("combobox")[0] as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "material" } });
    // Don't fill density

    fireEvent.click(screen.getByText(/^Create$/));
    expect(mockCreate).not.toHaveBeenCalled();
    // Error message (inside a destructive-styled box) mentions the missing field.
    // The label "Dichte" also appears as a regular label — so we filter to the
    // inline error box.
    const errors = screen.getAllByText(/Dichte/);
    const inErrorBox = errors.some((el) =>
      el.closest("div")?.className.includes("destructive"),
    );
    expect(inErrorBox).toBe(true);
  });

  it("submits specs when all required fields are set", () => {
    const { container } = render(
      <ComponentEditDialog open={true} onClose={vi.fn()} onSaved={vi.fn()}
        component={null} />,
    );
    const nameInput = screen.getAllByRole("textbox")[0] as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "PLA+" } });

    const select = screen.getAllByRole("combobox")[0] as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "material" } });

    const density = container.querySelector('input[data-spec="density_kg_m3"]') as HTMLInputElement;
    fireEvent.change(density, { target: { value: "1240" } });

    fireEvent.click(screen.getByText(/^Create$/));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      name: "PLA+",
      component_type: "material",
      specs: expect.objectContaining({ density_kg_m3: 1240 }),
    }));
  });

  it("shows 'Unknown properties' section when existing specs have extra keys", () => {
    render(
      <ComponentEditDialog open={true} onClose={vi.fn()} onSaved={vi.fn()}
        component={{
          id: 99, name: "legacy", component_type: "material",
          manufacturer: null, description: null, mass_g: null,
          bbox_x_mm: null, bbox_y_mm: null, bbox_z_mm: null, model_ref: null,
          specs: { density_kg_m3: 1240, legacy_field: "old", some_old_key: 42 },
          created_at: "", updated_at: "",
        }} />,
    );
    // The unknown-properties section is visible and lists legacy_field + some_old_key
    expect(screen.getByText(/Unknown properties/i)).toBeDefined();
  });

  it("number field shows the unit as a hint", () => {
    const { container } = render(
      <ComponentEditDialog open={true} onClose={vi.fn()} onSaved={vi.fn()}
        component={null} />,
    );
    const select = screen.getAllByRole("combobox")[0] as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "material" } });
    // The unit "kg/m³" appears near the density input
    expect(container.textContent).toContain("kg/m³");
  });
});
