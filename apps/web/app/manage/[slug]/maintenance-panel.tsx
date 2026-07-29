"use client";

import {
  AlertTriangle,
  CheckCircle2,
  CircleOff,
  ExternalLink,
  RotateCw,
  Save,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useI18n } from "@/components/locale-provider";
import { api } from "@/lib/api";
import type { Site } from "@/lib/types";

type HealthStatus = "unchecked" | "healthy" | "warning" | "broken" | "blocked";

type MaintenanceLink = {
  id: string;
  name: string;
  url: string;
  is_enabled: boolean;
  health_status: HealthStatus;
  health_status_code: number | null;
  health_error: string | null;
  health_checked_at: string | null;
  health_consecutive_failures: number;
};

type MaintenanceReport = {
  summary: Record<HealthStatus, number>;
  links: MaintenanceLink[];
};

export function MaintenancePanel({
  slug,
  csrf,
  site,
  onSiteChange,
  onSaveSettings,
}: {
  slug: string;
  csrf: string;
  site: Site;
  onSiteChange: (site: Site) => void;
  onSaveSettings: () => Promise<void>;
}) {
  const { t } = useI18n();
  const [report, setReport] = useState<MaintenanceReport | null>(null);
  const [checking, setChecking] = useState(false);
  const [bulkWorking, setBulkWorking] = useState(false);

  async function loadReport() {
    try {
      setReport(await api<MaintenanceReport>(`/api/v1/manage/sites/${slug}/maintenance`));
    } catch {
      setReport(null);
    }
  }

  useEffect(() => {
    let active = true;
    void api<MaintenanceReport>(`/api/v1/manage/sites/${slug}/maintenance`)
      .then((result) => {
        if (active) setReport(result);
      })
      .catch(() => {
        if (active) setReport(null);
      });
    return () => {
      active = false;
    };
  }, [slug]);

  async function checkNow() {
    if (!csrf) return;
    setChecking(true);
    try {
      const result = await api<{ checked: number; remaining: number }>(
        `/api/v1/manage/sites/${slug}/maintenance/check`,
        {
          method: "POST",
          headers: { "X-CSRF-Token": csrf },
          body: JSON.stringify({ limit: 200 }),
        },
      );
      await loadReport();
      toast.success(t("已检查 {count} 个链接", { count: result.checked }));
      if (result.remaining > 0) {
        toast.info(t("还有 {count} 个链接待检查", { count: result.remaining }));
      }
    } catch {
      toast.error(t("链接检查失败"));
    } finally {
      setChecking(false);
    }
  }

  async function bulk(action: "disable_broken" | "reset_health") {
    if (!csrf) return;
    if (
      action === "disable_broken" &&
      !window.confirm(t("停用所有确认失效的链接？公开页将不再显示这些链接。"))
    ) {
      return;
    }
    setBulkWorking(true);
    try {
      const result = await api<{ updated: number }>(
        `/api/v1/manage/sites/${slug}/maintenance/bulk`,
        {
          method: "POST",
          headers: { "X-CSRF-Token": csrf },
          body: JSON.stringify({ action }),
        },
      );
      await loadReport();
      toast.success(
        action === "disable_broken"
          ? t("已停用 {count} 个失效链接", { count: result.updated })
          : t("已重置 {count} 个检查状态", { count: result.updated }),
      );
    } catch {
      toast.error(t("批量维护失败"));
    } finally {
      setBulkWorking(false);
    }
  }

  const issues = report?.links.filter((link) =>
    ["warning", "broken", "blocked"].includes(link.health_status),
  ) ?? [];

  return (
    <details className="editor-section" open>
      <summary>
        <span><ShieldCheck size={17} /> {t("链接健康检查")}</span>
        <small>{report ? t("{count} 个需关注", { count: issues.length }) : t("尚未检查")}</small>
      </summary>
      <div className="editor-content maintenance-panel">
        <div className="maintenance-config">
          <label className="toggle-field">
            <span>{t("自动检查链接")}</span>
            <input
              type="checkbox"
              checked={site.maintenance_config.link_check_enabled}
              onChange={(event) =>
                onSiteChange({
                  ...site,
                  maintenance_config: {
                    ...site.maintenance_config,
                    link_check_enabled: event.target.checked,
                  },
                })
              }
            />
          </label>
          <div className="field compact-field">
            <label>{t("检查间隔")}</label>
            <select
              value={site.maintenance_config.check_interval_hours}
              onChange={(event) =>
                onSiteChange({
                  ...site,
                  maintenance_config: {
                    ...site.maintenance_config,
                    check_interval_hours: Number(event.target.value),
                  },
                })
              }
            >
              {[6, 12, 24, 72, 168].map((hours) => (
                <option key={hours} value={hours}>{t("每 {count} 小时", { count: hours })}</option>
              ))}
            </select>
          </div>
          <button className="button secondary" onClick={() => void onSaveSettings()}>
            <Save size={15} /> {t("保存自动维护设置")}
          </button>
        </div>

        <div className="health-summary">
          <div className="healthy"><CheckCircle2 size={16} /><strong>{report?.summary.healthy ?? 0}</strong><span>{t("健康")}</span></div>
          <div className="warning"><AlertTriangle size={16} /><strong>{report?.summary.warning ?? 0}</strong><span>{t("待确认")}</span></div>
          <div className="broken"><CircleOff size={16} /><strong>{report?.summary.broken ?? 0}</strong><span>{t("已失效")}</span></div>
          <div className="blocked"><ShieldCheck size={16} /><strong>{report?.summary.blocked ?? 0}</strong><span>{t("已拦截")}</span></div>
        </div>

        <div className="maintenance-actions">
          <button className="button" disabled={checking || !csrf} onClick={() => void checkNow()}>
            <RotateCw size={15} className={checking ? "spinning" : ""} />
            {checking ? t("正在检查…") : t("立即检查")}
          </button>
          <button
            className="button secondary"
            disabled={bulkWorking || !report?.summary.broken}
            onClick={() => void bulk("disable_broken")}
          >
            <Trash2 size={15} /> {t("停用失效链接")}
          </button>
          <button
            className="button ghost"
            disabled={bulkWorking || !report}
            onClick={() => void bulk("reset_health")}
          >
            {t("重置状态")}
          </button>
        </div>

        {issues.length > 0 && (
          <div className="maintenance-issues">
            {issues.slice(0, 20).map((link) => (
              <div key={link.id}>
                <span className={`health-dot ${link.health_status}`} />
                <span><strong>{link.name}</strong><small>{link.health_error ?? link.health_status_code}</small></span>
                <a href={link.url} target="_blank" rel="noopener noreferrer" title={t("打开链接")}>
                  <ExternalLink size={15} />
                </a>
              </div>
            ))}
            {issues.length > 20 && <p>{t("另有 {count} 个链接需关注", { count: issues.length - 20 })}</p>}
          </div>
        )}
      </div>
    </details>
  );
}
