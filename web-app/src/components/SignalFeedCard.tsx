import Link from "next/link";
import { Briefcase, Building2 } from "lucide-react";
import type { ApexSignal } from "@/types/feed";

function initialsFromFirm(firm: string): string {
  const words = firm.trim().split(/\s+/).filter(Boolean);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  return firm.slice(0, 2).toUpperCase();
}

function holderAvatars(signal: ApexSignal): string[] {
  if (signal.superinvestors?.length) {
    return signal.superinvestors
      .slice(0, 5)
      .map((h) => initialsFromFirm(h.firm ?? h.dataromaCode ?? "??"));
  }
  return ["BH", "TG", "BW", "CP", "DE"];
}

function formatUsd(amount: number): string {
  if (amount >= 1_000_000) {
    return `$${(amount / 1_000_000).toFixed(1)}M`;
  }
  if (amount >= 1_000) {
    return `$${(amount / 1_000).toFixed(0)}K`;
  }
  return `$${amount.toLocaleString()}`;
}

function relativeTime(isoDate: string): string {
  // Date-only strings (YYYY-MM-DD) are parsed as UTC midnight; anchor at noon UTC.
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(isoDate)
    ? `${isoDate}T12:00:00Z`
    : isoDate;
  const then = new Date(normalized).getTime();
  if (Number.isNaN(then)) return isoDate;
  const now = Date.now();
  const hours = Math.max(1, Math.round((now - then) / (1000 * 60 * 60)));
  if (hours < 24) return `${hours} Hr${hours === 1 ? "" : "s"} Ago`;
  const days = Math.round(hours / 24);
  return `${days} Day${days === 1 ? "" : "s"} Ago`;
}

function signalBadgeLabel(signal: ApexSignal): string {
  if (signal.signalType === "STRONG_RESONANCE") return "Resonance";
  return "Insider Buy";
}

interface DataRowProps {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}

function DataRow({ icon, label, children }: DataRowProps) {
  return (
    <div className="flex items-center justify-between gap-3 py-2">
      <div className="flex min-w-0 items-center gap-2.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/5">
          {icon}
        </span>
        <span className="text-sm text-zinc-400">{label}</span>
      </div>
      <div className="shrink-0 text-right text-sm text-zinc-100">{children}</div>
    </div>
  );
}

interface SignalFeedCardProps {
  signal: ApexSignal;
}

export function SignalFeedCard({ signal }: SignalFeedCardProps) {
  const { insiderActions, superinvestorCount } = signal;
  const primaryBuyer = insiderActions.recentBuyers[0] ?? "—";
  const avatars = holderAvatars(signal);
  const avatarCount = Math.min(superinvestorCount, avatars.length);

  return (
    <article
      className="group rounded-xl border border-white/10 bg-white/5 p-5 backdrop-blur-md transition-all duration-200 hover:border-zinc-700 hover:bg-zinc-900/80"
    >
      {/* Header */}
      <header className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold tracking-tight text-zinc-100">
            <Link
              href={`/ticker/${signal.ticker}`}
              className="hover:text-[#00FF66] hover:underline"
            >
              {signal.ticker}
            </Link>
          </h2>
          <p className="truncate text-sm text-zinc-400">{signal.companyName}</p>
        </div>
        <span className="shrink-0 rounded-full border border-white/10 bg-black/40 px-2.5 py-1 text-xs font-medium text-zinc-400">
          {relativeTime(insiderActions.date)}
        </span>
      </header>

      {/* Body — two DataRows */}
      <div className="divide-y divide-white/5">
        <DataRow
          icon={<Building2 className="h-4 w-4 text-[#8B5CF6]" strokeWidth={2} />}
          label="Superinvestors"
        >
          <div className="flex flex-col items-end gap-1.5">
            <span className="tabular-nums font-medium">
              {superinvestorCount}{" "}
              <span className="font-normal text-zinc-400">holding</span>
            </span>
            {avatarCount > 0 && (
              <div className="flex -space-x-2">
                {avatars.slice(0, avatarCount).map((initials, index) => (
                  <span
                    key={`${initials}-${index}`}
                    className="flex h-7 w-7 items-center justify-center rounded-full border border-zinc-800 bg-zinc-900 text-[10px] font-semibold text-[#8B5CF6]"
                    title={initials}
                  >
                    {initials}
                  </span>
                ))}
              </div>
            )}
          </div>
        </DataRow>

        <DataRow
          icon={<Briefcase className="h-4 w-4 text-[#00FF66]" strokeWidth={2} />}
          label="Insider Buy"
        >
          <div className="flex flex-col items-end gap-0.5">
            <span className="max-w-[12rem] truncate text-zinc-300">{primaryBuyer}</span>
            <span className="tabular-nums font-semibold text-[#00FF66]">
              {formatUsd(insiderActions.totalAmountUsd)}
            </span>
          </div>
        </DataRow>
      </div>

      {/* Tags + signal type */}
      <footer className="mt-4 flex flex-wrap items-center gap-2">
        <span
          className={
            signal.signalType === "STRONG_RESONANCE"
              ? "rounded-md border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 px-2 py-0.5 text-xs font-medium text-[#8B5CF6]"
              : "rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-xs font-medium text-zinc-400"
          }
        >
          {signalBadgeLabel(signal)}
        </span>
        {signal.tags.map((tag) => (
          <span
            key={tag}
            className="rounded-md border border-white/5 px-2 py-0.5 text-xs text-zinc-500"
          >
            {tag}
          </span>
        ))}
      </footer>
    </article>
  );
}
