import { DATA_API_BASE, FeedFetchError } from "@/lib/feed-api";
import type { FeedToday } from "@/types/feed";
import type { Sp500Grid } from "@/types/grid";
import type { TickerIndex, TickerTimeline } from "@/types/timeline";

export { DATA_API_BASE, FeedFetchError, fetchFeedToday } from "@/lib/feed-api";

async function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const url = `${DATA_API_BASE}/${path.replace(/^\//, "")}`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      signal,
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new FeedFetchError(
      err instanceof Error ? err.message : "Network request failed",
    );
  }
  if (!response.ok) {
    throw new FeedFetchError(
      `Failed to load ${path} (${response.status})`,
      response.status,
    );
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new FeedFetchError(`Invalid JSON at ${path}`);
  }
}

export async function fetchSp500Grid(signal?: AbortSignal): Promise<Sp500Grid> {
  const data = await fetchJson<Sp500Grid>("sp500_grid.json", signal);
  if (!data || !Array.isArray(data.grid)) {
    throw new FeedFetchError("Grid payload missing grid array");
  }
  return {
    lastUpdated: data.lastUpdated ?? new Date().toISOString(),
    sourcePortfolios: data.sourcePortfolios,
    grid: data.grid.filter(
      (row) => row && typeof row.ticker === "string",
    ),
  };
}

export async function fetchTickerIndex(signal?: AbortSignal): Promise<TickerIndex> {
  const data = await fetchJson<TickerIndex>("tickers/index.json", signal);
  return {
    lastUpdated: data.lastUpdated ?? new Date().toISOString(),
    tickers: Array.isArray(data.tickers) ? data.tickers : [],
  };
}

export async function fetchTickerTimeline(
  ticker: string,
  signal?: AbortSignal,
): Promise<TickerTimeline> {
  const id = ticker.toUpperCase().trim();
  const data = await fetchJson<TickerTimeline>(`tickers/${id}.json`, signal);
  if (!data?.ticker) {
    throw new FeedFetchError(`Timeline not found for ${id}`, 404);
  }
  return {
    ticker: data.ticker,
    companyName: data.companyName ?? id,
    lastUpdated: data.lastUpdated ?? new Date().toISOString(),
    events: Array.isArray(data.events) ? data.events : [],
  };
}

export type { FeedToday };
