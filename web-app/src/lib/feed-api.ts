import type { FeedToday } from "@/types/feed";

/** Public R2 / CDN base URL (no trailing slash). Objects live under /v1/ */
export const DATA_API_BASE =
  process.env.NEXT_PUBLIC_DATA_API_URL?.replace(/\/$/, "") ||
  "https://apex-data.thetamind.ai/v1";

export function feedTodayUrl(): string {
  return `${DATA_API_BASE}/feed_today.json`;
}

export class FeedFetchError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "FeedFetchError";
  }
}

export async function fetchFeedToday(
  signal?: AbortSignal,
): Promise<FeedToday> {
  const url = feedTodayUrl();
  let response: Response;

  try {
    response = await fetch(url, {
      method: "GET",
      signal,
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }
    throw new FeedFetchError(
      err instanceof Error ? err.message : "Network request failed",
    );
  }

  if (!response.ok) {
    throw new FeedFetchError(
      `Failed to load feed (${response.status} ${response.statusText})`,
      response.status,
    );
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new FeedFetchError("Invalid JSON in feed response");
  }

  if (!payload || typeof payload !== "object") {
    throw new FeedFetchError("Unexpected feed payload shape");
  }

  const data = payload as Record<string, unknown>;
  if (!Array.isArray(data.signals)) {
    throw new FeedFetchError("Feed is missing a signals array");
  }

  const signals = data.signals.filter((item): item is FeedToday["signals"][number] => {
    if (!item || typeof item !== "object") return false;
    const row = item as Record<string, unknown>;
    return (
      typeof row.id === "string" &&
      typeof row.ticker === "string" &&
      typeof row.companyName === "string" &&
      row.insiderActions !== null &&
      typeof row.insiderActions === "object"
    );
  });

  return {
    lastUpdated:
      typeof data.lastUpdated === "string"
        ? data.lastUpdated
        : new Date().toISOString(),
    signals,
    resonanceMatched:
      typeof data.resonanceMatched === "number"
        ? data.resonanceMatched
        : undefined,
  };
}
