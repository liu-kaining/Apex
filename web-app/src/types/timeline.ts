export interface TimelineEvent {
  date: string;
  type: "13F" | "INSIDER" | string;
  icon: string;
  title: string;
  description: string;
  meta?: Record<string, unknown>;
}

export interface TickerTimeline {
  ticker: string;
  companyName: string;
  lastUpdated: string;
  events: TimelineEvent[];
}

export interface TickerIndex {
  lastUpdated: string;
  tickers: string[];
}
