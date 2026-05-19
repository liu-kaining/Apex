import { GridSection } from "@/components/GridSection";
import { Grid3X3 } from "lucide-react";

export const metadata = {
  title: "Apex — Superinvestor Heatmap",
  description: "S&P conviction heatmap from aggregated 13F holdings (Rule 2).",
};

export default function GridPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <main className="mx-auto max-w-5xl px-4 pb-16 pt-10 sm:px-6">
        <header className="mb-8">
          <div className="mb-2 flex items-center gap-2 text-zinc-500">
            <Grid3X3 className="h-4 w-4 text-[#8B5CF6]" />
            <span className="text-xs uppercase tracking-widest">Rule 2 filter</span>
          </div>
          <h1 className="text-3xl font-semibold text-zinc-100">Conviction Heatmap</h1>
          <p className="mt-2 max-w-xl text-sm text-zinc-400">
            Tickers held by superinvestors with &gt;1% portfolio weight or meaningful
            QoQ change. Click a cell for the conviction timeline.
          </p>
        </header>
        <GridSection />
      </main>
    </div>
  );
}
