"use client";

import { ChevronDown, ChevronUp, Copy, Download, ExternalLink, Pin, Search, X } from "lucide-react";
import { type CSSProperties, useMemo, useState } from "react";
import { toast } from "sonner";

import { filterCategories } from "@/lib/search";
import { API_URL } from "@/lib/api";
import { getCategoryDisplay } from "@/lib/category-display";
import { faviconUrl } from "@/lib/navigation";
import { getWallpaperStyle, normalizeLayoutConfig } from "@/lib/personalization";
import type { Site } from "@/lib/types";
import { CategoryTabs } from "@/components/category-tabs";
import { useI18n } from "@/components/locale-provider";

export function NavigationView({ site, preview = false }: { site: Site; preview?: boolean }) {
  const { t, formatDate } = useI18n();
  const [query, setQuery] = useState("");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [expandedCategoryIds, setExpandedCategoryIds] = useState<Set<string>>(() => new Set());
  const categories = useMemo(
    () => filterCategories(site.categories, query, categoryId),
    [site.categories, query, categoryId],
  );
  const visibleCount = categories.reduce((total, category) => total + category.links.length, 0);
  const totalCount = site.categories.reduce((total, category) => total + category.links.length, 0);
  const pinnedLinks = useMemo(
    () => site.categories.flatMap((category) => category.links).filter((link) => link.is_pinned).slice(0, 5),
    [site.categories],
  );
  const revealAllCategories = query.trim().length > 0 || categoryId !== null;
  const layout = normalizeLayoutConfig(site.layout_config);
  const wallpaperStyle = getWallpaperStyle(layout);
  const appearance = {
    "--site-accent": layout.accent_color,
    "--nav-columns": layout.columns,
  } as CSSProperties;

  async function copyLink(url: string) {
    await navigator.clipboard.writeText(url);
    toast.success(t("链接已复制"));
  }

  async function downloadBookmarks() {
    try {
      const response = await fetch(
        `${API_URL}/api/v1/public/sites/${site.public_slug}/bookmarks/export`,
        { credentials: "include" },
      );
      if (!response.ok) throw new Error("BOOKMARK_EXPORT_FAILED");
      const objectUrl = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = `teamnav-${site.public_slug}-bookmarks.html`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1_000);
      toast.success(t("书签文件已下载"));
    } catch {
      toast.error(t("书签导出失败，请稍后重试"));
    }
  }

  function trackClick(linkId: string) {
    if (preview) return;
    void fetch(`${API_URL}/api/v1/public/sites/${site.public_slug}/links/${linkId}/click`, {
      method: "POST",
      credentials: "include",
      keepalive: true,
    });
  }

  function toggleCategory(categoryIdToToggle: string) {
    setExpandedCategoryIds((current) => {
      const next = new Set(current);
      if (next.has(categoryIdToToggle)) next.delete(categoryIdToToggle);
      else next.add(categoryIdToToggle);
      return next;
    });
  }

  return (
    <section
      className={`nav-view theme-${site.theme} canvas-${layout.canvas_style} cards-${layout.card_style} density-${layout.density} width-${layout.content_width} header-${layout.header_alignment} ${wallpaperStyle ? "wallpaper-active" : ""} ${preview ? "nav-preview" : ""}`}
      style={appearance}
    >
      {wallpaperStyle && (
        <>
          <div className="nav-wallpaper" style={wallpaperStyle} aria-hidden="true" />
          <div className="nav-wallpaper-overlay" style={{ opacity: layout.wallpaper_overlay / 100 }} aria-hidden="true" />
        </>
      )}
      <div className="nav-inner">
        <header className="nav-hero">
          <div className="nav-title-row">
            <div className="site-icon" aria-hidden="true">{site.icon}</div>
            <div className="site-heading">
              <span className="workspace-kicker">{t("共享工作台")}</span>
              <h1>{site.name}</h1>
              {site.description && <p>{site.description}</p>}
            </div>
          </div>
          <div className="nav-meta" aria-label={t("工作台摘要")}>
            <strong>{totalCount}</strong>
            <span>{t("{count} 个常用入口", { count: "" }).trim()}</span>
            <i aria-hidden="true" />
            <strong>{site.categories.length}</strong>
            <span>{t("{count} 个分组", { count: "" }).trim()}</span>
          </div>
        </header>

        {site.display_config.show_search !== false && (
          <div className="search-wrap">
            <Search size={19} aria-hidden="true" />
            <input className="search-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("搜索名称、标签或域名")} aria-label={t("搜索导航链接")} />
            {query && <button className="clear-search" onClick={() => setQuery("")} title={t("清除搜索")} aria-label={t("清除搜索")}><X size={16} /></button>}
            {query && <span className="result-count">{t("{count} 项", { count: visibleCount })}</span>}
          </div>
        )}

        {site.categories.length > 1 && (
          <CategoryTabs categories={site.categories} activeId={categoryId} allLabel={t("全部")} ariaLabel={t("分类筛选")} onSelect={setCategoryId} />
        )}

        <div className={`nav-workspace ${site.categories.length > 1 ? "has-category-rail" : ""}`}>
          {site.categories.length > 1 && (
            <nav className="nav-category-rail" aria-label={t("分类筛选")}>
              <div className="category-rail-list" role="tablist" aria-label={t("分类筛选")}>
                <button type="button" role="tab" aria-label={t("全部")} aria-selected={categoryId === null} className={categoryId === null ? "active" : ""} onClick={() => setCategoryId(null)}>
                  <span className="category-rail-icon" aria-hidden="true">#</span>
                  <span>{t("全部")}</span>
                  <strong aria-hidden="true">{totalCount}</strong>
                </button>
                {site.categories.map((category) => (
                  <button type="button" role="tab" aria-label={category.name} aria-selected={categoryId === category.id} className={categoryId === category.id ? "active" : ""} key={category.id} onClick={() => setCategoryId(category.id)}>
                    <span className="category-rail-icon" aria-hidden="true">{category.icon}</span>
                    <span>{category.name}</span>
                    <strong aria-hidden="true">{category.links.length}</strong>
                  </button>
                ))}
              </div>
            </nav>
          )}

          <div className="category-list">
            {categories.map((category) => {
              const display = getCategoryDisplay(category.links, {
                expanded: expandedCategoryIds.has(category.id),
                revealAll: revealAllCategories,
              });
              const linkGridId = `category-links-${category.id}`;
              const sectionWide = categories.length === 1 || display.links.length > 2 || revealAllCategories;
              const categoryColumns = sectionWide
                ? Math.min(layout.columns, Math.max(display.links.length, 1))
                : 1;
              return (
                <section className={`nav-category ${sectionWide ? "nav-category-wide" : ""}`} key={category.id}>
                  <div className="category-heading">
                    <span className="category-icon" aria-hidden="true">{category.icon}</span>
                    <div><h2>{category.name}</h2>{category.description && <p>{category.description}</p>}</div>
                    <span className="category-count">{category.links.length}</span>
                  </div>
                  <div className="link-grid" id={linkGridId} style={{ "--category-columns": categoryColumns } as CSSProperties}>
                    {display.links.map((link) => (
                      <article className="link-card" key={link.id}>
                        <a href={preview ? undefined : link.url} target={link.open_mode === "new" ? "_blank" : "_self"} rel="noopener noreferrer" onClick={(event) => { if (preview) event.preventDefault(); else trackClick(link.id); }}>
                          <LinkIcon url={link.url} fallback={link.icon} />
                          <span className="link-content">
                            <span className="link-name">{link.name}{link.is_pinned && <Pin size={12} />}</span>
                            {site.display_config.show_descriptions !== false && link.description && <span className="link-description">{link.description}</span>}
                            {site.display_config.show_tags !== false && link.tags.length > 0 && <span className="link-tags">{link.tags.slice(0, 3).map((tag) => <span key={tag}>{tag}</span>)}</span>}
                          </span>
                          <ExternalLink className="link-arrow" size={16} aria-hidden="true" />
                        </a>
                        {!preview && <button className="copy-link" onClick={() => copyLink(link.url)} title={t("复制链接")} aria-label={t("复制 {name} 链接", { name: link.name })}><Copy size={15} /></button>}
                      </article>
                    ))}
                  </div>
                  {display.toggle && (
                    <button
                      type="button"
                      className="category-toggle"
                      aria-controls={linkGridId}
                      aria-expanded={display.toggle === "collapse"}
                      onClick={() => toggleCategory(category.id)}
                    >
                      {display.toggle === "expand" ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
                      {display.toggle === "expand" ? t("展开其余 {count} 个", { count: display.hiddenCount }) : t("收起")}
                    </button>
                  )}
                </section>
              );
            })}
            {visibleCount === 0 && <div className="empty-search"><Search size={24} /><p>{t("没有找到匹配的链接")}</p></div>}
          </div>

          <aside className="nav-quick-panel" aria-label={t("工作台摘要")}>
            {pinnedLinks.length > 0 && (
              <section className="quick-panel-section">
                <h2><Pin size={14} />{t("置顶入口")}</h2>
                <div className="quick-link-list">
                  {pinnedLinks.map((link) => (
                    <a className="quick-link" href={preview ? undefined : link.url} target={link.open_mode === "new" ? "_blank" : "_self"} rel="noopener noreferrer" key={link.id} onClick={(event) => { if (preview) event.preventDefault(); else trackClick(link.id); }}>
                      <LinkIcon url={link.url} fallback={link.icon} />
                      <span>{link.name}</span>
                      <ExternalLink size={13} aria-hidden="true" />
                    </a>
                  ))}
                </div>
              </section>
            )}
            <section className="quick-panel-section">
              <h2>{t("工作台摘要")}</h2>
              <div className="quick-summary">
                <div><strong>{totalCount}</strong><span>{t("{count} 个常用入口", { count: "" }).trim()}</span></div>
                <div><strong>{site.categories.length}</strong><span>{t("{count} 个分组", { count: "" }).trim()}</span></div>
              </div>
              {site.display_config.show_updated_at !== false && <p className="quick-updated">{t("更新于 {date}", { date: formatDate(site.updated_at) })}</p>}
            </section>
          </aside>
        </div>

        <footer className="nav-footer">
          {site.display_config.show_updated_at !== false && <span>{t("更新于 {date}", { date: formatDate(site.updated_at) })}</span>}
          {site.display_config.show_visit_count && <span>{t("{count} 次访问", { count: site.visit_count })}</span>}
          <span className="powered-by">TeamNav</span>
          {!preview && site.display_config.allow_public_bookmark_export && <button type="button" className="bookmark-export" onClick={() => void downloadBookmarks()}><Download size={13} />{t("导出书签")}</button>}
          {!preview && <a href={`/report/${site.public_slug}`}>{t("举报")}</a>}
        </footer>
      </div>
    </section>
  );
}

function LinkIcon({ url, fallback }: { url: string; fallback: string }) {
  const source = faviconUrl(url);
  const [failed, setFailed] = useState(false);
  // Dynamic user origins cannot be declared in a Next Image hostname allowlist.
  // eslint-disable-next-line @next/next/no-img-element
  const image = <img src={source ?? ""} alt="" onError={() => setFailed(true)} />;
  return (
    <span className="link-icon" aria-hidden="true">
      {source && !failed ? image : fallback}
    </span>
  );
}
