"use client";

import { Briefcase, User } from "lucide-react";
import type { TimelineEvent } from "@/types/timeline";

function EventIcon({ type }: { type: string }) {
  if (type === "INSIDER") {
    return <User className="h-4 w-4 text-[#00FF66]" />;
  }
  return <Briefcase className="h-4 w-4 text-[#8B5CF6]" />;
}

interface ConvictionTimelineProps {
  events: TimelineEvent[];
}

export function ConvictionTimeline({ events }: ConvictionTimelineProps) {
  if (!events.length) {
    return (
      <p className="rounded-lg border border-white/10 bg-white/5 px-4 py-8 text-center text-sm text-zinc-500">
        No conviction events for this ticker yet.
      </p>
    );
  }

  return (
    <ol className="relative space-y-0 border-l border-white/10 pl-6">
      {events.map((event, index) => (
        <li key={`${event.date}-${event.type}-${index}`} className="pb-8 last:pb-0">
          <span className="absolute -left-[9px] flex h-4 w-4 items-center justify-center rounded-full border border-white/20 bg-[#0A0A0A]">
            <EventIcon type={event.type} />
          </span>
          <time className="text-xs text-zinc-500">{event.date || "—"}</time>
          <p className="mt-1 text-sm font-medium text-zinc-100">{event.title}</p>
          <p className="mt-0.5 text-sm text-zinc-400">{event.description}</p>
        </li>
      ))}
    </ol>
  );
}
