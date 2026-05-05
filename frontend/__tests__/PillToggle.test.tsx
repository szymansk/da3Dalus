import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = ({ size, ...rest }: Record<string, unknown>) =>
    React.createElement("span", { "data-testid": `icon-${size}`, ...rest });
  return { Package: icon, Box: icon };
});

import { PillToggle } from "@/components/ui/PillToggle";
import { Package, Box } from "lucide-react";

type View = "library" | "construction";

const OPTIONS = [
  { value: "library" as View, label: "Library", icon: Package },
  { value: "construction" as View, label: "Construction Parts", icon: Box },
];

describe("PillToggle", () => {
  it("renders all option labels", () => {
    render(<PillToggle options={OPTIONS} value="library" onChange={() => {}} />);
    expect(screen.getByText("Library")).toBeDefined();
    expect(screen.getByText("Construction Parts")).toBeDefined();
  });

  it("applies active styling to the selected option", () => {
    render(<PillToggle options={OPTIONS} value="library" onChange={() => {}} />);
    const activeBtn = screen.getByText("Library").closest("button")!;
    expect(activeBtn.className).toContain("bg-primary");
    const inactiveBtn = screen.getByText("Construction Parts").closest("button")!;
    expect(inactiveBtn.className).not.toContain("bg-primary");
  });

  it("calls onChange with the clicked option value", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PillToggle options={OPTIONS} value="library" onChange={onChange} />);
    await user.click(screen.getByText("Construction Parts"));
    expect(onChange).toHaveBeenCalledWith("construction");
  });

  it("calls onChange even when clicking the already-active option", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PillToggle options={OPTIONS} value="library" onChange={onChange} />);
    await user.click(screen.getByText("Library"));
    expect(onChange).toHaveBeenCalledWith("library");
  });

  it("uses custom isActive when provided", () => {
    const isActive = (opt: View, cur: View) =>
      opt === cur || (opt === "construction" && cur === "library");
    render(
      <PillToggle options={OPTIONS} value="library" onChange={() => {}} isActive={isActive} />,
    );
    const libraryBtn = screen.getByText("Library").closest("button")!;
    const constructionBtn = screen.getByText("Construction Parts").closest("button")!;
    expect(libraryBtn.className).toContain("bg-primary");
    expect(constructionBtn.className).toContain("bg-primary");
  });
});
