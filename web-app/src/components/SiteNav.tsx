"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Grid3X3, Zap } from "lucide-react";

const links = [
  { href: "/", label: "Feed", icon: Zap },
  { href: "/grid", label: "Heatmap", icon: Grid3X3 },
] as const;

export function SiteNav() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 border-b border-white/5 bg-[#0A0A0A]/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-4xl items-center gap-1 px-4 py-3 sm:px-6">
        <Link
          href="/"
          className="mr-4 text-sm font-semibold tracking-tight text-zinc-100"
        >
          Apex
        </Link>
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors ${
                active
                  ? "bg-white/10 text-[#00FF66]"
                  : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
