"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { SignalFeedCard } from "@/components/SignalFeedCard";
import { FeedFetchError, fetchFeedToday } from "@/lib/feed-api";
import type { FeedToday } from "@/types/feed";

function formatLastUpdated(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    });
  } catch {
    return iso;
  }
}

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
              : "Unable to load signals";
        setErrorMessage(message);
        setFeed(null);
        setState("error");
      });

    return () => controller.abort();
  }, [reloadKey]);

  if (state === "loading") {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-white/10 bg-white/5 py-20 backdrop-blur-md">
        <Loader2 className="h-8 w-8 animate-spin text-[#8B5CF6]" aria-hidden />
        <p className="text-sm text-zinc-400">Loading resonance feed…</p>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div
        className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 backdrop-blur-md"
        role="alert"
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
          <div className="min-w-0 flex-1">
            <p className="font-medium text-zinc-100">Could not load feed</p>
            <p className="mt-1 text-sm text-zinc-400">{errorMessage}</p>
            <button
              type="button"
              onClick={reload}
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-zinc-200 transition-colors hover:border-zinc-600 hover:bg-zinc-900"
            >
              <RefreshCw className="h-4 w-4" />
              Retry
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
          Updated {formatLastUpdated(feed.lastUpdated)}
          {typeof feed.resonanceMatched === "number" && (
            <span className="text-zinc-600">
              · {feed.resonanceMatched} resonance
              {feed.resonanceMatched === 1 ? "" : "s"}
            </span>
          )}
        </p>
      )}

      <section className="space-y-4" aria-label="Today's signals">
        {signals.map((signal) => (
          <SignalFeedCard key={signal.id} signal={signal} />
        ))}
      </section>

      {signals.length === 0 && (
        <p className="rounded-xl border border-dashed border-white/10 py-16 text-center text-sm text-zinc-500">
          No resonance signals today. Check back after market close.
        </p>
      )}
    </>
  );
}
