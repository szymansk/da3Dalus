/**
 * Types of the OpenVSP `.vsp3` import (gh-646, gh-737), shared by the import
 * button, its progress bar, the scale inputs and the warning banner. They live
 * here so the components do not import each other (gh-1366).
 */
export type ImportOpenVspWarning = {
  component_type: string;
  component_name: string;
  reason: string;
  severity: "info" | "warning" | "error";
};

export type ImportOpenVspResponse = {
  aeroplane_uuid: string;
  aeroplane_name: string;
  n_wings: number;
  n_fuselages: number;
  n_weight_items: number;
  warnings: ImportOpenVspWarning[];
  lossy_components: string[];
};

/**
 * Optional scaling instruction for the import request.
 *
 * - ``none``        — import as-is, no rescale.
 * - ``target_span`` — rescale to the requested wingspan in metres.
 * - ``scale_factor``— multiply all length-typed fields by the factor.
 *
 * Both ``target_span_m`` and ``scale_factor`` are validated server-side
 * (out-of-range → 422). The UI should also enforce reasonable bounds
 * to prevent obvious mistakes.
 */
export type ScaleOption =
  | { mode: "none" }
  | { mode: "target_span"; target_span_m: number }
  | { mode: "scale_factor"; scale_factor: number };
