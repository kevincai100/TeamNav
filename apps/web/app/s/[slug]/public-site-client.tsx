"use client";

import { KeyRound } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { NavigationView } from "@/components/navigation-view";
import { useI18n } from "@/components/locale-provider";
import { api, ApiError } from "@/lib/api";
import type { Site } from "@/lib/types";

export function PublicSiteClient({ slug }: { slug: string }) {
  const { t } = useI18n();
  const [site, setSite] = useState<Site | null>(null);
  const [status, setStatus] = useState<"loading" | "locked" | "missing" | "ready">("loading");
  const [password, setPassword] = useState("");
  const [unlocking, setUnlocking] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await api<Site>(`/api/v1/public/sites/${slug}`);
      setSite(data);
      setStatus("ready");
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.code === "PASSWORD_REQUIRED") setStatus("locked");
      else setStatus("missing");
    }
  }, [slug]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function unlock(event: React.FormEvent) {
    event.preventDefault();
    setUnlocking(true);
    setError("");
    try {
      await api<void>(`/api/v1/public/sites/${slug}/unlock`, { method: "POST", body: JSON.stringify({ password }) });
      await load();
    } catch {
      setError(t("密码不正确，请重试"));
    } finally {
      setUnlocking(false);
    }
  }

  if (status === "loading") return <main className="loading"><div className="spinner" aria-label={t("正在加载")} /></main>;
  if (status === "locked") {
    return (
      <main className="unlock-page">
        <form className="panel unlock-panel" onSubmit={unlock}>
          <div className="unlock-icon"><KeyRound size={24} /></div>
          <h1>{t("这个导航需要密码")}</h1>
          <p className="muted">{t("请输入创建者提供的访问密码。")}</p>
          <div className="field"><label htmlFor="unlock-password">{t("访问密码")}</label><input id="unlock-password" type="password" autoFocus value={password} onChange={(event) => setPassword(event.target.value)} /></div>
          {error && <p className="field-error">{error}</p>}
          <button className="button" disabled={unlocking || !password}>{t(unlocking ? "正在验证…" : "进入导航")}</button>
        </form>
      </main>
    );
  }
  if (status === "missing" || !site) return <main className="error-state"><h1>{t("导航站不可用")}</h1><p className="muted">{t("链接可能已失效、站点已删除或被停用。")}</p></main>;
  return <NavigationView site={site} />;
}
