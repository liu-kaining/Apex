export interface GridRow {
  ticker: string;
  heldBy: string[];
  totalWeight: number;
  qOqChange: string;
  holderCount: number;
}

export interface Sp500Grid {
  lastUpdated: string;
  sourcePortfolios?: number;
  grid: GridRow[];
}
