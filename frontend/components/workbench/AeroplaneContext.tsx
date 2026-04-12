"use client";

import { createContext, useContext, useState, useCallback } from "react";
import type { ReactNode } from "react";

interface AeroplaneContextValue {
  aeroplaneId: string | null;
  selectedWing: string | null;
  selectedXsecIndex: number | null;
  setAeroplaneId: (id: string | null) => void;
  selectWing: (name: string | null) => void;
  selectXsec: (index: number | null) => void;
}

const Ctx = createContext<AeroplaneContextValue | null>(null);

export function AeroplaneProvider({ children }: { children: ReactNode }) {
  const [aeroplaneId, setAeroplaneId] = useState<string | null>(null);
  const [selectedWing, setSelectedWing] = useState<string | null>(null);
  const [selectedXsecIndex, setSelectedXsecIndex] = useState<number | null>(null);

  const selectWing = useCallback((name: string | null) => {
    setSelectedWing(name);
    setSelectedXsecIndex(null);
  }, []);

  const selectXsec = useCallback((index: number | null) => {
    setSelectedXsecIndex(index);
  }, []);

  return (
    <Ctx value={{
      aeroplaneId,
      selectedWing,
      selectedXsecIndex,
      setAeroplaneId,
      selectWing,
      selectXsec,
    }}>
      {children}
    </Ctx>
  );
}

export function useAeroplaneContext(): AeroplaneContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAeroplaneContext must be used within AeroplaneProvider");
  return ctx;
}
