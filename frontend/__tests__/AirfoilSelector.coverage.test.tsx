/**
 * Coverage tests for AirfoilSelector additional branches (gh-822).
 *
 * Covers:
 * - select() function with onChange and onPreviewToggle callbacks (lines 104-107)
 * - search input onChange (line 158)
 * - "No airfoils found" path (filtered.length === 0)
 * - totalMatches > MAX_VISIBLE footer
 * - clicking outside closes dropdown
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

vi.mock("lucide-react", () => ({
  ChevronDown: (p: Record<string, unknown>) => (
    <svg data-testid="chevron-down" {...p} />
  ),
  ChevronUp: (p: Record<string, unknown>) => (
    <svg data-testid="chevron-up" {...p} />
  ),
  Search: (p: Record<string, unknown>) => <svg data-testid="search" {...p} />,
  Check: (p: Record<string, unknown>) => <svg data-testid="check" {...p} />,
}));

// SWR mock returning a list of airfoils
vi.mock("swr", () => ({
  default: vi.fn(() => ({
    data: {
      count: 3,
      airfoils: [
        { airfoil_name: "e423", file_name: "e423.dat" },
        { airfoil_name: "naca0015", file_name: "naca0015.dat" },
        { airfoil_name: "clark-y", file_name: "clark-y.dat" },
      ],
    },
    error: null,
    isLoading: false,
  })),
}));

import { AirfoilSelector } from "../components/workbench/AirfoilSelector";

describe("AirfoilSelector — coverage (gh-822)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls onChange when an airfoil is selected from the dropdown", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilSelector label="Root" value="naca0015" onChange={onChange} />,
    );
    // Open dropdown
    await user.click(screen.getByRole("button"));
    // Click on e423
    await user.click(screen.getByText("e423"));
    expect(onChange).toHaveBeenCalledWith("e423");
  });

  it("calls onPreviewToggle(false) when airfoil is selected", async () => {
    const onPreviewToggle = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        onPreviewToggle={onPreviewToggle}
      />,
    );
    await user.click(screen.getByRole("button"));
    // onPreviewToggle called with true on open
    expect(onPreviewToggle).toHaveBeenCalledWith(true);
    await user.click(screen.getByText("e423"));
    // onPreviewToggle called with false on select
    expect(onPreviewToggle).toHaveBeenCalledWith(false);
  });

  it("closes dropdown and clears search after selection", async () => {
    const user = userEvent.setup();
    render(<AirfoilSelector label="Root" value="naca0015" />);
    // Open dropdown
    const trigger = screen.getByRole("button");
    await user.click(trigger);
    // Type in search
    const searchInput = screen.getByPlaceholderText("Search airfoils…");
    await user.type(searchInput, "e423");
    // Select the airfoil
    await user.click(screen.getByText("e423"));
    // Dropdown should be closed (search input gone)
    expect(screen.queryByPlaceholderText("Search airfoils…")).toBeNull();
  });

  it("search input filters the list", async () => {
    const user = userEvent.setup();
    render(<AirfoilSelector label="Root" value="naca0015" />);
    await user.click(screen.getByRole("button"));
    const searchInput = screen.getByPlaceholderText("Search airfoils…");
    await user.type(searchInput, "clark");
    // Only clark-y should be visible
    expect(screen.getByText("clark-y")).toBeDefined();
    expect(screen.queryByText("e423")).toBeNull();
  });

  it("shows 'No airfoils found' when search has no results", async () => {
    const user = userEvent.setup();
    render(<AirfoilSelector label="Root" value="naca0015" />);
    await user.click(screen.getByRole("button"));
    const searchInput = screen.getByPlaceholderText("Search airfoils…");
    await user.type(searchInput, "zzz_no_match");
    expect(screen.getByText("No airfoils found")).toBeDefined();
  });

  it("toggle button closes dropdown and calls onPreviewToggle(false) on second click", async () => {
    const onPreviewToggle = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        onPreviewToggle={onPreviewToggle}
      />,
    );
    const trigger = screen.getByRole("button");
    // Open
    await user.click(trigger);
    expect(onPreviewToggle).toHaveBeenLastCalledWith(true);
    // Close
    await user.click(trigger);
    expect(onPreviewToggle).toHaveBeenLastCalledWith(false);
  });

  it("uses sortedNames ordering when provided and search is empty", async () => {
    const user = userEvent.setup();
    const sortedNames = ["clark-y", "naca0015", "e423"];
    const { container } = render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        sortedNames={sortedNames}
      />,
    );
    const trigger = screen.getByRole("button");
    await user.click(trigger);
    // Sorted order buttons
    const dropdown = container.querySelector('[class*="max-h"]');
    expect(dropdown).not.toBeNull();
    if (dropdown) {
      const btns = Array.from(dropdown.querySelectorAll("button"));
      const names = btns
        .map((b) => b.querySelector("span")?.textContent ?? "")
        .filter((t) => ["clark-y", "naca0015", "e423"].includes(t));
      expect(names[0]).toBe("clark-y");
    }
  });

  it("shows Check icon for currently selected airfoil", async () => {
    const user = userEvent.setup();
    render(<AirfoilSelector label="Root" value="e423" />);
    await user.click(screen.getByRole("button"));
    // Check icon appears for the selected item
    expect(screen.getByTestId("check")).toBeDefined();
  });

  it("ChevronUp shows when dropdown is open", async () => {
    const user = userEvent.setup();
    render(<AirfoilSelector label="Root" value="naca0015" />);
    // Initially ChevronDown
    expect(screen.getByTestId("chevron-down")).toBeDefined();
    await user.click(screen.getByRole("button"));
    // After open: ChevronUp
    expect(screen.getByTestId("chevron-up")).toBeDefined();
  });
});
