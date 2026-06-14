import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/components/workbench/AeroplaneContext", () => ({
  useAeroplaneContext: vi.fn(),
}));
vi.mock("@/components/workbench/PowertrainTab", () => ({
  PowertrainTab: ({ aeroplaneId }: { aeroplaneId: string }) => (
    <div data-testid="powertrain-tab">{aeroplaneId}</div>
  ),
}));

import { useAeroplaneContext } from "@/components/workbench/AeroplaneContext";
import PowertrainPage from "@/app/workbench/powertrain/page";

const mockCtx = useAeroplaneContext as unknown as ReturnType<typeof vi.fn>;

describe("PowertrainPage — top-level workbench tab", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the PowertrainTab for the selected aeroplane", () => {
    mockCtx.mockReturnValue({ aeroplaneId: "aero-42" });
    render(<PowertrainPage />);
    expect(screen.getByTestId("powertrain-tab")).toHaveTextContent("aero-42");
  });

  it("shows a placeholder when no aeroplane is selected", () => {
    mockCtx.mockReturnValue({ aeroplaneId: null });
    render(<PowertrainPage />);
    expect(screen.getByText(/No aeroplane selected/i)).toBeInTheDocument();
    expect(screen.queryByTestId("powertrain-tab")).toBeNull();
  });
});
