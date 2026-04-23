"use client";

import { createContext, useContext, useState, useCallback, useEffect, useMemo, type ReactNode } from "react";
import { useRouter } from "next/navigation";

interface UnsavedChangesContextValue {
  isDirty: boolean;
  setDirty: (dirty: boolean) => void;
  registerSave: (fn: () => Promise<void>) => void;
  pendingHref: string | null;
  requestNavigation: (href: string) => void;
  confirmDiscard: () => void;
  confirmSave: () => void;
  cancelNavigation: () => void;
  isSaving: boolean;
}

const UnsavedChangesContext = createContext<UnsavedChangesContextValue | null>(null);

export function UnsavedChangesProvider({ children }: Readonly<{ children: ReactNode }>) {
  const router = useRouter();
  const [isDirty, setDirty] = useState(false);
  const [pendingHref, setPendingHref] = useState<string | null>(null);
  const [saveFn, setSaveFn] = useState<(() => Promise<void>) | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const registerSave = useCallback((fn: () => Promise<void>) => {
    setSaveFn(() => fn);
  }, []);

  const requestNavigation = useCallback((href: string) => {
    if (isDirty) {
      setPendingHref(href);
    } else {
      router.push(href);
    }
  }, [isDirty, router]);

  const confirmDiscard = useCallback(() => {
    const href = pendingHref;
    setDirty(false);
    setPendingHref(null);
    if (href) router.push(href);
  }, [pendingHref, router]);

  const confirmSave = useCallback(async () => {
    if (!saveFn) return;
    setIsSaving(true);
    try {
      await saveFn();
      const href = pendingHref;
      setDirty(false);
      setPendingHref(null);
      if (href) router.push(href);
    } finally {
      setIsSaving(false);
    }
  }, [saveFn, pendingHref, router]);

  const cancelNavigation = useCallback(() => {
    setPendingHref(null);
  }, []);

  // Browser beforeunload
  useEffect(() => {
    if (!isDirty) return;
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isDirty]);

  const ctxValue = useMemo(() => ({
    isDirty, setDirty, registerSave, pendingHref,
    requestNavigation, confirmDiscard, confirmSave, cancelNavigation, isSaving,
  }), [isDirty, setDirty, registerSave, pendingHref,
    requestNavigation, confirmDiscard, confirmSave, cancelNavigation, isSaving]);

  return (
    <UnsavedChangesContext.Provider value={ctxValue}>
      {children}
    </UnsavedChangesContext.Provider>
  );
}

export function useUnsavedChanges() {
  const ctx = useContext(UnsavedChangesContext);
  if (!ctx) throw new Error("useUnsavedChanges must be inside UnsavedChangesProvider");
  return ctx;
}
