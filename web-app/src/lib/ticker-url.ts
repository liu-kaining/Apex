/** Static-export-safe ticker detail URL (no per-symbol HTML required). */
export function tickerHref(ticker: string): string {
  const sym = ticker.trim().toUpperCase();
  return `/ticker?t=${encodeURIComponent(sym)}`;
}
