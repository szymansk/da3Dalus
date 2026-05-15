import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { MissionToggleGrid } from "@/components/workbench/mission/MissionToggleGrid";
import type { MissionPreset } from "@/hooks/useMissionPresets";

const presets: MissionPreset[] = [
  {
    id: "trainer",
    label: "Trainer",
    description: "",
    target_polygon: {} as Record<string, number>,
    axis_ranges: {} as Record<string, [number, number]>,
    suggested_estimates: {
      g_limit: 4,
      target_static_margin: 0.12,
      cl_max: 1.4,
      power_to_weight: 0.4,
      prop_efficiency: 0.6,
    },
  },
  {
    id: "sport",
    label: "Sport",
    description: "",
    target_polygon: {} as Record<string, number>,
    axis_ranges: {} as Record<string, [number, number]>,
    suggested_estimates: {
      g_limit: 6,
      target_static_margin: 0.1,
      cl_max: 1.3,
      power_to_weight: 0.7,
      prop_efficiency: 0.6,
    },
  },
];

describe("MissionToggleGrid", () => {
  it("disables the active preset button and marks it 'aktiv'", () => {
    render(
      <MissionToggleGrid
        presets={presets}
        activeId="trainer"
        comparisonIds={[]}
        onToggle={() => {}}
      />,
    );
    const trainer = screen.getByRole("button", { name: /Trainer/ });
    expect(trainer).toBeDisabled();
    expect(screen.getByText(/aktiv/)).toBeInTheDocument();
  });

  it("calls onToggle when a non-active preset is clicked", () => {
    const onToggle = vi.fn();
    render(
      <MissionToggleGrid
        presets={presets}
        activeId="trainer"
        comparisonIds={[]}
        onToggle={onToggle}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Sport/ }));
    expect(onToggle).toHaveBeenCalledWith("sport");
  });

  it("highlights comparison presets distinctly from inactive ones", () => {
    render(
      <MissionToggleGrid
        presets={presets}
        activeId="trainer"
        comparisonIds={["sport"]}
        onToggle={() => {}}
      />,
    );
    const sport = screen.getByRole("button", { name: /Sport/ });
    expect(sport.className).toContain("text-sky-400");
  });

  it("does not call onToggle when active preset is clicked", () => {
    const onToggle = vi.fn();
    render(
      <MissionToggleGrid
        presets={presets}
        activeId="trainer"
        comparisonIds={[]}
        onToggle={onToggle}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Trainer/ }));
    expect(onToggle).not.toHaveBeenCalled();
  });
});
