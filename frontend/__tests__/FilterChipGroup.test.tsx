/**
 * Tests for the FilterChipGroup primitive (gh-835).
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { FilterChipGroup } from "@/components/workbench/FilterChipGroup";

const OPTIONS = [
  { value: "reflexed" as const, label: "Reflexed", description: "Flying-wing" },
  { value: "symmetric" as const, label: "Symmetric" },
  { value: "flat_bottom" as const, label: "Flat" },
] as const;

describe("FilterChipGroup", () => {
  it("renders all option labels", () => {
    render(
      <FilterChipGroup
        options={OPTIONS}
        selected={[]}
        onChange={() => {}}
        ariaLabel="Test group"
      />,
    );
    expect(screen.getByText("Reflexed")).toBeInTheDocument();
    expect(screen.getByText("Symmetric")).toBeInTheDocument();
    expect(screen.getByText("Flat")).toBeInTheDocument();
  });

  it("marks selected chips with aria-pressed=true", () => {
    render(
      <FilterChipGroup
        options={OPTIONS}
        selected={["reflexed"]}
        onChange={() => {}}
        ariaLabel="Test group"
      />,
    );
    const reflexed = screen.getByTestId("chip-reflexed");
    const symmetric = screen.getByTestId("chip-symmetric");
    expect(reflexed).toHaveAttribute("aria-pressed", "true");
    expect(symmetric).toHaveAttribute("aria-pressed", "false");
  });

  it("calls onChange with newly added value when inactive chip clicked", () => {
    const onChange = vi.fn();
    render(
      <FilterChipGroup
        options={OPTIONS}
        selected={["reflexed"]}
        onChange={onChange}
        ariaLabel="Test group"
      />,
    );
    fireEvent.click(screen.getByTestId("chip-symmetric"));
    expect(onChange).toHaveBeenCalledWith(["reflexed", "symmetric"]);
  });

  it("calls onChange with value removed when active chip clicked", () => {
    const onChange = vi.fn();
    render(
      <FilterChipGroup
        options={OPTIONS}
        selected={["reflexed", "symmetric"]}
        onChange={onChange}
        ariaLabel="Test group"
      />,
    );
    fireEvent.click(screen.getByTestId("chip-reflexed"));
    expect(onChange).toHaveBeenCalledWith(["symmetric"]);
  });

  it("renders with empty selection (no error)", () => {
    expect(() =>
      render(
        <FilterChipGroup
          options={OPTIONS}
          selected={[]}
          onChange={() => {}}
          ariaLabel="Test group"
        />,
      ),
    ).not.toThrow();
  });

  it("renders with all selected", () => {
    render(
      <FilterChipGroup
        options={OPTIONS}
        selected={["reflexed", "symmetric", "flat_bottom"]}
        onChange={() => {}}
        ariaLabel="Test group"
      />,
    );
    expect(screen.getByTestId("chip-reflexed")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("chip-symmetric")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("chip-flat_bottom")).toHaveAttribute("aria-pressed", "true");
  });

  it("has role=group with correct ariaLabel", () => {
    const { container } = render(
      <FilterChipGroup
        options={OPTIONS}
        selected={[]}
        onChange={() => {}}
        ariaLabel="Familie filtern"
      />,
    );
    const group = container.querySelector('[role="group"]');
    expect(group).not.toBeNull();
    expect(group).toHaveAttribute("aria-label", "Familie filtern");
  });
});
