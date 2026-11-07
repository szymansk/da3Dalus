import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExpertView } from "@/components/expert/ExpertView";

const useCanonAircraft = vi.fn();
vi.mock("@/hooks/useCanonAircraft", () => ({ useCanonAircraft: () => useCanonAircraft() }));

const FLEET = [
  { id: "bryan", name: "BRYAN", mass_kg: 0.151, flap_deflections: {} },
  { id: "rv-7", name: "RV-7", mass_kg: 0.5, flap_deflections: { "flap-deflection-landing": 30 } },
];

const MINE = "6f1c1a52-8f3c-4a43-9d9a-2c7c4c3b5a10";
const AEROPLANES = [
  { id: MINE, name: "Chekker (plan)", mass_kg: 0.45 },
  { id: "0b7c1a52-8f3c-4a43-9d9a-2c7c4c3b5a11", name: "No mass yet", mass_kg: null },
];

function frameSrc(): URL {
  const frame = screen.getByTitle(/canon navigator/i);
  return new URL(frame.getAttribute("src")!, "http://app.test");
}

function loaded(fleet = FLEET, aeroplanes = AEROPLANES) {
  useCanonAircraft.mockReturnValue({ fleet, aeroplanes, error: undefined, isLoading: false });
}

describe("ExpertView", () => {
  beforeEach(() => loaded());

  it("carries the development label of ADR 0030", () => {
    render(<ExpertView />);
    expect(screen.getByRole("note")).toHaveTextContent(
      "Canon/kernel view (development), experts only",
    );
  });

  it("hosts the connected navigator for the first aircraft of the fleet", () => {
    render(<ExpertView />);
    const src = frameSrc();
    expect(src.pathname).toBe("/canon-navigator.html");
    expect(src.searchParams.get("connected")).toBe("1");
    expect(src.searchParams.get("fleet")).toBe("bryan");
    expect(src.searchParams.get("api")).toMatch(/^https?:\/\//);
    expect(screen.getByText("0.151 kg")).toBeInTheDocument();
  });

  it("offers the fleet and the stored aeroplanes as two groups", () => {
    render(<ExpertView />);
    const fleet = screen.getByRole("group", { name: "Reference fleet" });
    const stored = screen.getByRole("group", { name: "Stored aeroplanes" });
    expect(within(fleet).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "BRYAN",
      "RV-7",
    ]);
    expect(within(stored).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Chekker (plan)",
      "No mass yet",
    ]);
  });

  it("reconnects the navigator to a fleet aircraft on a change", async () => {
    render(<ExpertView />);
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Aircraft" }), "RV-7");
    expect(frameSrc().searchParams.get("fleet")).toBe("rv-7");
    expect(screen.getByText("0.5 kg")).toBeInTheDocument();
  });

  it("connects the navigator to a stored aeroplane by its id, with its mass assumption", async () => {
    render(<ExpertView />);
    const picker = screen.getByRole("combobox", { name: "Aircraft" });
    await userEvent.selectOptions(picker, "Chekker (plan)");
    const src = frameSrc();
    expect(src.searchParams.get("aeroplane")).toBe(MINE);
    expect(src.searchParams.has("fleet")).toBe(false);
    expect(screen.getByText("0.45 kg (mass assumption)")).toBeInTheDocument();
    await userEvent.selectOptions(picker, "No mass yet");
    expect(screen.getByText("mass not set")).toBeInTheDocument();
  });

  it("starts with the first stored aeroplane when there is no fleet", () => {
    loaded([], AEROPLANES);
    render(<ExpertView />);
    expect(frameSrc().searchParams.get("aeroplane")).toBe(MINE);
    expect(screen.queryByRole("group", { name: "Reference fleet" })).toBeNull();
  });

  it("shows no frame while the aircraft load", () => {
    useCanonAircraft.mockReturnValue({ fleet: [], aeroplanes: [], error: undefined, isLoading: true });
    render(<ExpertView />);
    expect(screen.queryByTitle(/canon navigator/i)).toBeNull();
    expect(screen.getByText(/Loading the aircraft/)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Aircraft" })).toBeDisabled();
  });

  it("says when the aircraft cannot be loaded", () => {
    useCanonAircraft.mockReturnValue({
      fleet: [],
      aeroplanes: [],
      error: new Error("503 down"),
      isLoading: false,
    });
    render(<ExpertView />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The aircraft could not be loaded: 503 down",
    );
    expect(screen.queryByTitle(/canon navigator/i)).toBeNull();
  });
});
