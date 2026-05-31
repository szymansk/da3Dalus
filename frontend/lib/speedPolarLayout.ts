/**
 * Speed-polar (Geschwindigkeitspolare) Plotly layout helper (gh-799).
 *
 * Applies the backend-recommended velocity-axis bounds to the chart layout
 * when BOTH are finite numbers; otherwise returns the base layout unchanged so
 * Plotly autoranges. Kept as a pure, dependency-free function so the
 * velocity-range logic is unit-testable without rendering the chart.
 */
export function buildSpeedPolarLayout(
  baseLayout: Record<string, unknown>,
  v_axis_min: number | null | undefined,
  v_axis_max: number | null | undefined,
): Record<string, unknown> {
  const hasBounds =
    typeof v_axis_min === "number" &&
    isFinite(v_axis_min) &&
    typeof v_axis_max === "number" &&
    isFinite(v_axis_max);
  if (!hasBounds) return baseLayout;
  return {
    ...baseLayout,
    xaxis: {
      ...(baseLayout.xaxis as Record<string, unknown>),
      range: [v_axis_min, v_axis_max],
      autorange: false,
    },
  };
}
