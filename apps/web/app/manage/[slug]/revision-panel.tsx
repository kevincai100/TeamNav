"use client";

import { History, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useI18n } from "@/components/locale-provider";
import { api } from "@/lib/api";
import type { Site } from "@/lib/types";

type Revision = {
  id: string;
  action: string;
  created_at: string;
  category_count: number;
  link_count: number;
};

const actionLabels: Record<string, string> = {
  site_updated: "工作台设置已修改",
  category_created: "已添加分类",
  category_updated: "分类已修改",
  category_deleted: "分类已删除",
  categories_reordered: "分类顺序已修改",
  link_created: "已添加链接",
  link_updated: "链接已修改",
  link_deleted: "链接已删除",
  links_reordered: "链接顺序已修改",
  links_batch_created: "已批量添加链接",
  bookmarks_imported: "已导入浏览器书签",
  site_imported: "已导入站点数据",
  links_maintained: "已批量维护链接",
  revision_restored: "恢复前的工作台",
};

export function RevisionPanel({
  slug,
  csrf,
  onRestored,
}: {
  slug: string;
  csrf: string;
  onRestored: (site: Site) => void;
}) {
  const { t, formatDateTime } = useI18n();
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [restoring, setRestoring] = useState<string | null>(null);

  async function load() {
    try {
      setRevisions(await api<Revision[]>(`/api/v1/manage/sites/${slug}/revisions`));
    } catch {
      setRevisions([]);
    }
  }

  useEffect(() => {
    let active = true;
    void api<Revision[]>(`/api/v1/manage/sites/${slug}/revisions`)
      .then((result) => {
        if (active) setRevisions(result);
      })
      .catch(() => {
        if (active) setRevisions([]);
      });
    return () => {
      active = false;
    };
  }, [slug]);

  async function restore(revision: Revision) {
    if (!csrf || !window.confirm(t("恢复到此版本？当前状态会先保存到修改历史。"))) return;
    setRestoring(revision.id);
    try {
      const site = await api<Site>(
        `/api/v1/manage/sites/${slug}/revisions/${revision.id}/restore`,
        {
          method: "POST",
          headers: { "X-CSRF-Token": csrf },
        },
      );
      onRestored(site);
      await load();
      toast.success(t("工作台已恢复"));
    } catch {
      toast.error(t("恢复失败"));
    } finally {
      setRestoring(null);
    }
  }

  return (
    <details className="editor-section">
      <summary>
        <span><History size={17} /> {t("修改历史与恢复")}</span>
        <small>{t("保留最近 {count} 次", { count: 20 })}</small>
      </summary>
      <div className="editor-content revision-panel">
        {revisions.length === 0 ? (
          <p className="empty-inline">{t("还没有可恢复的修改记录")}</p>
        ) : (
          revisions.map((revision) => (
            <div className="revision-row" key={revision.id}>
              <span>
                <strong>{t(actionLabels[revision.action] ?? "工作台内容已修改")}</strong>
                <small>
                  {formatDateTime(revision.created_at)} · {t("{categories} 个分类，{links} 个链接", {
                    categories: revision.category_count,
                    links: revision.link_count,
                  })}
                </small>
              </span>
              <button
                className="button secondary"
                disabled={restoring !== null || !csrf}
                onClick={() => void restore(revision)}
              >
                <RotateCcw size={14} />
                {restoring === revision.id ? t("正在恢复…") : t("恢复")}
              </button>
            </div>
          ))
        )}
      </div>
    </details>
  );
}
