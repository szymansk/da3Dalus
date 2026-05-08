"use client";

import { useState } from "react";
import type { FlightEnvelopeData } from "@/hooks/useFlightEnvelope";
import { PerformanceOverview } from "@/components/workbench/PerformanceOverview";
import { VnDiagram } from "@/components/workbench/VnDiagram";

type View = "performance" | "vn-diagram";

interface Props {
  readonly envelope: FlightEnvelopeData | null;
  readonly isComputing: boolean;
  readonly error: string | null;
  readonly onCompute: () => void;
}

export function EnvelopePanel({ envelope, isComputing, error, onCompute }: Props) {
  const [view, setView] = useState<View>("performance");

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-auto bg-card-muted p-6">
      {/* Toolbar */}
      <div className="flex items-center gap-3">
        {/* Segmented control */}
        <div className="flex rounded-full border border-border bg-card">
          <button
            onClick={() => setView("performance")}
            className={`rounded-full px-3 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] transition-colors ${
              view === "performance"
                ? "bg-[#FF8400] text-white"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Performance
          </button>
          <button
            onClick={() => setView("vn-diagram")}
            className={`rounded-full px-3 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] transition-colors ${
              view === "vn-diagram"
                ? "bg-[#FF8400] text-white"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            V-n Diagram
          </button>
        </div>

        <div className="flex-1" />

        {/* Compute button */}
        <button
          onClick={onCompute}
          disabled={isComputing}
          className="flex items-center gap-1.5 rounded-full bg-[#FF8400] px-4 py-1.5 font-[family-name:var(--font-geist-sans)] text-[12px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isComputing ? "Computing..." : "Compute Envelope"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-red-400">
            {error}
          </span>
        </div>
      )}

      {/* Content */}
      {!envelope && !isComputing && !error && (
        <div className="flex flex-1 flex-col items-center justify-center gap-2">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[14px] text-muted-foreground">
            No envelope data. Click Compute Envelope to generate.
          </span>
        </div>
      )}

      {isComputing && !envelope && (
        <div className="flex flex-1 items-center justify-center">
          <span className="font-[family-name:var(--font-jetbrains-mono)] text-[13px] text-muted-foreground">
            Computing flight envelope...
          </span>
        </div>
      )}

      {envelope && view === "performance" && (
        <PerformanceOverview kpis={envelope.kpis} />
      )}

      {envelope && view === "vn-diagram" && (
        <VnDiagram
          vnCurve={envelope.vn_curve}
          operatingPoints={envelope.operating_points}
        />
      )}
    </div>
  );
}
