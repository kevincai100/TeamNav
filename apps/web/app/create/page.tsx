"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Check, Copy, Download, ExternalLink, KeyRound, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { api, ApiError } from "@/lib/api";
import type { CreateResult } from "@/lib/types";

const schema = z.object({
  name: z.string().trim().min(1, "请输入站点名称").max(80, "最多 80 个字符"),
  description: z.string().trim().max(300, "最多 300 个字符"),
  icon: z.string().trim().min(1).max(8),
  template_id: z.string(),
  theme: z.enum(["light", "dark", "system"]),
  access_password: z.string().min(6, "密码至少 6 位").max(128).or(z.literal("")),
});

type FormValues = z.infer<typeof schema>;

const templates = [
  ["blank", "空白模板"], ["developer", "开发团队"], ["ecommerce", "跨境电商"],
  ["customer-support", "客服售后"], ["operations", "运营团队"], ["ai-tools", "AI 工具集合"],
  ["project-workspace", "项目工作台"],
];

export default function CreatePage() {
  const [result, setResult] = useState<CreateResult | null>(null);
  const [saved, setSaved] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", description: "", icon: "🧭", template_id: "developer", theme: "light", access_password: "" },
  });

  async function onSubmit(values: FormValues) {
    try {
      const created = await api<CreateResult>("/api/v1/sites", {
        method: "POST",
        body: JSON.stringify({ ...values, access_password: values.access_password || null }),
      });
      sessionStorage.setItem("teamnav_last_created", JSON.stringify(created));
      setResult(created);
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "REQUEST_FAILED";
      toast.error(code === "CREATE_RATE_LIMITED" ? "创建过于频繁，请稍后再试" : "创建失败，请检查 API 服务");
    }
  }

  async function copy(value: string, label: string) {
    await navigator.clipboard.writeText(value);
    toast.success(`${label}已复制`);
  }

  function downloadRecovery() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result.recovery_payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `teamnav-${result.site.public_slug}-recovery.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  if (result) {
    return (
      <main className="compact-shell create-result">
        <div className="success-mark"><Check size={28} /></div>
        <span className="eyebrow">创建完成</span>
        <h1>{result.site.name} 已就绪</h1>
        <p className="muted">公开链接用于团队浏览，私密链接只用于维护。请勿把两者发到同一个群聊。</p>

        <section className="result-row public-link-row">
          <div><span className="result-label">公开访问链接</span><code>{result.public_url}</code></div>
          <button className="icon-button" onClick={() => copy(result.public_url, "公开链接")} title="复制公开链接"><Copy size={17} /></button>
        </section>

        <section className="result-secret">
          <div className="secret-heading"><KeyRound size={19} /><strong>私密编辑链接</strong></div>
          <code>{result.manage_url}</code>
          <div className="secret-actions">
            <button className="button secondary" onClick={() => copy(result.manage_url, "编辑链接")}><Copy size={16} /> 复制</button>
            <button className="button secondary" onClick={downloadRecovery}><Download size={16} /> 恢复文件</button>
          </div>
          <p>编辑链接相当于管理员密码，丢失后无法通过账号找回。</p>
        </section>

        <div className="result-share">
          <QRCodeSVG value={result.public_url} size={148} bgColor="transparent" />
          <div><strong>扫码打开公开导航</strong><p className="muted">适合发到微信、Slack 或 Teams。</p><button className="button ghost" onClick={() => copy(`团队导航：${result.public_url}`, "分享文案")}><Copy size={16} /> 复制分享文案</button></div>
        </div>

        <label className="save-confirm"><input type="checkbox" checked={saved} onChange={(event) => setSaved(event.target.checked)} /><span><ShieldCheck size={18} /> 我已经保存私密编辑链接或恢复文件</span></label>
        <div className="result-actions">
          <Link className={`button ${!saved ? "disabled-link" : ""}`} aria-disabled={!saved} tabIndex={saved ? 0 : -1} href={saved ? result.manage_url : "#"}>进入管理页 <ExternalLink size={16} /></Link>
          <Link className="button secondary" href={`/s/${result.site.public_slug}`}>查看公开页</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="compact-shell create-page">
      <span className="eyebrow">匿名创建</span>
      <h1>建立团队导航</h1>
      <p className="muted">选择一个模板开始，稍后可在管理页完整调整。</p>
      <form className="panel create-form" onSubmit={form.handleSubmit(onSubmit)}>
        <div className="panel-body form-grid">
          <div className="field span-2"><label htmlFor="name">站点名称 *</label><input id="name" placeholder="例如：售后团队工作台" {...form.register("name")} />{form.formState.errors.name && <span className="field-error">{form.formState.errors.name.message}</span>}</div>
          <div className="field span-2"><label htmlFor="description">站点描述</label><textarea id="description" placeholder="这个导航页服务于哪些人？" {...form.register("description")} /></div>
          <div className="field"><label htmlFor="icon">站点图标</label><input id="icon" {...form.register("icon")} /></div>
          <div className="field"><label htmlFor="theme">页面主题</label><select id="theme" {...form.register("theme")}><option value="light">浅色</option><option value="dark">深色</option><option value="system">跟随系统</option></select></div>
          <div className="field span-2"><label htmlFor="template">起步模板</label><select id="template" {...form.register("template_id")}>{templates.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></div>
          <div className="field span-2"><label htmlFor="password">访问密码（可选）</label><input id="password" type="password" autoComplete="new-password" placeholder="团队成员访问前需要输入" {...form.register("access_password")} />{form.formState.errors.access_password && <span className="field-error">{form.formState.errors.access_password.message}</span>}</div>
        </div>
        <div className="create-submit"><span>无需邮箱或账号</span><button className="button" disabled={form.formState.isSubmitting}>{form.formState.isSubmitting ? "正在创建…" : "创建导航站"}</button></div>
      </form>
    </main>
  );
}
