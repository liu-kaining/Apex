import Link from "next/link";
import Script from "next/script";

/** 静态站：/ticker/MCD → /ticker?t=MCD（脚本在首屏执行，不依赖 React hydration） */
export default function NotFound() {
  return (
    <>
      <Script id="ticker-legacy-redirect" strategy="beforeInteractive">
        {`(function(){var m=location.pathname.match(/\\/ticker\\/([^/.]+)\\/?$/i);if(m&&m[1]){location.replace('/ticker?t='+encodeURIComponent(m[1].toUpperCase()));}})();`}
      </Script>
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 px-4">
        <h1 className="text-2xl font-semibold text-zinc-100">页面不存在</h1>
        <p className="text-sm text-zinc-500">
          个股请使用 <code className="text-sky-400">/ticker?t=代码</code> 打开
        </p>
        <Link href="/" className="text-sm text-sky-400 hover:underline">
          返回信号流
        </Link>
      </div>
    </>
  );
}
