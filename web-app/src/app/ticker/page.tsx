"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { TickerTimelineSection } from "@/components/TickerTimelineSection";

function TickerPageInner() {
  const params = useSearchParams();
  const raw = params.get("t") || params.get("symbol") || "";
  const ticker = raw.trim().toUpperCase();

  if (!ticker) {
    return (
      <div className="rounded-xl border border-slate-700/50 bg-slate-900/60 px-6 py-12 text-center">
        <p className="text-zinc-300">请在地址栏使用 ?t=股票代码</p>
        <p className="mt-2 text-sm text-zinc-500">例如 /ticker?t=NFLX</p>
        <Link href="/" className="mt-6 inline-block text-sm text-sky-400 hover:underline">
          返回信号流
        </Link>
      </div>
    );
  }

  return <TickerTimelineSection ticker={ticker} />;
}

export default function TickerQueryPage() {
  return (
    <div className="min-h-screen bg-background">
      <main className="mx-auto max-w-2xl px-4 pb-16 pt-10 sm:px-6">
        <Suspense
          fallback={
            <p className="py-8 text-center text-sm text-zinc-500">加载时间轴…</p>
          }
        >
          <TickerPageInner />
        </Suspense>
      </main>
    </div>
  );
}
