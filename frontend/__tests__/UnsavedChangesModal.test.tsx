import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => ({
  TriangleAlert: (props: Record<string, unknown>) => (
    <svg data-testid="triangle-alert-icon" {...props} />
  ),
}));

const mockUseUnsavedChanges = vi.fn();

vi.mock("@/components/workbench/UnsavedChangesContext", () => ({
  useUnsavedChanges: () => mockUseUnsavedChanges(),
}));

import { UnsavedChangesModal } from "../components/workbench/UnsavedChangesModal";

function defaultCtx(overrides: Record<string, unknown> = {}) {
  return {
    pendingHref: null,
    isSaving: false,
    confirmDiscard: vi.fn(),
    confirmSave: vi.fn(),
    cancelNavigation: vi.fn(),
    ...overrides,
  };
}

describe("UnsavedChangesModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when pendingHref is null", () => {
    mockUseUnsavedChanges.mockReturnValue(defaultCtx());
    const { container } = render(<UnsavedChangesModal />);
    const dialog = container.querySelector("dialog");
    expect(dialog).toBeTruthy();
    expect(dialog?.hasAttribute("open")).toBe(false);
  });

  it("renders when pendingHref is set", () => {
    mockUseUnsavedChanges.mockReturnValue(
      defaultCtx({ pendingHref: "/workbench/analysis" }),
    );
    render(<UnsavedChangesModal />);
    expect(screen.getByText("Unsaved Changes")).toBeDefined();
    expect(
      screen.getByText("You have unsaved changes. Do you want to save before leaving?"),
    ).toBeDefined();
  });

  it("Discard button calls confirmDiscard", () => {
    const ctx = defaultCtx({ pendingHref: "/workbench/analysis" });
    mockUseUnsavedChanges.mockReturnValue(ctx);
    render(<UnsavedChangesModal />);

    fireEvent.click(screen.getByText("Discard"));
    expect(ctx.confirmDiscard).toHaveBeenCalledOnce();
  });

  it("Cancel button calls cancelNavigation", () => {
    const ctx = defaultCtx({ pendingHref: "/workbench/analysis" });
    mockUseUnsavedChanges.mockReturnValue(ctx);
    render(<UnsavedChangesModal />);

    fireEvent.click(screen.getByText("Cancel"));
    expect(ctx.cancelNavigation).toHaveBeenCalledOnce();
  });

  it("Save & Continue button calls confirmSave", () => {
    const ctx = defaultCtx({ pendingHref: "/workbench/analysis" });
    mockUseUnsavedChanges.mockReturnValue(ctx);
    render(<UnsavedChangesModal />);

    fireEvent.click(screen.getByText("Save & Continue"));
    expect(ctx.confirmSave).toHaveBeenCalledOnce();
  });

  it('shows "Saving..." when isSaving is true', () => {
    mockUseUnsavedChanges.mockReturnValue(
      defaultCtx({ pendingHref: "/workbench/analysis", isSaving: true }),
    );
    render(<UnsavedChangesModal />);
    expect(screen.getByText("Saving\u2026")).toBeDefined();
  });
});
