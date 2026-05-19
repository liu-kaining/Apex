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
  title: "Apex — Resonance Signals",
  description:
    "Serverless investment research: superinvestor 13F × insider buy resonance.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} min-h-screen bg-[#0A0A0A] font-sans tabular-nums antialiased text-zinc-100`}
      >
        <SiteNav />
        {children}
      </body>
    </html>
  );
}
