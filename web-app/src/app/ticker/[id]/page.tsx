import { TickerTimelineSection } from "@/components/TickerTimelineSection";
import { DATA_API_BASE } from "@/lib/feed-api";

const FALLBACK_TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META"];

export async function generateStaticParams(): Promise<{ id: string }[]> {
  try {
    const res = await fetch(`${DATA_API_BASE}/tickers/index.json`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return FALLBACK_TICKERS.map((id) => ({ id }));
    const data = (await res.json()) as { tickers?: string[] };
    const tickers = Array.isArray(data.tickers) ? data.tickers : [];
    const slice = tickers.slice(0, 300);
    if (!slice.length) return FALLBACK_TICKERS.map((id) => ({ id }));
    return slice.map((id) => ({ id: String(id).toUpperCase() }));
  } catch {
    return FALLBACK_TICKERS.map((id) => ({ id }));
  }
}

export function generateMetadata({ params }: { params: { id: string } }) {
  const ticker = params.id.toUpperCase();
  return {
    title: `Apex — ${ticker} conviction timeline`,
    description: `13F and insider conviction events for ${ticker}.`,
  };
}

export default function TickerPage({ params }: { params: { id: string } }) {
  const ticker = params.id.toUpperCase();
  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <main className="mx-auto max-w-2xl px-4 pb-16 pt-10 sm:px-6">
        <TickerTimelineSection ticker={ticker} />
      </main>
    </div>
  );
}
