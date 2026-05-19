import { FeedSection } from "@/components/FeedSection";
import { Activity, Zap } from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-32 top-0 h-96 w-96 rounded-full bg-[#8B5CF6]/10 blur-3xl" />
        <div className="absolute -right-32 top-1/3 h-80 w-80 rounded-full bg-[#00FF66]/5 blur-3xl" />
      </div>

      <main className="relative mx-auto max-w-2xl px-4 pb-16 pt-12 sm:px-6">
        <header className="mb-10">
          <div className="mb-3 flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/5 backdrop-blur-md">
              <Zap className="h-4 w-4 text-[#00FF66]" strokeWidth={2.5} />
            </span>
            <span className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Apex Signals
            </span>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-100 sm:text-4xl">
            Resonance Feed
          </h1>
          <p className="mt-2 max-w-lg text-sm leading-relaxed text-zinc-400">
            High-conviction overlap between superinvestor 13F holdings and qualifying
            insider open-market buys — noise filtered per Apex Rule 3.
          </p>
          <p className="mt-4 flex items-center gap-1.5 text-xs text-zinc-500">
            <Activity className="h-3.5 w-3.5" />
            Live data from Cloudflare R2
          </p>
        </header>

        <FeedSection />
      </main>
    </div>
  );
}
