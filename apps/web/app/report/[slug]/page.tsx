"use client";

import { Flag, Send } from "lucide-react";
import { use, useState } from "react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { useI18n } from "@/components/locale-provider";

export default function ReportPage({ params }: { params: Promise<{ slug: string }> }) {
  const { t } = useI18n();
  const { slug } = use(params);
  const [reason, setReason] = useState("spam");
  const [description, setDescription] = useState("");
  const [sent, setSent] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await api(`/api/v1/public/sites/${slug}/reports`, { method: "POST", body: JSON.stringify({ reason, description: description || null }) });
      setSent(true);
    } catch { toast.error(t("提交失败，请稍后重试")); }
  }

  return (
    <main className="compact-shell">
      <div className="success-mark"><Flag size={24} /></div>
      <h1 style={{ fontSize: 36 }}>{t("举报导航站")}</h1>
      {sent ? <div className="notice">{t("已收到举报。我们会根据站点内容和使用条款进行处理。")}</div> : (
        <form className="panel panel-body form-stack" onSubmit={submit}>
          <div className="field"><label htmlFor="reason">{t("原因")}</label><select id="reason" value={reason} onChange={(event) => setReason(event.target.value)}><option value="spam">{t("垃圾广告")}</option><option value="phishing">{t("钓鱼或欺诈")}</option><option value="illegal">{t("违法内容")}</option><option value="other">{t("其他")}</option></select></div>
          <div className="field"><label htmlFor="description">{t("补充说明")}</label><textarea id="description" maxLength={500} value={description} onChange={(event) => setDescription(event.target.value)} /></div>
          <button className="button" type="submit"><Send size={16} /> {t("提交举报")}</button>
        </form>
      )}
    </main>
  );
}
