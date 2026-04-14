/**
 * Unit tests for the TreeCard shared component.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

import { TreeCard } from "../components/workbench/TreeCard";

describe("TreeCard", () => {
  it("renders title text", () => {
    render(<TreeCard title="Weight Tree">body</TreeCard>);

    expect(screen.getByText("Weight Tree")).toBeDefined();
  });

  it("renders badge with muted variant class by default", () => {
    render(
      <TreeCard title="Weight" badge="1.177 kg">
        body
      </TreeCard>,
    );

    const badge = screen.getByText("1.177 kg");
    expect(badge).toBeDefined();
    expect(badge.className).toContain("text-muted-foreground");
    expect(badge.className).not.toContain("text-primary");
  });

  it("renders badge with primary variant class when specified", () => {
    render(
      <TreeCard title="Weight" badge="1.177 kg" badgeVariant="primary">
        body
      </TreeCard>,
    );

    const badge = screen.getByText("1.177 kg");
    expect(badge.className).toContain("text-primary");
  });

  it("renders actions slot content", () => {
    render(
      <TreeCard
        title="Tree"
        actions={<button data-testid="action-btn">Add</button>}
      >
        body
      </TreeCard>,
    );

    expect(screen.getByTestId("action-btn")).toBeDefined();
    expect(screen.getByText("Add")).toBeDefined();
  });

  it("body container has overflow-y-auto class", () => {
    render(
      <TreeCard title="Tree">
        <span data-testid="child">content</span>
      </TreeCard>,
    );

    const child = screen.getByTestId("child");
    const body = child.parentElement!;
    expect(body.className).toContain("overflow-y-auto");
  });
});
