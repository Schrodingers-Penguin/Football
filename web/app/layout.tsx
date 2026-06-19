import type { Metadata } from "next";
import localFont from "next/font/local";
import Link from "next/link";
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
  title: "Scouting",
  description: "Player and team scouting",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen`}>
        <nav className="border-b border-neutral-800 px-6 py-3 flex gap-6 text-sm text-neutral-400">
          <Link href="/" className="hover:text-white transition-colors">
            Players
          </Link>
          <Link href="/leagues" className="hover:text-white transition-colors">
            Leagues
          </Link>
          <Link href="/compare" className="hover:text-white transition-colors">
            Compare
          </Link>
          <Link href="/scatter" className="hover:text-white transition-colors">
            Scatter
          </Link>
        </nav>
        <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
