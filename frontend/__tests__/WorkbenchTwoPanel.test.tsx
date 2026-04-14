import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

import { WorkbenchTwoPanel } from "../components/workbench/WorkbenchTwoPanel";

describe("WorkbenchTwoPanel", () => {
  it("renders two children side by side", () => {
    render(
      <WorkbenchTwoPanel>
        <div data-testid="left">Left</div>
        <div data-testid="right">Right</div>
      </WorkbenchTwoPanel>,
    );
    expect(screen.getByTestId("left")).toBeTruthy();
    expect(screen.getByTestId("right")).toBeTruthy();
  });

  it("left panel has correct default width of 360px", () => {
    render(
      <WorkbenchTwoPanel>
        <div data-testid="left">Left</div>
        <div data-testid="right">Right</div>
      </WorkbenchTwoPanel>,
    );
    const leftPanel = screen.getByTestId("left").parentElement!;
    expect(leftPanel.style.width).toBe("360px");
    expect(leftPanel.style.minWidth).toBe("360px");
  });

  it("applies custom leftWidth prop", () => {
    render(
      <WorkbenchTwoPanel leftWidth={480}>
        <div data-testid="left">Left</div>
        <div data-testid="right">Right</div>
      </WorkbenchTwoPanel>,
    );
    const leftPanel = screen.getByTestId("left").parentElement!;
    expect(leftPanel.style.width).toBe("480px");
    expect(leftPanel.style.minWidth).toBe("480px");
  });

  it("renders gracefully with a single child", () => {
    render(
      <WorkbenchTwoPanel>
        <div data-testid="only">Only child</div>
      </WorkbenchTwoPanel>,
    );
    expect(screen.getByTestId("only")).toBeTruthy();
    // Right panel exists but is empty — no crash
    const container = screen.getByTestId("only").parentElement!.parentElement!;
    expect(container.children).toHaveLength(2);
  });
});
