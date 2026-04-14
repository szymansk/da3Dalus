import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("react-resizable-panels", () => ({
  Separator: ({ children, className, ...props }: any) => (
    <div data-testid="separator" className={className} {...props}>
      {typeof children === "function" ? children() : children}
    </div>
  ),
}));

vi.mock("lucide-react", () => ({
  ChevronRight: ({ className, ...props }: any) => (
    <svg data-testid="chevron" className={className} {...props} />
  ),
}));

import { SplitHandle } from "@/components/workbench/SplitHandle";

describe("SplitHandle", () => {
  it("renders 3 grip dots", () => {
    const { container } = render(<SplitHandle />);
    const dots = container.querySelectorAll(".rounded-full");
    expect(dots).toHaveLength(3);
  });

  it("renders collapse button when onCollapse provided", () => {
    render(<SplitHandle onCollapse={() => {}} />);
    const button = screen.getByRole("button");
    expect(button).toBeDefined();
  });

  it("does not render collapse button without onCollapse", () => {
    render(<SplitHandle />);
    const button = screen.queryByRole("button");
    expect(button).toBeNull();
  });

  it("chevron has rotate-180 class when collapsed=false", () => {
    render(<SplitHandle onCollapse={() => {}} collapsed={false} />);
    const chevron = screen.getByTestId("chevron");
    expect(chevron.getAttribute("class")).toContain("rotate-180");
  });

  it("calls onCollapse when collapse button is clicked", () => {
    const onCollapse = vi.fn();
    render(<SplitHandle onCollapse={onCollapse} collapsed={false} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onCollapse).toHaveBeenCalledOnce();
  });
});
