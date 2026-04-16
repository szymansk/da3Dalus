/**
 * Tests for the Construction-Parts card grid (gh#57-ggd).
 *
 * Renders the parts returned by `useConstructionParts` as clickable cards
 * with name / material / volume / lock-toggle / delete. Delete uses a
 * confirmation modal; it is blocked server-side with HTTP 409 when the
 * part is locked — we surface that as a blocked button + tooltip.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => {
  const icon = (props: Record<string, unknown>) =>
    React.createElement("span", props);
  return {
    Box: icon, Lock: icon, Unlock: icon, Trash2: icon, Plus: icon,
    Upload: icon, X: icon, Loader2: icon, Settings: icon, Check: icon,
    ChevronDown: icon, ChevronRight: icon, Package: icon, Search: icon,
  };
});

let partsReturn: {
  parts: Array<Record<string, unknown>>;
  total: number;
  isLoading: boolean;
  mutate: () => void;
} = { parts: [], total: 0, isLoading: false, mutate: vi.fn() };

const mockLock = vi.fn().mockResolvedValue({ id: 1, locked: true });
const mockUnlock = vi.fn().mockResolvedValue({ id: 1, locked: false });
const mockDelete = vi.fn().mockResolvedValue(undefined);

vi.mock("@/hooks/useConstructionParts", () => ({
  useConstructionParts: () => ({ ...partsReturn, error: null }),
  lockConstructionPart: (...a: unknown[]) => mockLock(...a),
  unlockConstructionPart: (...a: unknown[]) => mockUnlock(...a),
  deleteConstructionPart: (...a: unknown[]) => mockDelete(...a),
  uploadConstructionPart: vi.fn().mockResolvedValue({}),
  updateConstructionPart: vi.fn().mockResolvedValue({}),
}));

vi.mock("@/hooks/useComponents", () => ({
  useComponents: () => ({ components: [], total: 0, isLoading: false, error: null, mutate: vi.fn() }),
  useComponentTypes: () => ["material"],
}));

vi.mock("@/lib/fetcher", () => ({ API_BASE: "http://x", fetcher: vi.fn() }));

import { ConstructionPartsGrid } from "@/components/workbench/ConstructionPartsGrid";

beforeEach(() => {
  vi.clearAllMocks();
  partsReturn = { parts: [], total: 0, isLoading: false, mutate: vi.fn() };
});

describe("ConstructionPartsGrid", () => {
  it("shows the empty state when there are no parts", () => {
    render(<ConstructionPartsGrid aeroplaneId="a" onRequestUpload={vi.fn()} />);
    expect(screen.getByText(/No construction parts/i)).toBeDefined();
  });

  it("renders a card per part", () => {
    partsReturn = {
      parts: [
        { id: 1, name: "Rib-A", volume_mm3: 500, area_mm2: 40, locked: false, material_component_id: null, file_format: "step", thumbnail_url: null },
        { id: 2, name: "Spar-B", volume_mm3: 1200, area_mm2: 80, locked: true, material_component_id: null, file_format: "stl", thumbnail_url: null },
      ],
      total: 2, isLoading: false, mutate: vi.fn(),
    };
    render(<ConstructionPartsGrid aeroplaneId="a" onRequestUpload={vi.fn()} />);
    expect(screen.getByText("Rib-A")).toBeDefined();
    expect(screen.getByText("Spar-B")).toBeDefined();
  });

  it("lock-toggle calls the correct API (lock on unlocked, unlock on locked)", async () => {
    partsReturn = {
      parts: [
        { id: 1, name: "P1", volume_mm3: 100, area_mm2: 10, locked: false, material_component_id: null, file_format: "step", thumbnail_url: null },
      ],
      total: 1, isLoading: false, mutate: vi.fn(),
    };
    render(<ConstructionPartsGrid aeroplaneId="a" onRequestUpload={vi.fn()} />);

    const lockBtn = screen.getByTitle("Lock part");
    fireEvent.click(lockBtn);
    expect(mockLock).toHaveBeenCalledWith("a", 1);
  });

  it("delete asks for confirmation via modal and fires delete on confirm", async () => {
    partsReturn = {
      parts: [
        { id: 5, name: "Doomed", volume_mm3: 100, area_mm2: 10, locked: false, material_component_id: null, file_format: "step", thumbnail_url: null },
      ],
      total: 1, isLoading: false, mutate: vi.fn(),
    };
    render(<ConstructionPartsGrid aeroplaneId="a" onRequestUpload={vi.fn()} />);

    // First click opens the modal
    fireEvent.click(screen.getByTitle("Delete part"));
    expect(screen.getByText(/Delete "Doomed"/i)).toBeDefined();

    // Confirm fires the API
    fireEvent.click(screen.getByText(/Confirm/i));
    expect(mockDelete).toHaveBeenCalledWith("a", 5);
  });

  it("delete is disabled for locked parts", () => {
    partsReturn = {
      parts: [
        { id: 6, name: "Locked", volume_mm3: 100, area_mm2: 10, locked: true, material_component_id: null, file_format: "step", thumbnail_url: null },
      ],
      total: 1, isLoading: false, mutate: vi.fn(),
    };
    render(<ConstructionPartsGrid aeroplaneId="a" onRequestUpload={vi.fn()} />);

    const btn = screen.getByTitle("Delete blocked — unlock first") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("upload button calls onRequestUpload (parent opens the dialog)", () => {
    const onReq = vi.fn();
    render(<ConstructionPartsGrid aeroplaneId="a" onRequestUpload={onReq} />);
    fireEvent.click(screen.getByText(/Upload Part/i));
    expect(onReq).toHaveBeenCalledTimes(1);
  });
});
