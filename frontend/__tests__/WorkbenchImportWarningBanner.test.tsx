/**
 * Unit tests for WorkbenchImportWarningBanner (gh-695).
 *
 * The wrapper is a thin context consumer: it must hide the banner
 * when (a) no recent import, (b) the selected aeroplane doesn't
 * match the import-warning uuid, or (c) the warnings list is empty.
 * Otherwise it forwards the warnings to ImportWarningBanner.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WorkbenchImportWarningBanner } from "@/components/workbench/WorkbenchImportWarningBanner";

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: vi.fn(),
}));

import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";

const useCtx = useAeroplaneContext as unknown as ReturnType<typeof vi.fn>;

const warnings = [
  {
    component_type: "PROP",
    component_name: "MainProp",
    reason: "Propellers not yet supported",
    severity: "warning" as const,
  },
];

describe("WorkbenchImportWarningBanner", () => {
  it("renders nothing when no import warnings are in context", () => {
    useCtx.mockReturnValue({ lastImportWarnings: null, aeroplaneId: "uuid-1" });
    const { container } = render(<WorkbenchImportWarningBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when warnings belong to a different aeroplane", () => {
    useCtx.mockReturnValue({
      lastImportWarnings: { uuid: "uuid-imported", warnings },
      aeroplaneId: "uuid-other",
    });
    const { container } = render(<WorkbenchImportWarningBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when warnings list is empty", () => {
    useCtx.mockReturnValue({
      lastImportWarnings: { uuid: "uuid-1", warnings: [] },
      aeroplaneId: "uuid-1",
    });
    const { container } = render(<WorkbenchImportWarningBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("renders ImportWarningBanner when active aeroplane matches and warnings exist", () => {
    useCtx.mockReturnValue({
      lastImportWarnings: { uuid: "uuid-1", warnings },
      aeroplaneId: "uuid-1",
    });
    render(<WorkbenchImportWarningBanner />);
    expect(
      screen.getByText(/were not fully imported|propellers not yet supported/i),
    ).toBeInTheDocument();
  });
});
