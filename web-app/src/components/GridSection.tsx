"use client";

import { useCallback, useEffect, useState } from "react";
import { HeatmapGrid } from "@/components/HeatmapGrid";
import { fetchSp500Grid, FeedFetchError } from "@/lib/data-api";
import type { GridRow } from "@/types/grid";
import { formatZhDateTime } from "@/lib/zh";

export function GridSection() {
  const [rows, setRows] = useState<GridRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSp500Grid(signal);
      setRows(data.grid);
      setLastUpdated(data.lastUpdated);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(
        err instanceof FeedFetchError ? err.message : "无法加载热力图",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (loading) {
    return (
      <p className="py-12 text-center text-sm text-zinc-500">正在加载热力图…</p>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-6 text-center">
        <p className="text-sm text-red-300">{error}</p>
        <button
          type="button"
          onClick={() => void load()}
          className="mt-3 text-sm text-sky-400 underline"
        >
          重试
        </button>
      </div>
    );
  }

  return (
    <>
      {lastUpdated && (
        <p className="mb-4 text-xs text-zinc-500">
          更新于 {formatZhDateTime(lastUpdated)}
        </p>
      )}
      <HeatmapGrid rows={rows} />
    </>
  );
}
