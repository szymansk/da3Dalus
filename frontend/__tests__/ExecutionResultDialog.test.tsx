/**
 * Unit tests for ExecutionResultDialog Generated-files section (gh#339).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// Mock three-cad-viewer so the dialog body's CadViewer renders without
// pulling in WebGL/three modules in jsdom.
vi.mock("three-cad-viewer", () => ({
  Display: class {
    constructor() {}
    dispose() {}
  },
  Viewer: class {
    constructor() {}
    render() {}
    dispose() {}
    resize() {}
  },
}));

// Mock useArtifactFiles so the dialog can render without a real backend.
vi.mock("@/hooks/useConstructionPlans", async () => {
  const actual = await vi.importActual<
    typeof import("@/hooks/useConstructionPlans")
  >("@/hooks/useConstructionPlans");
  return {
    ...actual,
    useArtifactFiles: vi.fn(),
  };
});

import { useArtifactFiles } from "@/hooks/useConstructionPlans";
import { ExecutionResultDialog } from "@/components/workbench/construction-plans/ExecutionResultDialog";

describe("ExecutionResultDialog — Generated files section", () => {
  beforeEach(() => {
    vi.mocked(useArtifactFiles).mockReset();
    // jsdom does not implement HTMLDialogElement APIs by default
    if (
      !(HTMLDialogElement.prototype as unknown as { showModal?: () => void })
        .showModal
    ) {
      Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
        configurable: true,
        value: function () {
          this.open = true;
        },
      });
      Object.defineProperty(HTMLDialogElement.prototype, "close", {
        configurable: true,
        value: function () {
          this.open = false;
        },
      });
    }
  });

  it("renders the file list when files are returned", async () => {
    vi.mocked(useArtifactFiles).mockReturnValue({
      files: [
        { name: "wing.stl", is_dir: false, size_bytes: 1024, modified: "" },
        { name: "fuselage.stp", is_dir: false, size_bytes: 2048, modified: "" },
      ],
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    } as unknown as ReturnType<typeof useArtifactFiles>);

    render(
      <ExecutionResultDialog
        open
        title="Test"
        planId={42}
        result={{
          status: "success",
          shape_keys: [],
          export_paths: [],
          error: null,
          duration_ms: 100,
          tessellation: null,
          artifact_dir: "/tmp/x",
          execution_id: "exec-1",
        }}
        onClose={() => {}}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("wing.stl")).toBeInTheDocument();
      expect(screen.getByText("fuselage.stp")).toBeInTheDocument();
    });
  });

  it("renders an empty state when no files were generated", async () => {
    vi.mocked(useArtifactFiles).mockReturnValue({
      files: [],
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    } as unknown as ReturnType<typeof useArtifactFiles>);

    render(
      <ExecutionResultDialog
        open
        title="Test"
        planId={42}
        result={{
          status: "success",
          shape_keys: [],
          export_paths: [],
          error: null,
          duration_ms: 100,
          tessellation: null,
          artifact_dir: "/tmp/x",
          execution_id: "exec-1",
        }}
        onClose={() => {}}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/no files generated/i)).toBeInTheDocument();
    });
  });

  it("renders a Download zip link with the correct URL", async () => {
    vi.mocked(useArtifactFiles).mockReturnValue({
      files: [{ name: "a.stl", is_dir: false, size_bytes: 4, modified: "" }],
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    } as unknown as ReturnType<typeof useArtifactFiles>);

    render(
      <ExecutionResultDialog
        open
        title="Test"
        planId={42}
        result={{
          status: "success",
          shape_keys: [],
          export_paths: [],
          error: null,
          duration_ms: 100,
          tessellation: null,
          artifact_dir: "/tmp/x",
          execution_id: "exec-99",
        }}
        onClose={() => {}}
      />,
    );

    const zipLink = await screen.findByRole("link", { name: /download zip/i });
    expect(zipLink.getAttribute("href")).toContain(
      "/construction-plans/42/artifacts/exec-99/zip",
    );
  });
});
