"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
} from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import type { ReactNode } from "react";

import type { ImportOpenVspWarning } from "@/components/workbench/ImportOpenVspButton";

export type TreeMode = "wingconfig" | "asb" | "fuselage";

/**
 * Snapshot of the most recent OpenVSP import (gh-695). Captured by
 * the picker host on a successful upload and consumed by the
 * workbench layout's ``ImportWarningBanner``. Cleared (or replaced)
 * on the next import. Persists in memory only — the banner has its
 * own per-uuid localStorage dismiss flag.
 */
export interface LastImportWarnings {
  uuid: string;
  warnings: ImportOpenVspWarning[];
}

interface AeroplaneContextValue {
  aeroplaneId: string | null;
  hydrated: boolean;
  selectedWing: string | null;
  selectedXsecIndex: number | null;
  selectedFuselage: string | null;
  selectedFuselageXsecIndex: number | null;
  treeMode: TreeMode;
  pickerOpen: boolean;
  lastImportWarnings: LastImportWarnings | null;
  setAeroplaneId: (id: string | null) => void;
  selectWing: (name: string | null) => void;
  selectXsec: (index: number | null) => void;
  selectFuselage: (name: string | null) => void;
  selectFuselageXsec: (index: number | null) => void;
  setTreeMode: (mode: TreeMode) => void;
  openPicker: () => void;
  closePicker: () => void;
  setLastImportWarnings: (value: LastImportWarnings | null) => void;
}

const Ctx = createContext<AeroplaneContextValue | null>(null);

const STORAGE_KEY = "da3dalus_aeroplane_id";

export function AeroplaneProvider({ children }: Readonly<{ children: ReactNode }>) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [aeroplaneId, setAeroplaneIdRaw] = useState<string | null>(null);
  const [selectedWing, setSelectedWing] = useState<string | null>(null);
  const [selectedXsecIndex, setSelectedXsecIndex] = useState<number | null>(null);
  const [selectedFuselage, setSelectedFuselage] = useState<string | null>(null);
  const [selectedFuselageXsecIndex, setSelectedFuselageXsecIndex] = useState<number | null>(null);
  const [treeMode, setTreeMode] = useState<TreeMode>("wingconfig");
  const [hydrated, setHydrated] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [lastImportWarnings, setLastImportWarnings] =
    useState<LastImportWarnings | null>(null);
  const openPicker = useCallback(() => setPickerOpen(true), []);
  const closePicker = useCallback(() => setPickerOpen(false), []);

  const setAeroplaneId = useCallback(
    (id: string | null) => {
      setAeroplaneIdRaw(id);
      if (id) {
        localStorage.setItem(STORAGE_KEY, id);
        const params = new URLSearchParams(searchParams.toString());
        params.set("id", id);
        router.replace(`${pathname}?${params.toString()}`);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    },
    [searchParams, router, pathname],
  );

  useEffect(() => {
    const urlId = searchParams.get("id");
    const storedId = localStorage.getItem(STORAGE_KEY);
    const resolved = urlId ?? storedId ?? null;
    if (resolved) {
      setAeroplaneIdRaw(resolved);
      localStorage.setItem(STORAGE_KEY, resolved);
    }
    setHydrated(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Selecting a wing clears fuselage selection and vice versa
  const selectWing = useCallback((name: string | null) => {
    setSelectedWing(name);
    setSelectedXsecIndex(null);
    if (name) {
      // Clear fuselage xsec selection but keep selectedFuselage for tree expand
      setSelectedFuselageXsecIndex(null);
      setTreeMode((m) => m === "fuselage" ? "wingconfig" : m);
    }
  }, []);

  const selectXsec = useCallback((index: number | null) => {
    setSelectedXsecIndex(index);
  }, []);

  const selectFuselage = useCallback((name: string | null) => {
    setSelectedFuselage(name);
    setSelectedFuselageXsecIndex(null);
    if (name) {
      // Clear wing xsec selection (PropertyForm switches to fuselage mode)
      // but keep selectedWing so the tree can still show expanded wing data
      setSelectedXsecIndex(null);
      setTreeMode("fuselage");
    }
  }, []);

  const selectFuselageXsec = useCallback((index: number | null) => {
    setSelectedFuselageXsecIndex(index);
  }, []);

  const ctxValue = useMemo(() => ({
    aeroplaneId,
    hydrated,
    selectedWing,
    selectedXsecIndex,
    selectedFuselage,
    selectedFuselageXsecIndex,
    treeMode,
    pickerOpen,
    lastImportWarnings,
    setAeroplaneId,
    selectWing,
    selectXsec,
    selectFuselage,
    selectFuselageXsec,
    setTreeMode,
    openPicker,
    closePicker,
    setLastImportWarnings,
  }), [
    aeroplaneId,
    hydrated,
    selectedWing,
    selectedXsecIndex,
    selectedFuselage,
    selectedFuselageXsecIndex,
    treeMode,
    pickerOpen,
    lastImportWarnings,
    setAeroplaneId,
    selectWing,
    selectXsec,
    selectFuselage,
    selectFuselageXsec,
    setTreeMode,
    openPicker,
    closePicker,
  ]);

  return (
    <Ctx
      value={ctxValue}
    >
      {children}
    </Ctx>
  );
}

export function useAeroplaneContext(): AeroplaneContextValue {
  const ctx = useContext(Ctx);
  if (!ctx)
    throw new Error(
      "useAeroplaneContext must be used within AeroplaneProvider",
    );
  return ctx;
}
