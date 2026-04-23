"use client";

interface AirfoilPreviewProps {
  airfoilName: string;
  onClose?: () => void;
}

const AIRFOIL_UPPER =
  "M 0,0 C 0.01,-0.025 0.05,-0.055 0.1,-0.065 C 0.2,-0.078 0.3,-0.082 0.4,-0.078 C 0.5,-0.07 0.6,-0.058 0.7,-0.043 C 0.8,-0.027 0.9,-0.012 1,0";
const AIRFOIL_LOWER =
  "M 0,0 C 0.01,0.012 0.05,0.028 0.1,0.03 C 0.2,0.032 0.3,0.028 0.4,0.022 C 0.5,0.016 0.6,0.011 0.7,0.007 C 0.8,0.004 0.9,0.001 1,0";

/* Static bar data for CL vs alpha */
const CL_BARS = [
  0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.74, 0.82, 0.90, 0.97, 1.04, 1.08, 0.85,
];

/* Static bar data for CL/CD vs alpha */
const LD_BARS = [
  12, 25, 38, 50, 60, 66, 68.2, 65, 55, 42, 30, 18, 8,
];

const CL_MAX = Math.max(...CL_BARS);
const LD_MAX = Math.max(...LD_BARS);

export function AirfoilPreview({ airfoilName, onClose }: Readonly<AirfoilPreviewProps>) {
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-hidden p-4">
      {/* ── Header Row ── */}
      <div className="flex items-center gap-2">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-foreground">
          Airfoil Preview
        </span>
        <div className="flex-1" />
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-primary">
          {airfoilName}
        </span>

        {/* Re input */}
        <div className="flex items-center gap-1.5">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            Re
          </span>
          <div className="rounded-xl border border-border bg-input px-2 py-1">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
              200k
            </span>
          </div>
        </div>

        {/* Ma input */}
        <div className="flex items-center gap-1.5">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            Ma
          </span>
          <div className="rounded-xl border border-border bg-input px-2 py-1">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-foreground">
              0
            </span>
          </div>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="ml-2 font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-muted-foreground hover:text-foreground"
          >
            Close
          </button>
        )}
      </div>

      {/* ── Geometry Section ── */}
      <div className="flex flex-1 flex-col rounded-xl border border-border bg-card p-4">
        {/* Geometry header */}
        <div className="mb-3 flex items-center gap-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
            Airfoil Geometry &mdash; {airfoilName}
          </span>
          <div className="flex-1" />
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
            t/c = 8.9% &middot; camber = 2.4%
          </span>
        </div>

        {/* SVG airfoil shape */}
        <div className="flex flex-1 items-center justify-center">
          <svg
            viewBox="-0.05 -0.12 1.15 0.22"
            className="h-full w-full max-h-[200px]"
            preserveAspectRatio="xMidYMid meet"
          >
            {/* Chord line (dashed) */}
            <line
              x1="0"
              y1="0"
              x2="1"
              y2="0"
              stroke="currentColor"
              className="text-subtle-foreground"
              strokeWidth="0.002"
              strokeDasharray="0.02 0.01"
            />

            {/* Upper surface */}
            <path
              d={AIRFOIL_UPPER}
              fill="rgba(255, 132, 0, 0.12)"
              stroke="#FF8400"
              strokeWidth="0.004"
              strokeLinejoin="round"
            />

            {/* Lower surface */}
            <path
              d={AIRFOIL_LOWER}
              fill="rgba(255, 132, 0, 0.12)"
              stroke="#FF8400"
              strokeWidth="0.004"
              strokeLinejoin="round"
            />

            {/* Max t/c annotation line */}
            <line
              x1="0.3"
              y1="-0.082"
              x2="0.3"
              y2="0.028"
              stroke="currentColor"
              className="text-muted-foreground"
              strokeWidth="0.0015"
              strokeDasharray="0.008 0.005"
            />
            {/* Max t/c label */}
            <text
              x="0.32"
              y="-0.09"
              className="fill-muted-foreground"
              fontSize="0.022"
              fontFamily="var(--font-jetbrains-mono), monospace"
            >
              max t/c
            </text>
          </svg>
        </div>
      </div>

      {/* ── Polars Section ── */}
      <div className="flex gap-4">
        {/* CL vs alpha */}
        <div className="flex flex-1 flex-col rounded-xl border border-border bg-card p-4">
          <div className="mb-1 flex items-center gap-2">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
              C<sub>L</sub> vs &alpha;
            </span>
            <div className="flex-1" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
              C<sub>L,max</sub> = 1.08 @ 11&deg;
            </span>
          </div>

          {/* Bar chart */}
          <div className="flex flex-1 items-end gap-1 pt-2">
            {CL_BARS.map((val, i) => {
              const heightPct = (val / CL_MAX) * 100;
              const isStall = i === CL_BARS.length - 1;
              return (
                <div
                  key={`cl-${i}-${val}`}
                  className={`flex-1 rounded-t-sm ${isStall ? "bg-destructive" : "bg-primary"}`}
                  style={{ height: `${heightPct}%`, minHeight: 2 }}
                />
              );
            })}
          </div>

          {/* X-axis */}
          <div className="mt-1.5 flex items-center">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
              -10&deg;
            </span>
            <div className="flex-1" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
              0&deg;
            </span>
            <div className="flex-1" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
              10&deg;
            </span>
          </div>
          <div className="mt-0.5 text-center font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-subtle-foreground">
            &alpha; [&deg;]
          </div>
        </div>

        {/* CL/CD vs alpha */}
        <div className="flex flex-1 flex-col rounded-xl border border-border bg-card p-4">
          <div className="mb-1 flex items-center gap-2">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-foreground">
              C<sub>L</sub> / C<sub>D</sub> vs &alpha;
            </span>
            <div className="flex-1" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[10px] text-muted-foreground">
              L/D<sub>max</sub> = 68.2 @ 6&deg;
            </span>
          </div>

          {/* Bar chart */}
          <div className="flex flex-1 items-end gap-1 pt-2">
            {LD_BARS.map((val, i) => {
              const heightPct = (val / LD_MAX) * 100;
              return (
                <div
                  key={`ld-${i}-${val}`}
                  className="flex-1 rounded-t-sm bg-success"
                  style={{ height: `${heightPct}%`, minHeight: 2 }}
                />
              );
            })}
          </div>

          {/* X-axis */}
          <div className="mt-1.5 flex items-center">
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
              -10&deg;
            </span>
            <div className="flex-1" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
              0&deg;
            </span>
            <div className="flex-1" />
            <span className="font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-muted-foreground">
              10&deg;
            </span>
          </div>
          <div className="mt-0.5 text-center font-[family-name:var(--font-jetbrains-mono)] text-[9px] text-subtle-foreground">
            &alpha; [&deg;]
          </div>
        </div>
      </div>
    </div>
  );
}
