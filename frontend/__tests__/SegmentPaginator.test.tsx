import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", { ...props, "data-testid": props["data-testid"] || "icon" });
  return { ChevronLeft: icon, ChevronRight: icon };
});

import { SegmentPaginator } from "@/components/workbench/SegmentPaginator";

describe("SegmentPaginator", () => {
  const onChange = vi.fn<(n: number) => Promise<void>>().mockResolvedValue(undefined);

  beforeEach(() => vi.clearAllMocks());

  describe("few segments (total <= 5)", () => {
    it("renders all indices for total=4", () => {
      render(<SegmentPaginator current={0} total={4} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "1" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "2" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "3" })).toBeInTheDocument();
      expect(screen.queryByText("…")).not.toBeInTheDocument();
    });

    it("renders single index for total=1", () => {
      render(<SegmentPaginator current={0} total={1} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
    });
  });

  describe("many segments (total > 5) — ellipsis", () => {
    it("current=0: shows 0 1 … 10", () => {
      render(<SegmentPaginator current={0} total={11} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "1" })).toBeInTheDocument();
      expect(screen.getByText("…")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "2" })).not.toBeInTheDocument();
    });

    it("current=5: shows 0 … 4 5 6 … 10", () => {
      render(<SegmentPaginator current={5} total={11} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "4" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "5" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "6" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
      expect(screen.getAllByText("…")).toHaveLength(2);
    });

    it("current=10: shows 0 … 9 10", () => {
      render(<SegmentPaginator current={10} total={11} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "9" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
      expect(screen.getAllByText("…")).toHaveLength(1);
    });

    it("current=1: shows 0 1 2 … 10", () => {
      render(<SegmentPaginator current={1} total={11} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "1" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "2" })).toBeInTheDocument();
      expect(screen.getAllByText("…")).toHaveLength(1);
      expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
    });

    it("current=9: shows 0 … 8 9 10", () => {
      render(<SegmentPaginator current={9} total={11} onChange={onChange} />);
      expect(screen.getByRole("button", { name: "0" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "8" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "9" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
      expect(screen.getAllByText("…")).toHaveLength(1);
    });
  });

  describe("current highlight", () => {
    it("highlights current index with accent style", () => {
      render(<SegmentPaginator current={2} total={4} onChange={onChange} />);
      const btn = screen.getByRole("button", { name: "2" });
      expect(btn.className).toMatch(/bg-primary/);
    });
  });

  describe("arrow buttons", () => {
    it("prev arrow disabled at index 0", () => {
      render(<SegmentPaginator current={0} total={4} onChange={onChange} />);
      const prev = screen.getByLabelText("Previous segment");
      expect(prev).toBeDisabled();
    });

    it("next arrow disabled at last index", () => {
      render(<SegmentPaginator current={3} total={4} onChange={onChange} />);
      const next = screen.getByLabelText("Next segment");
      expect(next).toBeDisabled();
    });

    it("prev arrow calls onChange(current - 1)", async () => {
      render(<SegmentPaginator current={2} total={4} onChange={onChange} />);
      await act(async () => {
        fireEvent.click(screen.getByLabelText("Previous segment"));
      });
      expect(onChange).toHaveBeenCalledWith(1);
    });

    it("next arrow calls onChange(current + 1)", async () => {
      render(<SegmentPaginator current={1} total={4} onChange={onChange} />);
      await act(async () => {
        fireEvent.click(screen.getByLabelText("Next segment"));
      });
      expect(onChange).toHaveBeenCalledWith(2);
    });
  });

  describe("index click", () => {
    it("calls onChange with clicked index", async () => {
      render(<SegmentPaginator current={0} total={4} onChange={onChange} />);
      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: "3" }));
      });
      expect(onChange).toHaveBeenCalledWith(3);
    });

    it("does not call onChange when clicking current index", async () => {
      render(<SegmentPaginator current={2} total={4} onChange={onChange} />);
      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: "2" }));
      });
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe("disabled states", () => {
    it("all buttons disabled when disabled prop is true", () => {
      render(<SegmentPaginator current={1} total={4} onChange={onChange} disabled />);
      const buttons = screen.getAllByRole("button");
      buttons.forEach((btn) => expect(btn).toBeDisabled());
    });

    it("all buttons disabled while onChange is in flight", async () => {
      let resolveOnChange: () => void;
      const slowChange = vi.fn<(n: number) => Promise<void>>(
        () => new Promise((r) => { resolveOnChange = r; }),
      );
      render(<SegmentPaginator current={1} total={4} onChange={slowChange} />);

      await act(async () => {
        fireEvent.click(screen.getByLabelText("Next segment"));
      });

      const buttons = screen.getAllByRole("button");
      buttons.forEach((btn) => expect(btn).toBeDisabled());

      await act(async () => { resolveOnChange!(); });

      expect(screen.getByLabelText("Next segment")).not.toBeDisabled();
    });
  });
});
