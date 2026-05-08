/**
 * Unit tests for the TedEditDialog role dropdown (gh-439).
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// ── Mocks ─────────────────────────────────────────────────────────

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    X: icon,
    Check: icon,
    ChevronDown: icon,
    ChevronUp: icon,
    Search: icon,
    ChevronRight: icon,
  };
});

vi.mock("@/lib/fetcher", () => ({
  API_BASE: "http://localhost:8001/v2",
}));

vi.mock("@/hooks/useComponents", () => ({
  useComponents: () => ({ components: [] }),
}));

vi.mock("@/hooks/useDialog", () => ({
  useDialog: (open: boolean, onClose: () => void) => ({
    dialogRef: { current: null },
    handleClose: onClose,
  }),
}));

import { TedEditDialog } from "@/components/workbench/TedEditDialog";

// ── Tests ─────────────────────────────────────────────────────────

describe("TedEditDialog role dropdown", () => {
  const defaultProps = {
    open: true,
    onClose: vi.fn(),
    aeroplaneId: "1",
    wingName: "Main Wing",
    xsecIndex: 0,
    isNew: true,
    initialData: undefined,
    onSaved: vi.fn(),
  };

  it("renders role dropdown with all 8 options", () => {
    render(<TedEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    expect(select).toBeTruthy();
    expect(select.options.length).toBe(8);
  });

  it("defaults role to 'other' for new TED", () => {
    render(<TedEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    expect(select.value).toBe("other");
  });

  it("renders optional label input", () => {
    render(<TedEditDialog {...defaultProps} />);
    expect(screen.getByPlaceholderText("e.g. Left Aileron")).toBeTruthy();
  });

  it("pre-fills role from initialData", () => {
    render(
      <TedEditDialog
        {...defaultProps}
        isNew={false}
        initialData={{ role: "elevator", label: "Main Elevator" }}
      />
    );
    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    expect(select.value).toBe("elevator");
  });

  it("pre-fills label from initialData", () => {
    render(
      <TedEditDialog
        {...defaultProps}
        isNew={false}
        initialData={{ role: "aileron", label: "Left Aileron" }}
      />
    );
    const labelInput = screen.getByPlaceholderText("e.g. Left Aileron") as HTMLInputElement;
    expect(labelInput.value).toBe("Left Aileron");
  });

  it("allows changing role via dropdown", async () => {
    const user = userEvent.setup();
    render(<TedEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    await user.selectOptions(select, "elevator");
    expect(select.value).toBe("elevator");
  });

  it("renders all expected role option values", () => {
    render(<TedEditDialog {...defaultProps} />);
    const select = screen.getByLabelText("Role") as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toContain("elevator");
    expect(values).toContain("aileron");
    expect(values).toContain("rudder");
    expect(values).toContain("elevon");
    expect(values).toContain("stabilator");
    expect(values).toContain("flap");
    expect(values).toContain("spoiler");
    expect(values).toContain("other");
  });
});
