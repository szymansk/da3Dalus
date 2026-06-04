/**
 * Tests for the gh-837 'In Verwendung' section in AirfoilSelector.
 *
 * Covers:
 * - 'In Verwendung' header and items render at the top when usedNames provided
 * - Selection from the 'In Verwendung' section calls onChange
 * - Search filters both the 'In Verwendung' section and the full list
 * - Empty / absent usedNames → no 'In Verwendung' section
 * - De-duplication of usedNames
 * - Currently selected airfoil is marked in the 'In Verwendung' section
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

// SWR mock returning a larger list so the full-list section also renders
vi.mock("swr", () => ({
  default: vi.fn(() => ({
    data: {
      count: 4,
      airfoils: [
        { airfoil_name: "clark-y", file_name: "clark-y.dat" },
        { airfoil_name: "e423", file_name: "e423.dat" },
        { airfoil_name: "naca0015", file_name: "naca0015.dat" },
        { airfoil_name: "naca2412", file_name: "naca2412.dat" },
      ],
    },
    error: null,
    isLoading: false,
  })),
}));

import { AirfoilSelector } from "../components/workbench/AirfoilSelector";

describe("AirfoilSelector — 'In Verwendung' section (gh-837)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders 'In Verwendung' header at the top of the dropdown when usedNames is provided", async () => {
    const user = userEvent.setup();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        usedNames={["e423", "clark-y"]}
      />,
    );
    await user.click(screen.getByRole("button"));
    expect(screen.getByTestId("in-verwendung-header")).toBeDefined();
    expect(screen.getByTestId("in-verwendung-header").textContent).toMatch(
      /In Verwendung/i,
    );
  });

  it("renders all usedNames as items in the 'In Verwendung' section", async () => {
    const user = userEvent.setup();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        usedNames={["e423", "clark-y"]}
      />,
    );
    await user.click(screen.getByRole("button"));
    const items = screen.getAllByTestId("in-verwendung-item");
    const texts = items.map((el) => el.textContent);
    expect(texts.some((t) => t?.includes("e423"))).toBe(true);
    expect(texts.some((t) => t?.includes("clark-y"))).toBe(true);
  });

  it("places the 'In Verwendung' section ABOVE the full list", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        usedNames={["e423"]}
      />,
    );
    await user.click(screen.getByRole("button"));

    const listContainer = container.querySelector('[class*="max-h"]');
    expect(listContainer).not.toBeNull();

    // All children (header, items, divider, then full-list items)
    const allButtons = listContainer!.querySelectorAll("button");
    const buttonTexts = Array.from(allButtons).map((b) => b.textContent ?? "");

    // The first airfoil-named button should be the used one (e423)
    const firstAirfoilBtn = buttonTexts.find((t) =>
      ["e423", "clark-y", "naca0015", "naca2412"].some((n) => t.includes(n)),
    );
    expect(firstAirfoilBtn).toContain("e423");
  });

  it("calling select() on a 'In Verwendung' item calls onChange with correct name", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        onChange={onChange}
        usedNames={["e423", "clark-y"]}
      />,
    );
    await user.click(screen.getByRole("button"));
    const items = screen.getAllByTestId("in-verwendung-item");
    const e423Item = items.find((el) => el.textContent?.includes("e423"));
    expect(e423Item).toBeDefined();
    await user.click(e423Item!);
    expect(onChange).toHaveBeenCalledWith("e423");
  });

  it("does NOT show the 'In Verwendung' section when usedNames is empty", async () => {
    const user = userEvent.setup();
    render(<AirfoilSelector label="Root" value="naca0015" usedNames={[]} />);
    await user.click(screen.getByRole("button"));
    expect(screen.queryByTestId("in-verwendung-header")).toBeNull();
    expect(screen.queryByTestId("in-verwendung-item")).toBeNull();
  });

  it("does NOT show the 'In Verwendung' section when usedNames prop is absent", async () => {
    const user = userEvent.setup();
    render(<AirfoilSelector label="Root" value="naca0015" />);
    await user.click(screen.getByRole("button"));
    expect(screen.queryByTestId("in-verwendung-header")).toBeNull();
  });

  it("search filters the 'In Verwendung' section (matching items remain, non-matching items are hidden)", async () => {
    const user = userEvent.setup();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        usedNames={["e423", "clark-y"]}
      />,
    );
    await user.click(screen.getByRole("button"));
    const searchInput = screen.getByPlaceholderText("Search airfoils…");
    await user.type(searchInput, "e42");

    // e423 should still appear in 'In Verwendung'
    const items = screen.getAllByTestId("in-verwendung-item");
    expect(items.some((el) => el.textContent?.includes("e423"))).toBe(true);
    // clark-y should be filtered out of 'In Verwendung'
    expect(items.every((el) => !el.textContent?.includes("clark-y"))).toBe(true);
  });

  it("search also filters the regular (full) list in addition to the 'In Verwendung' section", async () => {
    const user = userEvent.setup();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        usedNames={["e423"]}
      />,
    );
    await user.click(screen.getByRole("button"));
    const searchInput = screen.getByPlaceholderText("Search airfoils…");
    await user.type(searchInput, "naca");

    // The full list should show naca entries
    expect(screen.queryByText("clark-y")).toBeNull();
    // naca names should still appear somewhere on screen
    const nacaTexts = screen
      .getAllByRole("button")
      .flatMap((b) => [b.textContent ?? ""])
      .filter((t) => t.includes("naca"));
    expect(nacaTexts.length).toBeGreaterThan(0);
  });

  it("shows 'No airfoils found' only when BOTH sections produce no results", async () => {
    const user = userEvent.setup();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        usedNames={["e423"]}
      />,
    );
    await user.click(screen.getByRole("button"));
    const searchInput = screen.getByPlaceholderText("Search airfoils…");
    await user.type(searchInput, "zzz_no_match");
    expect(screen.getByText("No airfoils found")).toBeDefined();
  });

  it("de-duplicates usedNames (duplicate entries appear only once in the section)", async () => {
    const user = userEvent.setup();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        usedNames={["e423", "e423", "clark-y"]}
      />,
    );
    await user.click(screen.getByRole("button"));
    const items = screen.getAllByTestId("in-verwendung-item");
    const e423Items = items.filter((el) => el.textContent?.includes("e423"));
    // e423 should appear exactly once despite being passed twice
    expect(e423Items).toHaveLength(1);
  });

  it("marks the currently selected airfoil with a Check icon when it appears in the 'In Verwendung' section", async () => {
    const user = userEvent.setup();
    // value='e423' is also in usedNames
    render(
      <AirfoilSelector
        label="Root"
        value="e423"
        usedNames={["e423", "clark-y"]}
      />,
    );
    await user.click(screen.getByRole("button"));
    const items = screen.getAllByTestId("in-verwendung-item");
    const e423Item = items.find((el) => el.textContent?.includes("e423"));
    expect(e423Item).toBeDefined();
    // The Check icon is rendered as an svg with data-testid="check" (from lucide mock)
    const checkIcon = e423Item!.querySelector('[data-testid="check"]');
    expect(checkIcon).not.toBeNull();
  });
});
