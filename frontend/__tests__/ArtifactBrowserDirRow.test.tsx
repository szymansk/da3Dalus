/**
 * Coverage for ArtifactBrowserDialog's directory-row rendering, touched by
 * the SonarCloud chore cleanup (S1082 + S6819 → directory rows render as a
 * real <button type="button"> instead of a <div role="button">; file rows
 * stay non-interactive <div>s).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import type { ArtifactDirectory, ArtifactFile } from "@/hooks/useConstructionPlans";

const mockUsePlanArtifacts = vi.fn();
const mockUseArtifactFiles = vi.fn();

vi.mock("@/hooks/useConstructionPlans", () => ({
  usePlanArtifacts: (...a: unknown[]) => mockUsePlanArtifacts(...a),
  useArtifactFiles: (...a: unknown[]) => mockUseArtifactFiles(...a),
  deleteArtifactFile: vi.fn(),
  deleteExecution: vi.fn(),
  artifactDownloadUrl: () => "http://x/download",
}));

vi.mock("@/hooks/useDialog", () => ({
  useDialog: () => ({ dialogRef: { current: null }, handleClose: vi.fn() }),
}));

import { ArtifactBrowserDialog } from "@/components/workbench/construction-plans/ArtifactBrowserDialog";

const EXEC: ArtifactDirectory = {
  execution_id: "exec-1",
  plan_id: 1,
  aeroplane_id: "a1",
  created: "2026-01-01T00:00:00Z",
  file_count: 2,
};

function file(overrides: Partial<ArtifactFile>): ArtifactFile {
  return { name: "x", is_dir: false, size_bytes: 10, modified: "2026-01-01T00:00:00Z", ...overrides };
}

beforeEach(() => {
  mockUsePlanArtifacts.mockReturnValue({
    executions: [EXEC],
    error: undefined,
    isLoading: false,
    mutate: vi.fn(),
  });
  mockUseArtifactFiles.mockReturnValue({
    files: [file({ name: "sub", is_dir: true }), file({ name: "part.step", is_dir: false })],
    error: undefined,
    isLoading: false,
    mutate: vi.fn(),
  });
});

describe("ArtifactBrowserDialog directory rows (S1082 / S6819)", () => {
  it("renders directory rows as a real <button> and files as non-buttons", () => {
    render(<ArtifactBrowserDialog open planId={1} planName="P" onClose={vi.fn()} />);

    // Content lives inside a jsdom <dialog> that is never shown via
    // showModal(), so its descendants are "hidden" for a11y queries.
    const dirLabel = screen.getByText("sub");
    const dirButton = dirLabel.closest("button");
    expect(dirButton).not.toBeNull();
    expect(dirButton).toHaveAttribute("type", "button");

    // The file name is NOT rendered inside a button.
    const fileLabel = screen.getByText("part.step");
    expect(fileLabel.closest("button")).toBeNull();
  });

  it("navigates into a directory when its button is clicked", () => {
    render(<ArtifactBrowserDialog open planId={1} planName="P" onClose={vi.fn()} />);
    const dirButton = screen.getByText("sub").closest("button");
    expect(dirButton).not.toBeNull();
    fireEvent.click(dirButton as HTMLButtonElement);
    // Navigation triggers a re-fetch of files at the new subpath: the hook is
    // called again with the "sub" currentPath.
    const calledPaths = mockUseArtifactFiles.mock.calls.map((c) => c[2]);
    expect(calledPaths).toContain("sub");
  });
});
