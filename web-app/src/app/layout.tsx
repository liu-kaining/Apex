import type { Metadata } from "next";
import localFont from "next/font/local";
import { SiteNav } from "@/components/SiteNav";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Apex — 共振信号",
  description: "超级投资者 13F × 内部人买入 · Serverless 投研看板",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} min-h-screen bg-background font-sans tabular-nums antialiased text-zinc-100`}
      >
        <SiteNav />
        {children}
      </body>
    </html>
  );
}
