"use client";

import * as Tooltip from "@radix-ui/react-tooltip";
import type { GridRow } from "@/types/grid";
import { TickerLink } from "@/components/TickerLink";
import { qoqLabelZh } from "@/lib/zh";

function heatColor(holderCount: number, totalWeight: number): string {
  const intensity = Math.min(1, holderCount / 10 + totalWeight / 35);
  if (intensity >= 0.65) return "bg-indigo-500/90 border-indigo-400/40 text-white";
  if (intensity >= 0.35) return "bg-sky-600/70 border-sky-500/30 text-zinc-100";
  if (intensity >= 0.15) return "bg-slate-700/80 border-slate-600/40 text-zinc-300";
  return "bg-slate-800/50 border-slate-700/50 text-zinc-500";
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
              <TickerLink
                ticker={row.ticker}
                className={`flex aspect-square flex-col items-center justify-center rounded-lg border p-1 text-center transition hover:scale-[1.03] hover:ring-2 hover:ring-sky-400/40 ${heatColor(row.holderCount, row.totalWeight)}`}
              >
                <span className="text-[11px] font-semibold leading-tight">
                  {row.ticker}
                </span>
                <span className="mt-0.5 text-[10px] opacity-80">
                  {row.holderCount} 家
                </span>
              </TickerLink>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                side="top"
                className="z-50 max-w-xs rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-xs text-zinc-200 shadow-xl"
              >
                <p className="font-semibold text-zinc-100">{row.ticker}</p>
                <p className="mt-1 text-zinc-400">
                  {row.holderCount} 位超级投资者持仓 · 合计权重{" "}
                  {row.totalWeight.toFixed(1)}%
                </p>
                <p className="mt-0.5 text-sky-300">{qoqLabelZh(row.qOqChange)}</p>
                <Tooltip.Arrow className="fill-slate-900" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        ))}
      </div>
    </Tooltip.Provider>
  );
}
