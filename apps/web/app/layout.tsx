import type { Metadata } from "next";
import { Inter, Noto_Sans_SC } from "next/font/google";
import Link from "next/link";
import { Compass, Github, Plus, UserRound } from "lucide-react";
import { Toaster } from "sonner";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const noto = Noto_Sans_SC({ subsets: ["latin"], variable: "--font-noto" });

export const metadata: Metadata = {
  title: "TeamNav · 团队工作台",
  description: "无需注册，创建并分享团队导航页",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" data-scroll-behavior="smooth">
      <body className={`${inter.variable} ${noto.variable}`}>
        <header className="app-header">
          <Link className="brand" href="/" aria-label="TeamNav 首页">
            <span className="brand-mark"><Compass size={19} /></span>
            <span>TeamNav</span>
          </Link>
          <nav aria-label="主导航">
            <Link className="header-create" href="/create"><Plus size={16} /> 新建工作台</Link>
            <Link href="/account" aria-label="个人账号" title="个人账号"><UserRound size={18} /></Link>
            <a href="https://github.com/kevincai100/TeamNav" target="_blank" rel="noopener noreferrer" aria-label="GitHub">
              <Github size={18} />
            </a>
          </nav>
        </header>
        {children}
        <Toaster position="top-center" richColors />
      </body>
    </html>
  );
}
