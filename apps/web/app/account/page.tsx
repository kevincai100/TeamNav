"use client";

import { ExternalLink, LogOut, Plus, RefreshCw, Settings2, UserRound, WifiOff } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api";

type AccountSite = { public_slug: string; name: string; description: string | null; icon: string; theme: string; visit_count: number; is_disabled: boolean; updated_at: string };
type AccountData = { email: string; sites: AccountSite[] };

export default function AccountPage() {
  const [account, setAccount] = useState<AccountData | null>(null);
  const [status, setStatus] = useState<"loading" | "guest" | "ready" | "error">("loading");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const load = useCallback(async () => {
    try {
      const restored = await api<{ email: string; csrf_token: string }>("/api/v1/account/session", { method: "POST" });
      sessionStorage.setItem("teamnav_account_csrf", restored.csrf_token);
      setAccount(await api<AccountData>("/api/v1/account/sites")); setStatus("ready");
    }
    catch (error) {
      setAccount(null);
      if (error instanceof ApiError && error.status === 401) {
        sessionStorage.removeItem("teamnav_account_csrf");
        setStatus("guest");
      } else {
        setStatus("error");
      }
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function authenticate(event: React.FormEvent) {
    event.preventDefault();
    try {
      const result = await api<{ email: string; csrf_token: string }>(`/api/v1/account/${mode}`, { method: "POST", body: JSON.stringify({ email, password }) });
      sessionStorage.setItem("teamnav_account_csrf", result.csrf_token);
      setPassword(""); await load();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "REQUEST_FAILED";
      toast.error(code === "EMAIL_ALREADY_REGISTERED" ? "这个邮箱已经注册" : "邮箱或密码不正确");
    }
  }

  async function logout() {
    await api<void>("/api/v1/account/logout", { method: "POST" });
    sessionStorage.removeItem("teamnav_account_csrf"); setAccount(null); setStatus("guest");
  }

  function prepareManage(slug: string) {
    const csrf = sessionStorage.getItem("teamnav_account_csrf");
    if (csrf) sessionStorage.setItem(`teamnav_csrf_${slug}`, csrf);
  }

  if (status === "loading") return <main className="loading"><div className="spinner" /></main>;
  if (status === "error") return <main className="error-state"><WifiOff size={34} /><h1>暂时无法连接</h1><p className="muted">账号会话仍会保留，请检查服务状态后重试。</p><button className="button" onClick={() => { setStatus("loading"); void load(); }}><RefreshCw size={16} />重试</button></main>;
  if (status === "guest") return <main className="compact-shell account-auth"><div className="auth-heading"><UserRound size={30} /><h1>{mode === "login" ? "登录个人账号" : "创建个人账号"}</h1><p className="muted">账号是可选的。登录后，新建和认领的工作台会同步到这里。</p></div><div className="segmented"><button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>登录</button><button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>注册</button></div><form className="panel" onSubmit={authenticate}><div className="panel-body form-stack"><div className="field"><label htmlFor="account-email">邮箱</label><input id="account-email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></div><div className="field"><label htmlFor="account-password">密码</label><input id="account-password" type="password" minLength={10} autoComplete={mode === "login" ? "current-password" : "new-password"} required value={password} onChange={(event) => setPassword(event.target.value)} /><span className="muted field-hint">至少 10 位</span></div><button className="button">{mode === "login" ? "登录" : "注册并登录"}</button></div></form></main>;

  return <main className="account-page"><header className="account-title"><div><span className="eyebrow">{account?.email}</span><h1>我的工作台</h1></div><div><Link className="button" href="/create"><Plus size={16} />新建</Link><button className="icon-button" title="退出登录" onClick={() => void logout()}><LogOut size={17} /></button></div></header>{account?.sites.length === 0 ? <section className="account-empty"><h2>还没有工作台</h2><p className="muted">创建新站点，或用私密编辑链接进入已有站点后认领。</p><Link className="button" href="/create">创建工作台</Link></section> : <section className="account-sites">{account?.sites.map((site) => <article className="account-site" key={site.public_slug}><span className="account-site-icon">{site.icon}</span><div><h2>{site.name}</h2><p>{site.description || "暂无描述"}</p><small>{site.visit_count} 次访问 · {new Date(site.updated_at).toLocaleDateString("zh-CN")}</small></div><div className="account-site-actions"><Link className="icon-button" title="管理" href={`/manage/${site.public_slug}`} onClick={() => prepareManage(site.public_slug)}><Settings2 size={16} /></Link><Link className="icon-button" title="公开访问" href={`/s/${site.public_slug}`} target="_blank"><ExternalLink size={16} /></Link></div></article>)}</section>}</main>;
}
