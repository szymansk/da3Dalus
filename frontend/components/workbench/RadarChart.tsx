interface RadarChartAxis {
  key: string;
  label: string;
}

interface RadarChartProps {
  axes: RadarChartAxis[];
  target: Record<string, number>;
  analysis?: Record<string, number> | null;
  size?: number;
}

export function polarToCartesian(
  cx: number,
  cy: number,
  r: number,
  angle: number,
): { x: number; y: number } {
  return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
}

export function buildPolygonPoints(
  cx: number,
  cy: number,
  R: number,
  values: number[],
  angles: number[],
): string {
  return values
    .map((v, i) => {
      const pt = polarToCartesian(cx, cy, R * v, angles[i]);
      return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`;
    })
    .join(" ");
}

export function RadarChart({
  axes,
  target,
  analysis = null,
  size = 420,
}: Readonly<RadarChartProps>) {
  const height = Math.round(size * 0.81);
  const cx = size / 2;
  const cy = height / 2;
  const R = Math.min(size, height) * 0.35;
  const n = axes.length;
  const angles = axes.map((_, i) => -Math.PI / 2 + (2 * Math.PI * i) / n);
  const levels = [0.33, 0.67, 1.0];

  const targetValues = axes.map((a) => target[a.key] ?? 0);
  const analysisValues = analysis
    ? axes.map((a) => analysis[a.key] ?? 0)
    : null;

  return (
    <svg
      data-testid="radar-chart"
      viewBox={`0 0 ${size} ${height}`}
      className="h-full w-full"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Grid: concentric pentagons */}
      {levels.map((lv) => (
        <polygon
          key={`grid-${lv}`}
          data-testid="grid-ring"
          points={buildPolygonPoints(
            cx, cy, R * lv, Array(n).fill(1), angles,
          )}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth="1"
        />
      ))}

      {/* Grid: axis spokes */}
      {angles.map((angle, i) => {
        const outer = polarToCartesian(cx, cy, R, angle);
        return (
          <line
            key={`spoke-${i}`}
            x1={cx} y1={cy} x2={outer.x} y2={outer.y}
            stroke="var(--color-border)" strokeWidth="1"
          />
        );
      })}

      {/* Target polygon */}
      <polygon
        data-testid="target-polygon"
        points={buildPolygonPoints(cx, cy, R, targetValues, angles)}
        fill="#FF840030"
        stroke="var(--color-primary)"
        strokeWidth="2"
      />

      {/* Analysis polygon */}
      {analysisValues && (
        <polygon
          data-testid="analysis-polygon"
          points={buildPolygonPoints(cx, cy, R, analysisValues, angles)}
          fill="#30A46C30"
          stroke="var(--color-success)"
          strokeWidth="2"
        />
      )}

      {/* Axis labels */}
      {axes.map((axis, i) => {
        const labelR = R + 25;
        const pt = polarToCartesian(cx, cy, labelR, angles[i]);
        const cosA = Math.cos(angles[i]);
        let anchor: "middle" | "start" | "end" = "middle";
        if (cosA > 0.3) anchor = "start";
        else if (cosA < -0.3) anchor = "end";

        return (
          <text
            key={axis.key}
            x={pt.x} y={pt.y + 4}
            textAnchor={anchor}
            fontSize="11"
            fill="var(--color-muted-foreground)"
            fontFamily="var(--font-geist-sans)"
          >
            {axis.label}
          </text>
        );
      })}
    </svg>
  );
}
