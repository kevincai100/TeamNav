"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import {
  LOCALE_STORAGE_KEY,
  localeTag,
  resolveLocale,
  translate,
  type Locale,
} from "@/lib/i18n";

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (message: string, values?: Record<string, string | number>) => string;
  formatDate: (value: string | Date) => string;
  formatDateTime: (value: string | Date) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("zh-CN");

  useEffect(() => {
    const detected = resolveLocale(localStorage.getItem(LOCALE_STORAGE_KEY), navigator.languages);
    document.documentElement.lang = localeTag(detected);
    const timer = window.setTimeout(() => setLocaleState(detected), 0);
    return () => window.clearTimeout(timer);
  }, []);

  const value = useMemo<I18nContextValue>(() => ({
    locale,
    setLocale(next) {
      localStorage.setItem(LOCALE_STORAGE_KEY, next);
      document.documentElement.lang = localeTag(next);
      setLocaleState(next);
    },
    t: (message, values) => translate(locale, message, values),
    formatDate: (input) => new Intl.DateTimeFormat(localeTag(locale)).format(new Date(input)),
    formatDateTime: (input) => new Intl.DateTimeFormat(localeTag(locale), {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(input)),
  }), [locale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useI18n must be used within LocaleProvider");
  return value;
}
