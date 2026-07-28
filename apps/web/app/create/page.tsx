"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  Bot, BriefcaseBusiness, Check, Code2, Copy, Download, ExternalLink,
  Headphones, KeyRound, Megaphone, PackageOpen, ShieldCheck, ShoppingBag,
} from "lucide-react";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { api, ApiError } from "@/lib/api";
import type { CreateResult } from "@/lib/types";
import { useI18n } from "@/components/locale-provider";

function createSchema(t: (message: string, values?: Record<string, string | number>) => string) {
  return z.object({
    name: z.string().trim().min(1, t("请输入站点名称")).max(80, t("最多 {count} 个字符", { count: 80 })),
    description: z.string().trim().max(300, t("最多 {count} 个字符", { count: 300 })),
    icon: z.string().trim().min(1).max(8),
    template_id: z.string(),
    theme: z.enum(["light", "dark", "system"]),
    access_password: z.string().min(6, t("密码至少 {count} 位", { count: 6 })).max(128).or(z.literal("")),
  });
}

type FormValues = z.infer<ReturnType<typeof createSchema>>;

const templates = [
  { id: "blank", name: "空白", icon: PackageOpen },
  { id: "developer", name: "开发团队", icon: Code2 },
  { id: "ecommerce", name: "跨境电商", icon: ShoppingBag },
  { id: "customer-support", name: "客服售后", icon: Headphones },
  { id: "operations", name: "运营团队", icon: Megaphone },
  { id: "ai-tools", name: "AI 工具", icon: Bot },
  { id: "project-workspace", name: "项目协作", icon: BriefcaseBusiness },
];

export default function CreatePage() {
  const { t } = useI18n();
  const schema = useMemo(() => createSchema(t), [t]);
  const [result, setResult] = useState<CreateResult | null>(null);
  const [saved, setSaved] = useState(false);
  const [captcha, setCaptcha] = useState<{ required: boolean; prompt: string; token: string } | null>(null);
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", description: "", icon: "🧭", template_id: "developer", theme: "light", access_password: "" },
  });
  const selectedTemplate = useWatch({ control: form.control, name: "template_id" });
  const selectedTheme = useWatch({ control: form.control, name: "theme" });

  const loadCaptcha = useCallback(async () => {
    try {
      setCaptcha(await api("/api/v1/captcha/challenge"));
      setCaptchaAnswer("");
    } catch {
      setCaptcha(null);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadCaptcha(), 0);
    return () => window.clearTimeout(timer);
  }, [loadCaptcha]);

  async function onSubmit(values: FormValues) {
    try {
      const created = await api<CreateResult>("/api/v1/sites", {
        method: "POST",
        body: JSON.stringify({
          ...values,
          access_password: values.access_password || null,
          captcha_token: captcha?.token,
          captcha_answer: captchaAnswer,
        }),
      });
      sessionStorage.setItem("teamnav_last_created", JSON.stringify(created));
      setResult(created);
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "REQUEST_FAILED";
      if (code.startsWith("CAPTCHA_")) await loadCaptcha();
      toast.error(t(code === "CREATE_RATE_LIMITED" ? "创建过于频繁，请稍后再试" : "创建失败，请检查 API 服务"));
    }
  }

  async function copy(value: string, label: string) {
    await navigator.clipboard.writeText(value);
    toast.success(t("{label}已复制", { label }));
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
        <span className="eyebrow">{t("创建完成")}</span>
        <h1>{t("{name} 已就绪", { name: result.site.name })}</h1>
        <p className="muted">{t("公开链接用于团队浏览，私密链接只用于维护。请勿把两者发到同一个群聊。")}</p>

        <section className="result-row public-link-row">
          <div><span className="result-label">{t("公开访问链接")}</span><code>{result.public_url}</code></div>
          <button className="icon-button" onClick={() => copy(result.public_url, t("公开链接"))} title={t("复制公开链接")}><Copy size={17} /></button>
        </section>

        <section className="result-secret">
          <div className="secret-heading"><KeyRound size={19} /><strong>{t("私密编辑链接")}</strong></div>
          <code>{result.manage_url}</code>
          <div className="secret-actions">
            <button className="button secondary" onClick={() => copy(result.manage_url, t("编辑链接"))}><Copy size={16} /> {t("复制")}</button>
            <button className="button secondary" onClick={downloadRecovery}><Download size={16} /> {t("恢复文件")}</button>
          </div>
          <p>{t("编辑链接相当于管理员密码，丢失后无法通过账号找回。")}</p>
        </section>

        <div className="result-share">
          <QRCodeSVG value={result.public_url} size={148} bgColor="transparent" />
          <div><strong>{t("扫码打开公开导航")}</strong><p className="muted">{t("适合发到微信、Slack 或 Teams。")}</p><button className="button ghost" onClick={() => copy(t("团队导航：{url}", { url: result.public_url }), t("分享文案"))}><Copy size={16} /> {t("复制分享文案")}</button></div>
        </div>

        <label className="save-confirm"><input type="checkbox" checked={saved} onChange={(event) => setSaved(event.target.checked)} /><span><ShieldCheck size={18} /> {t("我已经保存私密编辑链接或恢复文件")}</span></label>
        <div className="result-actions">
          <Link data-testid="manage-link" className={`button ${!saved ? "disabled-link" : ""}`} aria-disabled={!saved} tabIndex={saved ? 0 : -1} href={saved ? result.manage_url : "#"}>{t("进入管理页")} <ExternalLink size={16} /></Link>
          <Link className="button secondary" href={`/s/${result.site.public_slug}`}>{t("查看公开页")}</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="compact-shell create-page">
      <span className="eyebrow">{t("创建工作台")}</span>
      <h1>{t("从一个清晰的入口开始。")}</h1>
      <p className="muted">{t("先确定内容骨架，创建后可以继续调整品牌色、布局和卡片样式。")}</p>
      <form className="panel create-form" onSubmit={form.handleSubmit(onSubmit)}>
        <div className="panel-body form-grid">
          {captcha?.required && <div className="field span-2 captcha-field"><label htmlFor="captcha-answer">{t("人机验证：{prompt}", { prompt: captcha.prompt })}</label><div><input id="captcha-answer" inputMode="numeric" autoComplete="off" required value={captchaAnswer} onChange={(event) => setCaptchaAnswer(event.target.value)} /><button type="button" className="button secondary" onClick={() => void loadCaptcha()}>{t("换一题")}</button></div></div>}
          <div className="field span-2"><label htmlFor="name">{t("站点名称 *")}</label><input id="name" placeholder={t("例如：售后团队工作台")} {...form.register("name")} />{form.formState.errors.name && <span className="field-error">{form.formState.errors.name.message}</span>}</div>
          <div className="field span-2"><label htmlFor="description">{t("站点描述")}</label><textarea id="description" placeholder={t("这个导航页服务于哪些人？")} {...form.register("description")} /></div>
          <div className="field span-2 icon-field"><label htmlFor="icon">{t("站点图标")}</label><input id="icon" {...form.register("icon")} /></div>
          <fieldset className="template-picker span-2">
            <legend>{t("起步模板")}</legend>
            <input type="hidden" {...form.register("template_id")} />
            <div className="template-grid" role="radiogroup" aria-label={t("起步模板")}>
              {templates.map((template) => {
                const Icon = template.icon;
                return <button type="button" role="radio" aria-checked={selectedTemplate === template.id} className={selectedTemplate === template.id ? "active" : ""} key={template.id} onClick={() => form.setValue("template_id", template.id)}><Icon size={18} /><span>{t(template.name)}</span>{selectedTemplate === template.id && <Check size={14} />}</button>;
              })}
            </div>
          </fieldset>
          <fieldset className="theme-picker span-2">
            <legend>{t("初始主题")}</legend>
            <input type="hidden" {...form.register("theme")} />
            <div className="segmented create-theme" role="radiogroup" aria-label={t("初始主题")}><button type="button" role="radio" aria-checked={selectedTheme === "light"} className={selectedTheme === "light" ? "active" : ""} onClick={() => form.setValue("theme", "light")}>{t("浅色")}</button><button type="button" role="radio" aria-checked={selectedTheme === "dark"} className={selectedTheme === "dark" ? "active" : ""} onClick={() => form.setValue("theme", "dark")}>{t("深色")}</button><button type="button" role="radio" aria-checked={selectedTheme === "system"} className={selectedTheme === "system" ? "active" : ""} onClick={() => form.setValue("theme", "system")}>{t("跟随系统")}</button></div>
          </fieldset>
          <div className="field span-2"><label htmlFor="password">{t("访问密码（可选）")}</label><input id="password" type="password" autoComplete="new-password" placeholder={t("团队成员访问前需要输入")} {...form.register("access_password")} />{form.formState.errors.access_password && <span className="field-error">{form.formState.errors.access_password.message}</span>}</div>
        </div>
        <div className="create-submit"><span>{t("无需邮箱或账号")}</span><button className="button" disabled={form.formState.isSubmitting}>{t(form.formState.isSubmitting ? "正在创建…" : "创建导航站")}</button></div>
      </form>
    </main>
  );
}
