"use client";

import { Briefcase, User } from "lucide-react";
import type { TimelineEvent } from "@/types/timeline";

function EventIcon({ type }: { type: string }) {
  if (type === "INSIDER") {
    return <User className="h-4 w-4 text-positive" />;
  }
  return <Briefcase className="h-4 w-4 text-indigo-400" />;
}

function eventTypeLabel(type: string): string {
  if (type === "INSIDER") return "内部人";
  if (type === "13F") return "13F 持仓";
  return type;
}

interface ConvictionTimelineProps {
  events: TimelineEvent[];
}

export function ConvictionTimeline({ events }: ConvictionTimelineProps) {
  if (!events.length) {
    return (
      <p className="rounded-lg border border-slate-700/50 bg-card px-4 py-8 text-center text-sm text-zinc-500">
        该标的暂无 conviction 事件记录。
      </p>
    );
  }

  return (
    <ol className="relative space-y-0 border-l border-slate-700 pl-6">
      {events.map((event, index) => (
        <li key={`${event.date}-${event.type}-${index}`} className="pb-8 last:pb-0">
          <span className="absolute -left-[9px] flex h-4 w-4 items-center justify-center rounded-full border border-slate-600 bg-background">
            <EventIcon type={event.type} />
          </span>
          <span className="text-xs text-zinc-500">
            {event.date || "—"} · {eventTypeLabel(event.type)}
          </span>
          <p className="mt-1 text-sm font-medium text-zinc-100">{event.title}</p>
          <p className="mt-0.5 text-sm text-zinc-500">{event.description}</p>
        </li>
      ))}
    </ol>
  );
}
