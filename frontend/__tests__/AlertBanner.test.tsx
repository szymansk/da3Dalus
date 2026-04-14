import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => ({
  Info: (props: Record<string, unknown>) => (
    <svg data-testid="info-icon" {...props} />
  ),
}));

import { AlertBanner } from "../components/workbench/AlertBanner";

describe("AlertBanner", () => {
  it("renders default title and children text", () => {
    render(<AlertBanner>Some body text here</AlertBanner>);

    expect(
      screen.getByText("Coming soon \u2014 backend wiring in progress"),
    ).toBeDefined();
    expect(screen.getByText("Some body text here")).toBeDefined();
  });

  it("renders custom title when provided", () => {
    render(<AlertBanner title="Custom title">Body content</AlertBanner>);

    expect(screen.getByText("Custom title")).toBeDefined();
    expect(screen.getByText("Body content")).toBeDefined();
  });

  it("renders the Info icon", () => {
    render(<AlertBanner>Content</AlertBanner>);

    expect(screen.getByTestId("info-icon")).toBeDefined();
  });
});
