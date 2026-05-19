import { GridSection } from "@/components/GridSection";
import { Grid3X3 } from "lucide-react";

export const metadata = {
  title: "Apex — 超级投资者共识热力图",
  description: "按规则 2 聚合的 13F 持仓共识热力图。",
};

export default function GridPage() {
  return (
    <div className="min-h-screen bg-background">
      <main className="mx-auto max-w-5xl px-4 pb-16 pt-10 sm:px-6">
        <header className="mb-8">
          <div className="mb-2 flex items-center gap-2 text-zinc-500">
            <Grid3X3 className="h-4 w-4 text-indigo-400" />
            <span className="text-xs tracking-wide">规则 2 筛选</span>
          </div>
          <h1 className="text-3xl font-semibold text-zinc-100">共识热力图</h1>
          <p className="mt-2 max-w-xl text-sm text-zinc-500">
            超级投资者持仓权重 &gt;1% 或季度变化显著。点击格子查看 conviction 时间轴。
          </p>
        </header>
        <GridSection />
      </main>
    </div>
  );
}
