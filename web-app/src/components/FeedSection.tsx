"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { SignalFeedCard } from "@/components/SignalFeedCard";
import { FeedFetchError, fetchFeedToday } from "@/lib/feed-api";
import type { FeedToday } from "@/types/feed";
import { formatZhDateTime } from "@/lib/zh";

type LoadState = "loading" | "success" | "error";

export function FeedSection() {
  const [state, setState] = useState<LoadState>("loading");
  const [feed, setFeed] = useState<FeedToday | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const reload = useCallback(() => {
    setReloadKey((k) => k + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setState("loading");
    setErrorMessage(null);

    fetchFeedToday(controller.signal)
      .then((data) => {
        setFeed(data);
        setState("success");
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        const message =
          err instanceof FeedFetchError
            ? err.message
            : err instanceof Error
              ? err.message
              : "无法加载信号";
        setErrorMessage(message);
        setFeed(null);
        setState("error");
      });

    return () => controller.abort();
  }, [reloadKey]);

  if (state === "loading") {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-slate-700/50 bg-card py-20">
        <Loader2 className="h-8 w-8 animate-spin text-sky-400" aria-hidden />
        <p className="text-sm text-zinc-500">正在加载共振信号…</p>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div
        className="rounded-xl border border-red-500/20 bg-red-500/5 p-6"
        role="alert"
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
          <div className="min-w-0 flex-1">
            <p className="font-medium text-zinc-100">无法加载信号流</p>
            <p className="mt-1 text-sm text-zinc-500">{errorMessage}</p>
            <p className="mt-2 text-xs text-zinc-600">
              若提示跨域失败，请在 Cloudflare R2 配置 CORS 并刷新缓存。
            </p>
            <button
              type="button"
              onClick={reload}
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-800/80 px-3 py-2 text-sm text-zinc-200 transition-colors hover:bg-slate-700"
            >
              <RefreshCw className="h-4 w-4" />
              重试
            </button>
          </div>
        </div>
      </div>
    );
  }

  const signals = feed?.signals ?? [];

  return (
    <>
      {feed?.lastUpdated && (
        <p className="mb-4 flex items-center gap-1.5 text-xs text-zinc-500">
          更新于 {formatZhDateTime(feed.lastUpdated)}
          {typeof feed.resonanceMatched === "number" && (
            <span className="text-zinc-600">
              · {feed.resonanceMatched} 条强共振
            </span>
          )}
        </p>
      )}

      <section className="space-y-4" aria-label="今日信号">
        {signals.map((signal) => (
          <SignalFeedCard key={signal.id} signal={signal} />
        ))}
      </section>

      {signals.length === 0 && (
        <p className="rounded-xl border border-dashed border-slate-700/50 py-16 text-center text-sm text-zinc-500">
          今日暂无符合条件的信号，可在收盘后刷新查看。
        </p>
      )}
    </>
  );
}
