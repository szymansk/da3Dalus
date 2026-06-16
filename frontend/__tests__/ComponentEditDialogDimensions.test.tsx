/**
 * Tests for ESC dimensions (bbox L/W/H) and boolean spec fields
 * in ComponentEditDialog (gh-1009).
 *
 * Spec: The dialog must surface bbox_x_mm / bbox_y_mm / bbox_z_mm as
 * editable Length / Width / Height (mm) inputs, and render boolean spec
 * fields (e.g. ESC BEC voltage toggles) as checkboxes.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    X: icon,
    Loader2: icon,
    ChevronDown: icon,
    ChevronRight: icon,
  };
});

const mockCreate = vi.fn().mockResolvedValue({});
const mockUpdate = vi.fn().mockResolvedValue({});

vi.mock("@/hooks/useComponents", () => ({
  createComponent: (...a: unknown[]) => mockCreate(...a),
  updateComponent: (...a: unknown[]) => mockUpdate(...a),
}));

/** ESC type schema with boolean BEC voltage fields (matches gh-1009 canonical schema). */
vi.mock("@/hooks/useComponentTypes", () => ({
  useComponentTypes: () => ({
    types: [
      {
        id: 1,
        name: "generic",
        label: "Generic",
        description: null,
        schema: [],
        deletable: false,
        reference_count: 0,
        created_at: "",
        updated_at: "",
      },
      {
        id: 2,
        name: "esc",
        label: "ESC",
        description: null,
        schema: [
          {
            name: "continuous_current_a",
            label: "Continuous Current",
            type: "number",
            unit: "A",
            required: true,
          },
          {
            name: "bec_voltage_5v",
            label: "BEC 5.0 V",
            type: "boolean",
            required: false,
          },
          {
            name: "bec_voltage_6v",
            label: "BEC 6.0 V",
            type: "boolean",
            required: false,
          },
          {
            name: "bec_current_a",
            label: "BEC Current",
            type: "number",
            unit: "A",
            required: false,
          },
        ],
        deletable: false,
        reference_count: 0,
        created_at: "",
        updated_at: "",
      },
    ],
    isLoading: false,
    mutate: vi.fn(),
    error: null,
  }),
}));

import { ComponentEditDialog } from "@/components/workbench/ComponentEditDialog";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ComponentEditDialog — bbox dimensions (gh-1009)", () => {
  it("renders Length input bound to bbox_x_mm", () => {
    const { container } = render(
      <ComponentEditDialog
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        component={null}
      />,
    );
    const lengthInput = container.querySelector(
      'input[data-bbox="bbox_x_mm"]',
    ) as HTMLInputElement | null;
    expect(
      lengthInput,
      "Expected an input with data-bbox='bbox_x_mm' for the Length field",
    ).not.toBeNull();
  });

  it("renders Width input bound to bbox_y_mm", () => {
    const { container } = render(
      <ComponentEditDialog
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        component={null}
      />,
    );
    const widthInput = container.querySelector(
      'input[data-bbox="bbox_y_mm"]',
    ) as HTMLInputElement | null;
    expect(
      widthInput,
      "Expected an input with data-bbox='bbox_y_mm' for the Width field",
    ).not.toBeNull();
  });

  it("renders Height input bound to bbox_z_mm", () => {
    const { container } = render(
      <ComponentEditDialog
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        component={null}
      />,
    );
    const heightInput = container.querySelector(
      'input[data-bbox="bbox_z_mm"]',
    ) as HTMLInputElement | null;
    expect(
      heightInput,
      "Expected an input with data-bbox='bbox_z_mm' for the Height field",
    ).not.toBeNull();
  });

  it("shows labels Length, Width, Height (mm) for the dimension inputs", () => {
    render(
      <ComponentEditDialog
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        component={null}
      />,
    );
    expect(screen.getByText(/Length/)).toBeDefined();
    expect(screen.getByText(/Width/)).toBeDefined();
    expect(screen.getByText(/Height/)).toBeDefined();
  });

  it("pre-populates dimension inputs from existing component bbox values", () => {
    const { container } = render(
      <ComponentEditDialog
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        component={{
          id: 42,
          name: "AVICON 20A",
          component_type: "esc",
          manufacturer: "AVICON",
          description: null,
          mass_g: 15,
          bbox_x_mm: 60,
          bbox_y_mm: 25,
          bbox_z_mm: 10,
          model_ref: null,
          specs: {},
          created_at: "",
          updated_at: "",
        }}
      />,
    );
    const l = container.querySelector(
      'input[data-bbox="bbox_x_mm"]',
    ) as HTMLInputElement;
    const w = container.querySelector(
      'input[data-bbox="bbox_y_mm"]',
    ) as HTMLInputElement;
    const h = container.querySelector(
      'input[data-bbox="bbox_z_mm"]',
    ) as HTMLInputElement;
    expect(l?.value).toBe("60");
    expect(w?.value).toBe("25");
    expect(h?.value).toBe("10");
  });

  it("sends bbox values in the save payload", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ComponentEditDialog
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        component={null}
      />,
    );
    // Fill name
    const nameInput = screen.getAllByRole("textbox")[0] as HTMLInputElement;
    await user.clear(nameInput);
    await user.type(nameInput, "My ESC");

    // Fill dimension inputs
    const l = container.querySelector(
      'input[data-bbox="bbox_x_mm"]',
    ) as HTMLInputElement;
    const w = container.querySelector(
      'input[data-bbox="bbox_y_mm"]',
    ) as HTMLInputElement;
    const h = container.querySelector(
      'input[data-bbox="bbox_z_mm"]',
    ) as HTMLInputElement;
    await user.clear(l);
    await user.type(l, "60");
    await user.clear(w);
    await user.type(w, "25");
    await user.clear(h);
    await user.type(h, "10");

    await user.click(screen.getByText(/^Create$/));
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        bbox_x_mm: 60,
        bbox_y_mm: 25,
        bbox_z_mm: 10,
      }),
    );
  });
});

describe("ComponentEditDialog — ESC boolean spec fields (gh-1009)", () => {
  it("renders boolean spec fields as checkboxes", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ComponentEditDialog
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        component={null}
      />,
    );
    // Switch to ESC type
    const select = screen.getAllByRole("combobox")[0] as HTMLSelectElement;
    await user.selectOptions(select, "esc");

    const bec5vCheckbox = container.querySelector(
      'input[type="checkbox"][data-spec="bec_voltage_5v"]',
    ) as HTMLInputElement | null;
    expect(
      bec5vCheckbox,
      "Expected a checkbox for bec_voltage_5v",
    ).not.toBeNull();
  });

  it("renders BEC 5.0 V and BEC 6.0 V labels for boolean fields", async () => {
    const user = userEvent.setup();
    render(
      <ComponentEditDialog
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        component={null}
      />,
    );
    const select = screen.getAllByRole("combobox")[0] as HTMLSelectElement;
    await user.selectOptions(select, "esc");

    expect(screen.getByText(/BEC 5\.0 V/i)).toBeDefined();
    expect(screen.getByText(/BEC 6\.0 V/i)).toBeDefined();
  });

  it("boolean spec field can be toggled", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ComponentEditDialog
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        component={null}
      />,
    );
    const select = screen.getAllByRole("combobox")[0] as HTMLSelectElement;
    await user.selectOptions(select, "esc");

    const checkbox = container.querySelector(
      'input[type="checkbox"][data-spec="bec_voltage_5v"]',
    ) as HTMLInputElement;
    expect(checkbox.checked).toBe(false); // starts unchecked (default false)

    await user.click(checkbox);
    expect(checkbox.checked).toBe(true);
  });

  it("sends boolean spec values as booleans (not strings) in save payload", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ComponentEditDialog
        open={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        component={null}
      />,
    );
    // Fill name
    const nameInput = screen.getAllByRole("textbox")[0] as HTMLInputElement;
    await user.clear(nameInput);
    await user.type(nameInput, "AVICON 20A");

    // Switch to ESC type
    const select = screen.getAllByRole("combobox")[0] as HTMLSelectElement;
    await user.selectOptions(select, "esc");

    // Fill required continuous_current_a
    const currentInput = container.querySelector(
      'input[data-spec="continuous_current_a"]',
    ) as HTMLInputElement;
    await user.clear(currentInput);
    await user.type(currentInput, "20");

    // Toggle bec_voltage_5v on
    const bec5v = container.querySelector(
      'input[type="checkbox"][data-spec="bec_voltage_5v"]',
    ) as HTMLInputElement;
    await user.click(bec5v);

    await user.click(screen.getByText(/^Create$/));
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        specs: expect.objectContaining({
          bec_voltage_5v: true,
          continuous_current_a: 20,
        }),
      }),
    );
  });
});
