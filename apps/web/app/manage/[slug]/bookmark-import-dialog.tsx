"use client";

import { AlertTriangle, CheckCircle2, FileUp, FolderOpen, X } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { useI18n } from "@/components/locale-provider";
import { api, ApiError } from "@/lib/api";

type ImportMode = "merge" | "replace";
type DuplicateStrategy = "skip" | "keep";

type Capacity = {
  current: number;
  importing: number;
  after: number;
  limit: number;
  allowed: boolean;
};

type BookmarkPreview = {
  source_categories: number;
  source_links: number;
  accepted_links: number;
  unsupported_links: number;
  duplicate_links: number;
  imported_links: number;
  created_categories: number;
  matched_categories: number;
  capacity: {
    allowed: boolean;
    categories: Capacity;
    links: Capacity;
  };
  categories: {
    name: string;
    source_links: number;
    imported_links: number;
    existing: boolean;
  }[];
};

type ImportDraft = {
  fileName: string;
  html: string;
  mode: ImportMode;
  duplicateStrategy: DuplicateStrategy;
};

export function BookmarkImportDialog({
  slug,
  csrf,
  onImported,
}: {
  slug: string;
  csrf: string;
  onImported: () => Promise<void>;
}) {
  const { t } = useI18n();
  const inputRef = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<ImportDraft | null>(null);
  const [preview, setPreview] = useState<BookmarkPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);

  async function loadPreview(next: ImportDraft) {
    setDraft(next);
    setLoading(true);
    try {
      const result = await api<BookmarkPreview>(
        `/api/v1/manage/sites/${slug}/bookmarks/preview`,
        {
          method: "POST",
          body: JSON.stringify({
            mode: next.mode,
            duplicate_strategy: next.duplicateStrategy,
            html: next.html,
          }),
        },
      );
      setPreview(result);
    } catch {
      setPreview(null);
      toast.error(t("书签文件无效或没有可导入的链接"));
    } finally {
      setLoading(false);
    }
  }

  async function selectFile(file: File) {
    if (file.size > 5_000_000) {
      toast.error(t("书签文件不能超过 5 MB"));
      return;
    }
    const html = await file.text();
    await loadPreview({
      fileName: file.name,
      html,
      mode: "merge",
      duplicateStrategy: "skip",
    });
  }

  function close() {
    setDraft(null);
    setPreview(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function confirmImport() {
    if (!draft || !preview?.capacity.allowed || !csrf) return;
    setImporting(true);
    try {
      const result = await api<{ imported_links: number }>(
        `/api/v1/manage/sites/${slug}/bookmarks/import`,
        {
          method: "POST",
          headers: { "X-CSRF-Token": csrf },
          body: JSON.stringify({
            mode: draft.mode,
            duplicate_strategy: draft.duplicateStrategy,
            html: draft.html,
          }),
        },
      );
      await onImported();
      toast.success(t("已导入 {count} 个书签", { count: result.imported_links }));
      close();
    } catch (error) {
      if (
        error instanceof ApiError &&
        ["BOOKMARK_IMPORT_LINK_LIMIT_REACHED", "BOOKMARK_IMPORT_CATEGORY_LIMIT_REACHED"].includes(
          error.code,
        )
      ) {
        toast.error(t("导入数量超过工作台上限"));
      } else {
        toast.error(t("书签导入失败，当前内容未更改"));
      }
    } finally {
      setImporting(false);
    }
  }

  return (
    <>
      <label className="button secondary">
        <FileUp size={16} /> {t("导入书签")}
        <input
          ref={inputRef}
          type="file"
          accept="text/html,.html"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void selectFile(file);
          }}
        />
      </label>

      {draft && (
        <div className="modal-backdrop">
          <div className="modal panel bookmark-import-dialog" role="dialog" aria-modal="true">
            <div className="panel-header">
              <div>
                <h2>{t("预览书签导入")}</h2>
                <small>{draft.fileName}</small>
              </div>
              <button className="icon-button" onClick={close} title={t("关闭")}>
                <X size={17} />
              </button>
            </div>
            <div className="panel-body form-stack">
              <div className="import-options">
                <fieldset className="appearance-group">
                  <legend>{t("导入方式")}</legend>
                  <div className="segmented-control">
                    {(["merge", "replace"] as const).map((mode) => (
                      <button
                        type="button"
                        key={mode}
                        className={draft.mode === mode ? "active" : ""}
                        onClick={() => void loadPreview({ ...draft, mode })}
                      >
                        {t(mode === "merge" ? "合并现有内容" : "替换全部内容")}
                      </button>
                    ))}
                  </div>
                </fieldset>
                <fieldset className="appearance-group">
                  <legend>{t("重复链接")}</legend>
                  <div className="segmented-control">
                    {(["skip", "keep"] as const).map((strategy) => (
                      <button
                        type="button"
                        key={strategy}
                        className={draft.duplicateStrategy === strategy ? "active" : ""}
                        onClick={() =>
                          void loadPreview({ ...draft, duplicateStrategy: strategy })
                        }
                      >
                        {t(strategy === "skip" ? "跳过重复项" : "保留重复项")}
                      </button>
                    ))}
                  </div>
                </fieldset>
              </div>

              {draft.mode === "replace" && (
                <div className="notice warning-notice">
                  <AlertTriangle size={16} /> {t("替换会删除当前全部分类和链接")}
                </div>
              )}

              {loading && <div className="import-loading"><span className="spinner" /> {t("正在分析书签…")}</div>}

              {!loading && preview && (
                <>
                  <div className="import-stats">
                    <div><strong>{preview.source_links}</strong><span>{t("文件中的链接")}</span></div>
                    <div><strong>{preview.imported_links}</strong><span>{t("预计导入")}</span></div>
                    <div><strong>{preview.duplicate_links}</strong><span>{t("重复项")}</span></div>
                    <div><strong>{preview.unsupported_links}</strong><span>{t("不支持")}</span></div>
                  </div>

                  <div className={`capacity-check ${preview.capacity.allowed ? "allowed" : "blocked"}`}>
                    {preview.capacity.allowed ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />}
                    <span>
                      {preview.capacity.allowed
                        ? t("容量检查通过")
                        : t("容量不足，无法执行本次导入")}
                    </span>
                    <small>
                      {t("导入后 {categories}/{categoryLimit} 个分类，{links}/{linkLimit} 个链接", {
                        categories: preview.capacity.categories.after,
                        categoryLimit: preview.capacity.categories.limit,
                        links: preview.capacity.links.after,
                        linkLimit: preview.capacity.links.limit,
                      })}
                    </small>
                  </div>

                  <div className="import-category-list">
                    {preview.categories.slice(0, 12).map((category) => (
                      <div key={category.name}>
                        <FolderOpen size={15} />
                        <span>{category.name}</span>
                        <small>{category.existing ? t("合并") : t("新建")} · {category.imported_links}</small>
                      </div>
                    ))}
                    {preview.categories.length > 12 && (
                      <p>{t("另有 {count} 个分类", { count: preview.categories.length - 12 })}</p>
                    )}
                  </div>
                </>
              )}

              <div className="modal-actions">
                <button className="button secondary" onClick={close}>{t("取消")}</button>
                <button
                  className="button"
                  disabled={loading || importing || !preview?.capacity.allowed || !csrf}
                  onClick={() => void confirmImport()}
                >
                  <FileUp size={16} />
                  {importing ? t("正在导入…") : t("确认导入 {count} 项", { count: preview?.imported_links ?? 0 })}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
