import { FeedSection } from "@/components/FeedSection";
import { Activity, Zap } from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <main className="relative mx-auto max-w-2xl px-4 pb-16 pt-12 sm:px-6">
        <header className="mb-10">
          <div className="mb-3 flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700/50 bg-card">
              <Zap className="h-4 w-4 text-sky-400" strokeWidth={2.5} />
            </span>
            <span className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Apex 信号
            </span>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-100 sm:text-4xl">
            共振信号流
          </h1>
          <p className="mt-2 max-w-lg text-sm leading-relaxed text-zinc-500">
            超级投资者 13F 持仓与符合条件的内部人公开市场买入重叠——按 Apex 规则 3 过滤噪音。
          </p>
          <p className="mt-4 flex items-center gap-1.5 text-xs text-zinc-600">
            <Activity className="h-3.5 w-3.5" />
            数据来自 Cloudflare R2
          </p>
        </header>

        <FeedSection />
      </main>
    </div>
  );
}
