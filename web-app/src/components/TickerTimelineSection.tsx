"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
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
          err instanceof FeedFetchError ? err.message : "无法加载时间轴",
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
    return <p className="py-8 text-center text-sm text-zinc-500">加载中…</p>;
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-6 text-center">
        <p className="text-sm text-red-300">{error ?? "未找到该标的"}</p>
        <p className="mt-2 text-xs text-zinc-500">
          可能尚未生成时间轴数据，请等待日频任务更新后重试。
        </p>
        <button
          type="button"
          onClick={() => void load()}
          className="mt-3 text-sm text-sky-400 underline"
        >
          重试
        </button>
        <Link href="/" className="mt-4 block text-sm text-zinc-500 hover:text-zinc-300">
          返回信号流
        </Link>
      </div>
    );
  }

  return (
    <>
      <header className="mb-8">
        <Link href="/" className="text-xs text-zinc-500 hover:text-sky-400">
          ← 返回信号流
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-zinc-100">{data.ticker}</h1>
        <p className="text-sm text-zinc-500">{data.companyName}</p>
      </header>
      <ConvictionTimeline events={data.events} />
    </>
  );
}
