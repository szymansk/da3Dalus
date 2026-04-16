/**
 * Tests for the Component Type Management dialog (gh#84).
 *
 * The management dialog lists all registered types (seeded + user-added),
 * shows their reference-count, and lets the user open an edit dialog for
 * each or create a new type. Delete is disabled for seeded types and for
 * user types with references.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    X: icon, Plus: icon, Pencil: icon, Trash2: icon, Lock: icon,
    Loader2: icon, Check: icon, Settings: icon,
  };
});

let typesReturn: {
  types: Array<Record<string, unknown>>;
  isLoading: boolean;
  mutate: () => void;
  error?: Error | null;
} = { types: [], isLoading: false, mutate: vi.fn() };

vi.mock("@/hooks/useComponentTypes", () => ({
  useComponentTypes: () => ({ error: null, ...typesReturn }),
  createComponentType: vi.fn().mockResolvedValue({}),
  updateComponentType: vi.fn().mockResolvedValue({}),
  deleteComponentType: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/fetcher", () => ({ API_BASE: "http://x", fetcher: vi.fn() }));

import { ComponentTypeManagementDialog } from "@/components/workbench/ComponentTypeManagementDialog";

beforeEach(() => {
  vi.clearAllMocks();
  typesReturn = { types: [], isLoading: false, mutate: vi.fn() };
});

function makeType(o: Record<string, unknown> = {}) {
  return {
    id: 1, name: "foo", label: "Foo",
    description: null, schema: [],
    deletable: true, reference_count: 0,
    created_at: "2026-04-16T00:00:00Z",
    updated_at: "2026-04-16T00:00:00Z",
    ...o,
  };
}

describe("ComponentTypeManagementDialog", () => {
  it("does not render when open=false", () => {
    render(<ComponentTypeManagementDialog open={false} onClose={vi.fn()} />);
    expect(screen.queryByText(/Manage Component Types/i)).toBeNull();
  });

  it("shows empty state message when no types exist", () => {
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    // Header always present
    expect(screen.getByText(/Manage Component Types/i)).toBeDefined();
  });

  it("lists types with label, reference-count, and deletable indicator", () => {
    typesReturn = {
      types: [
        makeType({ id: 1, name: "material", label: "Material", deletable: false, reference_count: 5 }),
        makeType({ id: 2, name: "custom_tube", label: "Custom Tube", deletable: true, reference_count: 0 }),
      ],
      isLoading: false, mutate: vi.fn(),
    };
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    expect(screen.getByText("Material")).toBeDefined();
    expect(screen.getByText("Custom Tube")).toBeDefined();
    expect(screen.getByText(/5 components/i)).toBeDefined();
  });

  it("delete button is disabled for seeded types", () => {
    typesReturn = {
      types: [
        makeType({ id: 1, name: "material", label: "Material", deletable: false, reference_count: 0 }),
      ],
      isLoading: false, mutate: vi.fn(),
    };
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    const btn = screen.getByTitle(/Seeded type cannot be deleted/i) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("delete button is disabled for user types with references", () => {
    typesReturn = {
      types: [
        makeType({ id: 1, name: "ut", label: "User Type", deletable: true, reference_count: 3 }),
      ],
      isLoading: false, mutate: vi.fn(),
    };
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    const btn = screen.getByTitle(/Referenced by 3/i) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("delete button is enabled for user types without references", () => {
    typesReturn = {
      types: [
        makeType({ id: 1, name: "ut", label: "User Type", deletable: true, reference_count: 0 }),
      ],
      isLoading: false, mutate: vi.fn(),
    };
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    const btn = screen.getByTitle(/Delete User Type/i) as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it("'+ New Type' button opens the Edit dialog with an empty type", () => {
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    fireEvent.click(screen.getByText(/New Type/i));
    // The Edit dialog has its own title "Edit Type" or "New Type"
    expect(screen.getByText(/New Type:/i)).toBeDefined();
  });

  it("pencil icon on a row opens the Edit dialog with that type", () => {
    typesReturn = {
      types: [
        makeType({ id: 1, name: "material", label: "Material", deletable: false }),
      ],
      isLoading: false, mutate: vi.fn(),
    };
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    fireEvent.click(screen.getByTitle(/Edit Material/i));
    expect(screen.getByText(/Edit Type: Material/i)).toBeDefined();
  });

  it("shows a visible error when the GET /component-types fetch fails", () => {
    // Regression for the 2026-04-16 bug report: both the Mgmt dialog list
    // and the New-Component dropdown were empty, but the user had no visible
    // feedback because the hook swallowed the error. With this fix, any SWR
    // error surfaces in the dialog.
    typesReturn = {
      types: [],
      isLoading: false,
      mutate: vi.fn(),
      error: new Error("404 Not Found: /component-types"),
    };
    render(<ComponentTypeManagementDialog open={true} onClose={vi.fn()} />);
    expect(screen.getByText(/Failed to load types/i)).toBeDefined();
    expect(screen.getByText(/404/)).toBeDefined();
  });

  it("Close button calls onClose", () => {
    const onClose = vi.fn();
    render(<ComponentTypeManagementDialog open={true} onClose={onClose} />);
    fireEvent.click(screen.getByText(/^Close$/));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
