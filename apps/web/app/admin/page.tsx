"use client";

import { Ban, Check, RefreshCw, Shield, Undo2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { useI18n } from "@/components/locale-provider";

type Report = { id: string; site_slug: string | null; site_name: string; reason: string; description: string | null; status: "open" | "resolved" | "dismissed"; created_at: string };
type AdminSite = { public_slug: string; name: string; is_disabled: boolean; visit_count: number; created_at: string };
type Dashboard = { reports: Report[]; sites: AdminSite[] };

export default function AdminPage() {
  const { t, formatDateTime } = useI18n();
  const [token, setToken] = useState("");
  const [csrf, setCsrf] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [status, setStatus] = useState<"loading" | "login" | "ready">("loading");

  const load = useCallback(async () => {
    try { setDashboard(await api<Dashboard>("/api/v1/admin/dashboard")); setStatus("ready"); }
    catch { setStatus("login"); }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setCsrf(sessionStorage.getItem("teamnav_admin_csrf") ?? "");
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function login(event: React.FormEvent) {
    event.preventDefault();
    try {
      const result = await api<{ csrf_token: string }>("/api/v1/admin/session", { method: "POST", body: JSON.stringify({ token }) });
      sessionStorage.setItem("teamnav_admin_csrf", result.csrf_token);
      setCsrf(result.csrf_token); setToken(""); await load();
    } catch { toast.error(t("管理员令牌无效")); }
  }

  async function mutate(path: string, body: unknown) {
    await api(path, { method: "PATCH", headers: { "X-CSRF-Token": csrf }, body: JSON.stringify(body) });
    await load();
  }

  if (status === "loading") return <main className="loading"><div className="spinner" /></main>;
  if (status === "login") return <main className="compact-shell admin-login"><form className="panel" onSubmit={login}><div className="panel-body form-stack"><Shield size={30} /><h1>{t("管理后台")}</h1><p className="muted">{t("使用服务端配置的管理员令牌登录。")}</p><div className="field"><label htmlFor="admin-token">{t("管理员令牌")}</label><input id="admin-token" type="password" autoComplete="current-password" required value={token} onChange={(event) => setToken(event.target.value)} /></div><button className="button">{t("登录")}</button></div></form></main>;

  const openReports = dashboard?.reports.filter((report) => report.status === "open") ?? [];
  return <main className="admin-page">
    <header className="admin-title"><div><span className="eyebrow">{t("运营与安全")}</span><h1>{t("管理后台")}</h1></div><button className="icon-button" title={t("刷新")} onClick={() => void load()}><RefreshCw size={17} /></button></header>
    <section className="admin-section"><div className="admin-section-title"><h2>{t("待处理举报")}</h2><span>{openReports.length}</span></div>{openReports.length === 0 ? <p className="admin-empty">{t("暂无待处理举报")}</p> : <div className="admin-table-wrap"><table><thead><tr><th>{t("站点")}</th><th>{t("原因")}</th><th>{t("说明")}</th><th>{t("时间")}</th><th>{t("操作")}</th></tr></thead><tbody>{openReports.map((report) => <tr key={report.id}><td><a href={`/s/${report.site_slug}`} target="_blank">{report.site_name}</a></td><td>{t(report.reason)}</td><td>{report.description || "-"}</td><td>{formatDateTime(report.created_at)}</td><td><div className="table-actions"><button className="icon-button" title={t("标记已处理")} onClick={() => void mutate(`/api/v1/admin/reports/${report.id}`, { status: "resolved" })}><Check size={15} /></button><button className="icon-button" title={t("驳回举报")} onClick={() => void mutate(`/api/v1/admin/reports/${report.id}`, { status: "dismissed" })}><Undo2 size={15} /></button></div></td></tr>)}</tbody></table></div>}</section>
    <section className="admin-section"><div className="admin-section-title"><h2>{t("站点状态")}</h2><span>{dashboard?.sites.length ?? 0}</span></div><div className="admin-table-wrap"><table><thead><tr><th>{t("名称")}</th><th>{t("公开标识")}</th><th>{t("访问")}</th><th>{t("状态")}</th><th>{t("操作")}</th></tr></thead><tbody>{dashboard?.sites.map((site) => <tr key={site.public_slug}><td><a href={`/s/${site.public_slug}`} target="_blank">{site.name}</a></td><td><code>{site.public_slug}</code></td><td>{site.visit_count}</td><td><span className={`status-dot ${site.is_disabled ? "disabled" : "active"}`}>{t(site.is_disabled ? "已封禁" : "正常")}</span></td><td><button className={`button ${site.is_disabled ? "secondary" : "danger"}`} onClick={() => void mutate(`/api/v1/admin/sites/${site.public_slug}`, { is_disabled: !site.is_disabled })}>{site.is_disabled ? <><Undo2 size={15} />{t("解除")}</> : <><Ban size={15} />{t("封禁")}</>}</button></td></tr>)}</tbody></table></div></section>
  </main>;
}
