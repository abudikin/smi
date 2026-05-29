import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SMI Admin",
  description: "Админка источников и новостей",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>
        <div className="shell">
          <header className="topbar">
            <div className="brand">SMI Admin</div>
            <nav className="nav">
              <a href="/">Источники</a>
              <a href="/news">Новости</a>
            </nav>
          </header>
          <main className="content">{children}</main>
        </div>
      </body>
    </html>
  );
}
