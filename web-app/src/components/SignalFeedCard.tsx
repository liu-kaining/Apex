import { Briefcase, Building2 } from "lucide-react";
import type { ApexSignal } from "@/types/feed";
import { TickerLink } from "@/components/TickerLink";
import {
  formatUsdZh,
  relativeTimeZh,
  signalTypeLabelZh,
  tagLabelZh,
} from "@/lib/zh";

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
  return [];
}

interface DataRowProps {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
  hint?: string;
}

function DataRow({ icon, label, children, hint }: DataRowProps) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5">
      <div className="flex min-w-0 items-center gap-2.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-800/80">
          {icon}
        </span>
        <div>
          <span className="text-sm text-zinc-400">{label}</span>
          {hint ? <p className="text-xs text-zinc-600">{hint}</p> : null}
        </div>
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
  const isResonance = signal.signalType === "STRONG_RESONANCE";

  return (
    <article className="group rounded-xl border border-slate-700/50 bg-card p-5 backdrop-blur-sm transition-all duration-200 hover:border-slate-600 hover:bg-slate-900/90">
      <header className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold tracking-tight text-zinc-100">
            <TickerLink ticker={signal.ticker} className="hover:text-sky-300 hover:underline">
              {signal.ticker}
            </TickerLink>
          </h2>
          <p className="truncate text-sm text-zinc-500">{signal.companyName}</p>
        </div>
        <span className="shrink-0 rounded-full border border-slate-600/80 bg-slate-900/80 px-2.5 py-1 text-xs text-zinc-400">
          {relativeTimeZh(insiderActions.date)}
        </span>
      </header>

      <div className="divide-y divide-slate-800/80">
        <DataRow
          icon={<Building2 className="h-4 w-4 text-indigo-400" strokeWidth={2} />}
          label="超级投资者"
          hint={
            superinvestorCount === 0
              ? "暂无大佬持仓（仅内部人买入，非共振）"
              : undefined
          }
        >
          <div className="flex flex-col items-end gap-1.5">
            <span className="tabular-nums font-medium">
              {superinvestorCount}
              <span className="font-normal text-zinc-500"> 家持仓</span>
            </span>
            {avatarCount > 0 && (
              <div className="flex -space-x-2">
                {avatars.slice(0, avatarCount).map((initials, index) => (
                  <span
                    key={`${initials}-${index}`}
                    className="flex h-7 w-7 items-center justify-center rounded-full border border-slate-700 bg-slate-800 text-[10px] font-semibold text-indigo-300"
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
          icon={<Briefcase className="h-4 w-4 text-positive" strokeWidth={2} />}
          label="内部人买入"
        >
          <div className="flex flex-col items-end gap-0.5">
            <span className="max-w-[12rem] truncate text-zinc-300">{primaryBuyer}</span>
            <span className="tabular-nums font-semibold text-positive">
              {formatUsdZh(insiderActions.totalAmountUsd)}
            </span>
          </div>
        </DataRow>
      </div>

      <footer className="mt-4 flex flex-wrap items-center gap-2">
        <span
          className={
            isResonance
              ? "rounded-md border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-xs font-medium text-indigo-300"
              : "rounded-md border border-slate-600/50 bg-slate-800/50 px-2 py-0.5 text-xs font-medium text-zinc-400"
          }
        >
          {signalTypeLabelZh(signal.signalType)}
        </span>
        {signal.tags.map((tag) => (
          <span
            key={tag}
            className="rounded-md border border-slate-700/50 px-2 py-0.5 text-xs text-zinc-500"
          >
            {tagLabelZh(tag)}
          </span>
        ))}
      </footer>
    </article>
  );
}
