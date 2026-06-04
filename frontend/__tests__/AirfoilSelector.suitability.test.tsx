/**
 * Unit tests for AirfoilSelector suitability enhancements (gh-822).
 * Verifies: per-row badge via stats slot; sorted rows by score;
 * '🔍 Passende finden' toggle switches to ranked mode.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

// Mock SWR to return a fixed airfoil list
vi.mock("swr", () => ({
  default: vi.fn(() => ({
    data: {
      count: 3,
      airfoils: [
        { airfoil_name: "naca0015", file_name: "naca0015.dat" },
        { airfoil_name: "e423", file_name: "e423.dat" },
        { airfoil_name: "clark-y", file_name: "clark-y.dat" },
      ],
    },
    error: null,
    isLoading: false,
  })),
}));

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

import { AirfoilSelector } from "../components/workbench/AirfoilSelector";

// stats slot uses string values per the existing interface
const STATS: Record<string, string> = {
  "naca0015": "0.45",
  "e423": "0.85",
  "clark-y": "0.65",
};

describe("AirfoilSelector — suitability enhancements", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows stats badge text in dropdown rows when stats prop is given", async () => {
    const user = userEvent.setup();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        stats={STATS}
      />,
    );
    // Open the dropdown
    const trigger = screen.getByRole("button");
    await user.click(trigger);

    // Each airfoil row should show its stats value
    expect(screen.getByText("0.85")).toBeDefined(); // e423
    expect(screen.getByText("0.65")).toBeDefined(); // clark-y
    expect(screen.getByText("0.45")).toBeDefined(); // naca0015
  });

  it("does NOT show stats when stats prop is not provided", async () => {
    const user = userEvent.setup();
    render(<AirfoilSelector label="Root" value="naca0015" />);

    const trigger = screen.getByRole("button");
    await user.click(trigger);

    // No numeric score text
    expect(screen.queryByText("0.85")).toBeNull();
  });

  it("sorts rows by score desc when sortedNames prop provided", async () => {
    const user = userEvent.setup();
    // sortedNames: e423 (0.85) first, then clark-y (0.65), then naca0015 (0.45)
    const sortedNames = ["e423", "clark-y", "naca0015"];
    const { container } = render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        stats={STATS}
        sortedNames={sortedNames}
      />,
    );

    // The trigger button is the first button in the component (before dropdown opens)
    const buttons = screen.getAllByRole("button");
    // The first button (without the suitabilityToggle) is the dropdown trigger
    const triggerBtn = buttons[0];
    await user.click(triggerBtn);

    // After opening, look for the dropdown list
    const dropdownContainer = container.querySelector('[class*="max-h"]');
    expect(dropdownContainer).not.toBeNull();

    if (dropdownContainer) {
      // Get all the airfoil name spans in the dropdown (inside list item buttons)
      const listButtons = dropdownContainer.querySelectorAll('button');
      const texts = Array.from(listButtons)
        .map((btn) => {
          const nameSpan = btn.querySelector('span[class*="jetbrains"]');
          return nameSpan?.textContent ?? "";
        })
        .filter((t) => ["e423", "clark-y", "naca0015"].includes(t));
      // First item should be e423 (highest score)
      expect(texts[0]).toBe("e423");
    }
  });

  it("renders 'Passende finden' toggle button when suitabilityToggle is provided", async () => {
    const onToggle = vi.fn();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        stats={STATS}
        suitabilityToggle={{ active: false, onToggle }}
      />,
    );

    // The button should be visible even before opening dropdown
    expect(screen.getByTitle(/Passende finden/i)).toBeDefined();
  });

  it("calls onToggle when 'Passende finden' button is clicked", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        stats={STATS}
        suitabilityToggle={{ active: false, onToggle }}
      />,
    );

    const findBtn = screen.getByTitle(/Passende finden/i);
    await user.click(findBtn);
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it("shows ranked mode active styling when suitabilityToggle.active is true", () => {
    render(
      <AirfoilSelector
        label="Root"
        value="naca0015"
        stats={STATS}
        suitabilityToggle={{ active: true, onToggle: vi.fn() }}
      />,
    );

    const findBtn = screen.getByTitle(/Passende finden/i);
    // Active state — should have primary/accent styling
    expect(findBtn.className).toMatch(/primary|text-primary|text-\[#FF8400\]/);
  });
});
