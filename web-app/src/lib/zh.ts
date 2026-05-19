/** UI copy — 简体中文 */

export function formatZhDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("zh-CN", {
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return iso;
  }
}

export function relativeTimeZh(isoDate: string): string {
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(isoDate)
    ? `${isoDate}T12:00:00Z`
    : isoDate;
  const then = new Date(normalized).getTime();
  if (Number.isNaN(then)) return isoDate;
  const hours = Math.max(1, Math.round((Date.now() - then) / (1000 * 60 * 60)));
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.round(hours / 24);
  return `${days} 天前`;
}

export function formatUsdZh(amount: number): string {
  if (amount >= 100_000_000) {
    return `约 $${(amount / 100_000_000).toFixed(2)} 亿`;
  }
  if (amount >= 1_000_000) {
    return `约 $${(amount / 1_000_000).toFixed(1)} 百万`;
  }
  if (amount >= 10_000) {
    return `约 $${(amount / 10_000).toFixed(0)} 万`;
  }
  return `$${amount.toLocaleString("zh-CN")}`;
}

export function tagLabelZh(tag: string): string {
  const map: Record<string, string> = {
    "Cluster Buy": "集中买入",
    "Insider Buy": "内部人买入",
    "13F Resonance": "13F 共振",
    "Officer Buy": "高管买入",
    "Resonance": "共振",
  };
  return map[tag] ?? tag;
}

export function signalTypeLabelZh(signalType: string): string {
  if (signalType === "STRONG_RESONANCE") return "强共振";
  if (signalType === "INSIDER_BUY") return "内部人买入";
  return signalType;
}

export function qoqLabelZh(change: string): string {
  if (change === "NEW") return "新建仓";
  if (change === "INCREASED") return "增持";
  if (change === "DECREASED") return "减持";
  return "持平";
}
