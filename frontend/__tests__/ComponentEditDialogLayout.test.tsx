/**
 * Regression tests for the ComponentEditDialog layout (gh#84 follow-up).
 *
 * Reported 2026-04-16: a user-created component type with a very long
 * name (~60 chars of random-looking string) made the Type <select>
 * grow to the width of that option, pushing the Mass field out of the
 * modal. Root cause: without `min-w-0` on the flex items and `w-full`
 * on the controls, a <select> sizes to its longest option.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return { X: icon, Loader2: icon };
});

vi.mock("@/hooks/useComponents", () => ({
  createComponent: vi.fn(),
  updateComponent: vi.fn(),
}));

vi.mock("@/hooks/useComponentTypes", () => ({
  useComponentTypes: () => ({
    types: [
      { id: 1, name: "generic", label: "Generic", description: null, schema: [], deletable: false, reference_count: 0, created_at: "", updated_at: "" },
      { id: 2, name: "servo", label: "Servo", description: null, schema: [], deletable: false, reference_count: 0, created_at: "", updated_at: "" },
      // User-added type with an absurdly long label — exactly what
      // broke the layout in the reported screenshot.
      { id: 99, name: "u2bwxy4wok1geb0tag6vl2jxesoblmw84hffy6b274s7kztftgdibouh5cjd6r11lal8re9sueczvwy_qa1r7nqx", label: "u2bwxy4wok1geb0tag6vl2jxesoblmw84hffy6b274s7kztftgdibouh5cjd6r11lal8re9sueczvwy_qa1r7nqx", description: null, schema: [], deletable: true, reference_count: 0, created_at: "", updated_at: "" },
    ],
    isLoading: false, mutate: vi.fn(), error: null,
  }),
}));

vi.mock("@/lib/fetcher", () => ({ API_BASE: "http://x", fetcher: vi.fn() }));

import { ComponentEditDialog } from "@/components/workbench/ComponentEditDialog";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ComponentEditDialog — Type/Mass row layout", () => {
  it("Type <select> wrapper has min-w-0 so it can shrink below the longest option", () => {
    const { container } = render(
      <ComponentEditDialog open={true} onClose={vi.fn()} onSaved={vi.fn()} component={null} />,
    );
    const select = container.querySelector("select") as HTMLSelectElement;
    expect(select).not.toBeNull();
    // The flex wrapper around the select must allow shrinking
    const wrapper = select.closest("div") as HTMLElement;
    expect(wrapper.className).toMatch(/min-w-0/);
    // The select itself carries w-full so its parent drives its width
    expect(select.className).toMatch(/w-full/);
  });

  it("Mass (g) input wrapper has the same fix so the row is symmetric", () => {
    const { container } = render(
      <ComponentEditDialog open={true} onClose={vi.fn()} onSaved={vi.fn()} component={null} />,
    );
    const massInput = container.querySelector('input[type="number"]') as HTMLInputElement;
    expect(massInput).not.toBeNull();
    const wrapper = massInput.closest("div") as HTMLElement;
    expect(wrapper.className).toMatch(/min-w-0/);
    expect(massInput.className).toMatch(/w-full/);
  });
});
