export type SignalType = "STRONG_RESONANCE" | "INSIDER_BUY";

export interface InsiderActions {
  recentBuyers: string[];
  totalAmountUsd: number;
  date: string;
}

export interface SuperinvestorRef {
  cik: string;
  firm?: string;
  dataromaCode?: string;
  weightPct?: number;
}

export interface ApexSignal {
  id: string;
  ticker: string;
  companyName: string;
  signalType: SignalType;
  superinvestorCount: number;
  insiderActions: InsiderActions;
  tags: string[];
  superinvestors?: SuperinvestorRef[];
}

export interface FeedToday {
  lastUpdated: string;
  signals: ApexSignal[];
  resonanceMatched?: number;
}
