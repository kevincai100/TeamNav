"use client";

import { Compass, Github, Languages, Plus, UserRound } from "lucide-react";
import Link from "next/link";

import { useI18n } from "@/components/locale-provider";
import type { Locale } from "@/lib/i18n";

export function AppHeader() {
  const { locale, setLocale, t } = useI18n();
  return (
    <header className="app-header">
      <Link className="brand" href="/" aria-label={t("TeamNav 首页")}>
        <span className="brand-mark"><Compass size={19} /></span>
        <span>TeamNav</span>
      </Link>
      <nav aria-label={t("主导航")}>
        <Link className="header-create" href="/create"><Plus size={16} /> {t("新建工作台")}</Link>
        <Link href="/account" aria-label={t("个人账号")} title={t("个人账号")}><UserRound size={18} /></Link>
        <label className="language-picker" title={t("语言")}>
          <Languages size={17} aria-hidden="true" />
          <select aria-label={t("语言")} value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>
            <option value="zh-CN">{t("中文")}</option>
            <option value="en">{t("英文")}</option>
          </select>
        </label>
        <a href="https://github.com/kevincai100/TeamNav" target="_blank" rel="noopener noreferrer" aria-label="GitHub">
          <Github size={18} />
        </a>
      </nav>
    </header>
  );
}
