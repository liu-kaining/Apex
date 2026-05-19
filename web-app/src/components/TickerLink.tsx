import type { ReactNode } from "react";
import { tickerHref } from "@/lib/ticker-url";

/**
 * Plain anchor — avoids Next.js client navigation fetching /ticker/SYM.txt (RSC)
 * which breaks on GitHub Pages static export.
 */
export function TickerLink({
  ticker,
  className,
  children,
}: {
  ticker: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <a href={tickerHref(ticker)} className={className}>
      {children}
    </a>
  );
}
