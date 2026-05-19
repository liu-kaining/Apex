"use client";

import Link from "next/link";
import * as Tooltip from "@radix-ui/react-tooltip";
import type { GridRow } from "@/types/grid";

function heatColor(holderCount: number, totalWeight: number): string {
  const intensity = Math.min(1, holderCount / 12 + totalWeight / 40);
  if (intensity >= 0.7) return "bg-[#8B5CF6] border-[#A78BFA]/40";
  if (intensity >= 0.4) return "bg-[#6D28D9]/80 border-[#8B5CF6]/30";
  if (intensity >= 0.2) return "bg-[#4C1D95]/60 border-white/10";
  return "bg-white/5 border-white/10";
}

function qoqLabel(change: string): string {
  if (change === "NEW") return "New position";
  if (change === "INCREASED") return "Increased";
  if (change === "DECREASED") return "Decreased";
  return "Unchanged";
}

interface HeatmapGridProps {
  rows: GridRow[];
}

export function HeatmapGrid({ rows }: HeatmapGridProps) {
  return (
    <Tooltip.Provider delayDuration={200}>
      <div className="grid grid-cols-4 gap-2 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10">
        {rows.map((row) => (
          <Tooltip.Root key={row.ticker}>
            <Tooltip.Trigger asChild>
              <Link
                href={`/ticker/${row.ticker}`}
                className={`flex aspect-square flex-col items-center justify-center rounded-lg border p-1 text-center transition hover:scale-105 hover:ring-1 hover:ring-[#00FF66]/50 ${heatColor(row.holderCount, row.totalWeight)}`}
              >
                <span className="text-xs font-semibold text-zinc-100">
                  {row.ticker}
                </span>
                <span className="mt-0.5 text-[10px] text-zinc-400">
                  {row.holderCount}
                </span>
              </Link>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                side="top"
                className="z-50 max-w-xs rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-xs text-zinc-200 shadow-xl"
              >
                <p className="font-semibold text-zinc-100">{row.ticker}</p>
                <p className="mt-1 text-zinc-400">
                  {row.holderCount} superinvestor
                  {row.holderCount === 1 ? "" : "s"} · {row.totalWeight.toFixed(1)}%
                  combined weight
                </p>
                <p className="mt-0.5 text-[#00FF66]">{qoqLabel(row.qOqChange)}</p>
                <Tooltip.Arrow className="fill-zinc-900" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        ))}
      </div>
    </Tooltip.Provider>
  );
}
