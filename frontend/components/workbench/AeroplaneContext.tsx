"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import type { ReactNode } from "react";

export type TreeMode = "wingconfig" | "asb" | "fuselage";

interface AeroplaneContextValue {
  aeroplaneId: string | null;
  selectedWing: string | null;
  selectedXsecIndex: number | null;
  selectedFuselage: string | null;
  selectedFuselageXsecIndex: number | null;
  treeMode: TreeMode;
  setAeroplaneId: (id: string | null) => void;
  selectWing: (name: string | null) => void;
  selectXsec: (index: number | null) => void;
  selectFuselage: (name: string | null) => void;
  selectFuselageXsec: (index: number | null) => void;
  setTreeMode: (mode: TreeMode) => void;
}

const Ctx = createContext<AeroplaneContextValue | null>(null);

const STORAGE_KEY = "da3dalus_aeroplane_id";

export function AeroplaneProvider({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [aeroplaneId, setAeroplaneIdRaw] = useState<string | null>(null);
  const [selectedWing, setSelectedWing] = useState<string | null>(null);
  const [selectedXsecIndex, setSelectedXsecIndex] = useState<number | null>(null);
  const [selectedFuselage, setSelectedFuselage] = useState<string | null>(null);
  const [selectedFuselageXsecIndex, setSelectedFuselageXsecIndex] = useState<number | null>(null);
  const [treeMode, setTreeMode] = useState<TreeMode>("wingconfig");

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

  return (
    <Ctx
      value={{
        aeroplaneId,
        selectedWing,
        selectedXsecIndex,
        selectedFuselage,
        selectedFuselageXsecIndex,
        treeMode,
        setAeroplaneId,
        selectWing,
        selectXsec,
        selectFuselage,
        selectFuselageXsec,
        setTreeMode,
      }}
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
