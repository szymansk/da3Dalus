import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { InfoLabel } from "@/components/workbench/InfoLabel";

describe("InfoLabel", () => {
  it("renders the label text", () => {
    render(<InfoLabel label="Target Cruise" description="Cruise speed in m/s." />);
    expect(screen.getByText("Target Cruise")).toBeInTheDocument();
  });

  it("renders a tooltip element with the description when provided", () => {
    render(
      <InfoLabel
        label="Target Cruise"
        description="Cruise speed in m/s."
      />,
    );
    const tip = screen.getByRole("tooltip", { hidden: true });
    expect(tip).toBeInTheDocument();
    expect(tip).toHaveTextContent("Cruise speed in m/s.");
  });

  it("tooltip is hidden by default (Tailwind `hidden` class)", () => {
    render(
      <InfoLabel label="A" description="hidden-by-default" />,
    );
    const tip = screen.getByRole("tooltip", { hidden: true });
    expect(tip.className).toContain("hidden");
    expect(tip.className).toContain("group-hover/info:block");
    expect(tip.className).toContain("group-focus-within/info:block");
  });

  it("renders a focusable HelpCircle icon when a description is provided", () => {
    const { container } = render(
      <InfoLabel label="Foo" description="hello" />,
    );
    // The icon is the only tabIndex=0 element inside the label.
    const focusable = container.querySelector("[tabindex='0']");
    expect(focusable).not.toBeNull();
  });

  it("links the label to a form control via htmlFor", () => {
    const { container } = render(
      <InfoLabel label="Foo" description="bar" htmlFor="my-input" />,
    );
    const label = container.querySelector("label");
    expect(label?.getAttribute("for")).toBe("my-input");
  });

  it("renders a plain label without icon/tooltip when no description is given", () => {
    const { container } = render(<InfoLabel label="Bare" htmlFor="x" />);
    expect(screen.getByText("Bare")).toBeInTheDocument();
    expect(container.querySelector("[role='tooltip']")).toBeNull();
    expect(container.querySelector("[tabindex='0']")).toBeNull();
  });

  it("renders a plain label without icon/tooltip when description is empty string", () => {
    const { container } = render(<InfoLabel label="Bare" description="" />);
    expect(screen.getByText("Bare")).toBeInTheDocument();
    expect(container.querySelector("[role='tooltip']")).toBeNull();
  });

  it("plain label still respects htmlFor", () => {
    const { container } = render(<InfoLabel label="Bare" htmlFor="y" />);
    const label = container.querySelector("label");
    expect(label?.getAttribute("for")).toBe("y");
  });
});
