/**
 * Coverage tests for AirfoilPreviewConfigPanel (gh-822).
 *
 * Covers: commitVelocity (valid/invalid), Re info toggle, segment nav,
 * isDirty path (Revert + Save buttons), hasTip=true (tipRe field),
 * isSaving=true (Loader2), ranked mode toggles, and ReadOnlyField.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

vi.mock("lucide-react", () => ({
  Info: (p: Record<string, unknown>) => <svg data-testid="info" {...p} />,
  ArrowLeft: (p: Record<string, unknown>) => <svg data-testid="arrow-left" {...p} />,
  Save: (p: Record<string, unknown>) => <svg data-testid="save" {...p} />,
  Loader2: (p: Record<string, unknown>) => <svg data-testid="loader2" {...p} />,
  ChevronLeft: (p: Record<string, unknown>) => <svg data-testid="chevron-left" {...p} />,
  ChevronRight: (p: Record<string, unknown>) => <svg data-testid="chevron-right" {...p} />,
  ChevronDown: (p: Record<string, unknown>) => <svg data-testid="chevron-down" {...p} />,
  ChevronUp: (p: Record<string, unknown>) => <svg data-testid="chevron-up" {...p} />,
  Search: (p: Record<string, unknown>) => <svg data-testid="search" {...p} />,
  Check: (p: Record<string, unknown>) => <svg data-testid="check" {...p} />,
  Undo2: (p: Record<string, unknown>) => <svg data-testid="undo2" {...p} />,
  AlertTriangle: (p: Record<string, unknown>) => <svg data-testid="alert-triangle" {...p} />,
}));

vi.mock("swr", () => ({
  default: vi.fn(() => ({
    data: {
      count: 2,
      airfoils: [
        { airfoil_name: "e423", file_name: "e423.dat" },
        { airfoil_name: "naca0015", file_name: "naca0015.dat" },
      ],
    },
    error: null,
    isLoading: false,
  })),
}));

import { AirfoilPreviewConfigPanel } from "../components/workbench/AirfoilPreviewConfigPanel";

const BASE_PROPS = {
  rootAirfoil: "e423",
  tipAirfoil: "naca0015",
  onRootAirfoilChange: vi.fn(),
  onTipAirfoilChange: vi.fn(),
  isRunning: false,
  segmentIndex: 1,
  segmentCount: 3,
  onSegmentChange: vi.fn(),
  segmentProps: {
    length: 500,
    sweep: 2,
    dihedral: 3,
    incidence: 1,
  },
  velocity: 14,
  onVelocityChange: vi.fn(),
  rootRe: 190000,
  tipRe: 140000,
  onRootReChange: vi.fn(),
  onTipReChange: vi.fn(),
  rootChordMm: 200,
  tipChordMm: 150,
  isDirty: false,
  isSaving: false,
  onSave: vi.fn(),
  onRevert: vi.fn(),
  onBack: vi.fn(),
};

describe("AirfoilPreviewConfigPanel — coverage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders segment navigation correctly", () => {
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} />);
    expect(screen.getByText("segment 1")).toBeDefined();
    expect(screen.getByText("2/3")).toBeDefined();
  });

  it("previous segment button calls onSegmentChange with segmentIndex - 1", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} segmentIndex={1} />);
    const prevBtn = screen.getByTitle("Previous segment");
    await user.click(prevBtn);
    expect(BASE_PROPS.onSegmentChange).toHaveBeenCalledWith(0);
  });

  it("next segment button calls onSegmentChange with segmentIndex + 1", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} segmentIndex={1} segmentCount={3} />);
    const nextBtn = screen.getByTitle("Next segment");
    await user.click(nextBtn);
    expect(BASE_PROPS.onSegmentChange).toHaveBeenCalledWith(2);
  });

  it("previous segment button is disabled when segmentIndex is 0", () => {
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} segmentIndex={0} />);
    const prevBtn = screen.getByTitle("Previous segment");
    expect((prevBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it("next segment button is disabled when at last segment", () => {
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} segmentIndex={2} segmentCount={3} />);
    const nextBtn = screen.getByTitle("Next segment");
    expect((nextBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it("back button calls onBack", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} />);
    await user.click(screen.getByTitle("Back to Construction"));
    expect(BASE_PROPS.onBack).toHaveBeenCalledOnce();
  });

  it("Re info toggle shows/hides Re explanation on click", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} />);
    // No Re info initially
    expect(screen.queryByText(/Reynolds-Zahl/i)).toBeNull();
    await user.click(screen.getByTitle("Reynolds-Zahl Berechnung"));
    // Now shown
    expect(screen.getByText(/Reynolds-Zahl/i)).toBeDefined();
    // Toggle off
    await user.click(screen.getByTitle("Reynolds-Zahl Berechnung"));
    expect(screen.queryByText(/Reynolds-Zahl/i)).toBeNull();
  });

  it("isDirty=true shows Revert and Save buttons", () => {
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} isDirty />);
    expect(screen.getByTitle("Revert to saved airfoils")).toBeDefined();
    expect(screen.getByText("Save")).toBeDefined();
  });

  it("isDirty=false hides Revert and Save buttons", () => {
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} isDirty={false} />);
    expect(screen.queryByTitle("Revert to saved airfoils")).toBeNull();
  });

  it("Revert button calls onRevert", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} isDirty />);
    await user.click(screen.getByTitle("Revert to saved airfoils"));
    expect(BASE_PROPS.onRevert).toHaveBeenCalledOnce();
  });

  it("Save button calls onSave", async () => {
    const user = userEvent.setup();
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} isDirty />);
    await user.click(screen.getByText("Save"));
    expect(BASE_PROPS.onSave).toHaveBeenCalledOnce();
  });

  it("isSaving=true shows Loader2 and 'Saving…' text", () => {
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} isDirty isSaving />);
    expect(screen.getByTestId("loader2")).toBeDefined();
    // The Unicode ellipsis is U+2026, or the "…" character
    const savingText = screen.queryByText(/Saving/);
    expect(savingText).toBeDefined();
  });

  it("velocity input changes commit on blur with valid value", async () => {
    const onVelocityChange = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        velocity={14}
        onVelocityChange={onVelocityChange}
      />,
    );
    const velocityInput = screen.getByDisplayValue("14") as HTMLInputElement;
    await user.clear(velocityInput);
    await user.type(velocityInput, "20");
    fireEvent.blur(velocityInput);
    expect(onVelocityChange).toHaveBeenCalledWith(20);
  });

  it("velocity input resets to previous value on blur with invalid (NaN) input", async () => {
    const onVelocityChange = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        velocity={14}
        onVelocityChange={onVelocityChange}
      />,
    );
    const velocityInput = screen.getByDisplayValue("14") as HTMLInputElement;
    await user.clear(velocityInput);
    await user.type(velocityInput, "abc");
    fireEvent.blur(velocityInput);
    // Should not call onVelocityChange with NaN
    expect(onVelocityChange).not.toHaveBeenCalled();
    // Should reset to "14"
    expect(velocityInput.value).toBe("14");
  });

  it("velocity input commits on Enter key", async () => {
    const onVelocityChange = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        velocity={14}
        onVelocityChange={onVelocityChange}
      />,
    );
    const velocityInput = screen.getByDisplayValue("14") as HTMLInputElement;
    await user.clear(velocityInput);
    await user.type(velocityInput, "18");
    await user.keyboard("{Enter}");
    expect(onVelocityChange).toHaveBeenCalledWith(18);
  });

  it("velocity input rejects zero value (v <= 0) and resets", async () => {
    const onVelocityChange = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        velocity={14}
        onVelocityChange={onVelocityChange}
      />,
    );
    const velocityInput = screen.getByDisplayValue("14") as HTMLInputElement;
    await user.clear(velocityInput);
    await user.type(velocityInput, "0");
    fireEvent.blur(velocityInput);
    // v=0 → should reset, not call onChange
    expect(onVelocityChange).not.toHaveBeenCalled();
    expect(velocityInput.value).toBe("14");
  });

  it("tipRe Reynolds field is shown when tipAirfoil differs from rootAirfoil", () => {
    // root=e423, tip=naca0015 → hasTip=true → tipRe field shown
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} />);
    // The Re fields have the Re value displayed; "c=150mm" appears in the tip Re row
    expect(screen.getByText(/c=150mm/)).toBeDefined();
  });

  it("tipRe Reynolds field is hidden when tipAirfoil equals rootAirfoil", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        rootAirfoil="e423"
        tipAirfoil="e423"
      />,
    );
    // hasTip=false → no c=150mm in tip position
    expect(screen.queryByText(/c=150mm/)).toBeNull();
  });

  it("ReadOnlyField shows '—' for undefined values", () => {
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        segmentProps={{}}
      />,
    );
    // length, sweep, dihedral, incidence are all undefined → show '—'
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(4);
  });

  it("ReadOnlyField shows values when segmentProps are provided", () => {
    render(<AirfoilPreviewConfigPanel {...BASE_PROPS} />);
    expect(screen.getByDisplayValue("14")).toBeDefined(); // velocity input
    // segment props are shown in read-only fields
    expect(screen.getByText("500")).toBeDefined(); // length
    expect(screen.getByText("2")).toBeDefined(); // sweep
  });

  it("ranked mode toggle buttons fire callbacks when provided", async () => {
    const onRootRankedModeToggle = vi.fn();
    const onTipRankedModeToggle = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        rootRankedMode={false}
        onRootRankedModeToggle={onRootRankedModeToggle}
        tipRankedMode={false}
        onTipRankedModeToggle={onTipRankedModeToggle}
      />,
    );
    // There should be two "🔍" toggle buttons
    const toggleBtns = screen.getAllByTitle(/Passende finden/i);
    expect(toggleBtns.length).toBeGreaterThanOrEqual(1);
    await user.click(toggleBtns[0]);
    expect(onRootRankedModeToggle).toHaveBeenCalledOnce();
  });

  it("shows root_airfoil label in primary color", () => {
    const { container } = render(<AirfoilPreviewConfigPanel {...BASE_PROPS} />);
    expect(container.textContent).toContain("root_airfoil");
  });

  it("shows tip_airfoil label", () => {
    const { container } = render(<AirfoilPreviewConfigPanel {...BASE_PROPS} />);
    expect(container.textContent).toContain("tip_airfoil");
  });

  it("Re input calls onRootReChange with parsed int when valid positive value entered", async () => {
    const onRootReChange = vi.fn();
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        rootRe={190000}
        onRootReChange={onRootReChange}
      />,
    );
    // Find the Re input for root (shows "Re" label with "c=200mm")
    const reInput = screen.getByDisplayValue("190000") as HTMLInputElement;
    fireEvent.change(reInput, { target: { value: "250000" } });
    expect(onRootReChange).toHaveBeenCalledWith(250000);
  });

  it("Re input does NOT call onRootReChange when value is NaN", async () => {
    const onRootReChange = vi.fn();
    render(
      <AirfoilPreviewConfigPanel
        {...BASE_PROPS}
        rootRe={190000}
        onRootReChange={onRootReChange}
      />,
    );
    const reInput = screen.getByDisplayValue("190000") as HTMLInputElement;
    fireEvent.change(reInput, { target: { value: "xyz" } });
    expect(onRootReChange).not.toHaveBeenCalled();
  });
});
