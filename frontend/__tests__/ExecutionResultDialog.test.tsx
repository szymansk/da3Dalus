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

  it("gh#344: shows Download zip even when no files are generated", async () => {
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
          execution_id: "exec-empty",
        }}
        onClose={() => {}}
      />,
    );

    // The zip link MUST be present even when the file list is empty —
    // the user must always have a download path on a successful execution.
    const zipLink = await screen.findByRole("link", { name: /download zip/i });
    expect(zipLink.getAttribute("href")).toContain(
      "/construction-plans/42/artifacts/exec-empty/zip",
    );
  });

  it("gh#344: renders nested file paths returned by the recursive listing", async () => {
    // Recursive listing puts subdir files in the flat list with relative
    // path in the `name` field — this is the bug fix from gh#344.
    vi.mocked(useArtifactFiles).mockReturnValue({
      files: [
        {
          name: "wing/export_stl_main_wing.loft.stl",
          is_dir: false,
          size_bytes: 4096,
          modified: "",
        },
        {
          name: "fuselage/body.stp",
          is_dir: false,
          size_bytes: 8192,
          modified: "",
        },
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
          execution_id: "exec-nested",
        }}
        onClose={() => {}}
      />,
    );

    await waitFor(() => {
      expect(
        screen.getByText("wing/export_stl_main_wing.loft.stl"),
      ).toBeInTheDocument();
      expect(screen.getByText("fuselage/body.stp")).toBeInTheDocument();
    });

    // Verify the download link preserves the relative path
    const wingLink = screen.getByText("wing/export_stl_main_wing.loft.stl");
    expect(wingLink.getAttribute("href")).toContain(
      "/artifacts/exec-nested/wing/export_stl_main_wing.loft.stl",
    );
  });

  it("gh#344: useArtifactFiles is called with recursive=true", async () => {
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
          execution_id: "exec-r",
        }}
        onClose={() => {}}
      />,
    );

    // Pin the contract: the dialog asks the hook for a recursive listing
    // so files in subdirectories are included.
    expect(vi.mocked(useArtifactFiles)).toHaveBeenCalledWith(
      42,
      "exec-r",
      "",
      true,
    );
  });
});
