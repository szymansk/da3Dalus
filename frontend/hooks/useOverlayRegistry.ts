"use client";

import { useCallback, useMemo, useRef, useState } from "react";

export type PlotlyTrace = Record<string, unknown>;

export interface UseOverlayRegistryReturn {
  /** Flat list of all registered traces, in key-insertion order. */
  traces: PlotlyTrace[];
  /** Returns a stable setter that publishes (or clears) the traces for `key`.
   *  Calling with [] removes the key entirely. Calling with the same key
   *  again replaces the previously-published traces. The returned setter
   *  is referentially stable across renders. */
  register: (key: string) => (next: PlotlyTrace[]) => void;
}

interface RegistryState {
  /** Traces keyed by registration key. */
  byKey: Record<string, PlotlyTrace[]>;
  /** Insertion order of keys with non-empty traces. */
  order: string[];
}

const EMPTY_STATE: RegistryState = { byKey: {}, order: [] };

function applyUpdate(
  prev: RegistryState,
  key: string,
  next: PlotlyTrace[],
): RegistryState {
  if (next.length === 0) {
    if (!(key in prev.byKey)) return prev;
    const byKey = { ...prev.byKey };
    delete byKey[key];
    return { byKey, order: prev.order.filter((k) => k !== key) };
  }
  const order = prev.order.includes(key) ? prev.order : [...prev.order, key];
  return { byKey: { ...prev.byKey, [key]: next }, order };
}

/**
 * Composable overlay registry for the workbench Plotly preview.
 *
 * Each overlay component (e.g. StabilityOverlay) holds a stable
 * `register(key)` setter; calling it with a non-empty array publishes
 * those traces into the registry. Calling with an empty array removes
 * the key entirely. The flat `traces` array is fed to
 * `<WingOutlineViewer extraTraces={...}/>` (gh-569).
 *
 * Order of traces follows the order in which keys were first registered.
 * Removing then re-registering a key moves it to the end.
 */
export function useOverlayRegistry(): UseOverlayRegistryReturn {
  const [state, setState] = useState<RegistryState>(EMPTY_STATE);
  // Stable setter cache, memoised per key. Held in a ref so identical
  // calls to register(key) return the exact same function reference,
  // letting consumers use it safely in useEffect deps.
  const setterRef = useRef<Record<string, (next: PlotlyTrace[]) => void>>({});

  const register = useCallback((key: string) => {
    let setter = setterRef.current[key];
    if (!setter) {
      setter = (next: PlotlyTrace[]) =>
        setState((prev) => applyUpdate(prev, key, next));
      setterRef.current[key] = setter;
    }
    return setter;
  }, []);

  const traces = useMemo<PlotlyTrace[]>(
    () => state.order.flatMap((k) => state.byKey[k] ?? []),
    [state],
  );

  return { traces, register };
}
