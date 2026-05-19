"use client";

import { useCallback, useEffect, useState } from "react";
import { ConvictionTimeline } from "@/components/ConvictionTimeline";
import { fetchTickerTimeline, FeedFetchError } from "@/lib/data-api";
import type { TickerTimeline } from "@/types/timeline";

interface TickerTimelineSectionProps {
  ticker: string;
}

export function TickerTimelineSection({ ticker }: TickerTimelineSectionProps) {
  const [data, setData] = useState<TickerTimeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        setData(await fetchTickerTimeline(ticker, signal));
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(
          err instanceof FeedFetchError ? err.message : "Failed to load timeline",
        );
      } finally {
        setLoading(false);
      }
    },
    [ticker],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (loading) {
    return <p className="py-8 text-center text-sm text-zinc-500">Loading…</p>;
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-6 text-center">
        <p className="text-sm text-red-300">{error ?? "Not found"}</p>
        <button
          type="button"
          onClick={() => void load()}
          className="mt-3 text-sm text-[#00FF66] underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <>
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-zinc-100">{data.ticker}</h1>
        <p className="text-sm text-zinc-400">{data.companyName}</p>
      </header>
      <ConvictionTimeline events={data.events} />
    </>
  );
}
