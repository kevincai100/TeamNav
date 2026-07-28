import type { Metadata } from "next";
import { Toaster } from "sonner";

import { AppHeader } from "@/components/app-header";
import { LocaleProvider } from "@/components/locale-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: "TeamNav · 团队工作台",
  description: "无需注册，创建并分享团队导航页",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" data-scroll-behavior="smooth">
      <body>
        <LocaleProvider>
          <AppHeader />
          {children}
          <Toaster position="top-center" richColors />
        </LocaleProvider>
      </body>
    </html>
  );
}
