import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { Wind: icon };
});

import { Chip } from "@/components/workbench/Chip";
import { Wind } from "lucide-react";

describe("Chip primitive", () => {
  it("renders symbol = value", () => {
    render(<Chip icon={Wind} symbol="V_md" value="13.2 m/s" />);
    expect(screen.getByText(/13\.2 m\/s/)).toBeInTheDocument();
  });

  it("renders valueNode in place of value when provided", () => {
    render(
      <Chip
        icon={Wind}
        symbol="CG"
        valueNode={<span data-testid="rich">rich</span>}
      />,
    );
    expect(screen.getByTestId("rich")).toBeInTheDocument();
  });

  it("applies stale red colour to value when stale=true", () => {
    const { container } = render(
      <Chip icon={Wind} symbol="V_md" value="13.2" stale />,
    );
    const valueSpan = container.querySelector("span.text-red-400");
    expect(valueSpan).not.toBeNull();
  });

  it("applies valueColorClassName when not stale", () => {
    const { container } = render(
      <Chip
        icon={Wind}
        symbol="e"
        value="0.80"
        valueColorClassName="text-emerald-400"
      />,
    );
    expect(container.querySelector("span.text-emerald-400")).not.toBeNull();
  });

  it("stale overrides valueColorClassName", () => {
    const { container } = render(
      <Chip
        icon={Wind}
        symbol="e"
        value="0.80"
        valueColorClassName="text-emerald-400"
        stale
      />,
    );
    expect(container.querySelector("span.text-red-400")).not.toBeNull();
    expect(container.querySelector("span.text-emerald-400")).toBeNull();
  });

  it("renders tooltip description", () => {
    render(
      <Chip
        icon={Wind}
        symbol="V_md"
        value="13.2"
        description="Minimum-drag speed"
      />,
    );
    expect(screen.getByText("Minimum-drag speed")).toBeInTheDocument();
  });
});
